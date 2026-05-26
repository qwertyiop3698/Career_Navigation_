import json
import re
from datetime import datetime

import requests
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_env
from app.models import ProjectEvaluation, ProjectSubmission, Roadmap
from app.schemas.project import ProjectSubmissionCreate

DEFAULT_REVIEW_MODEL = "gpt-5.4-mini"
DEFAULT_MONTHLY_BUDGET_USD = 1.0
DEFAULT_MAX_OUTPUT_TOKENS = 900
DEFAULT_INPUT_PRICE_PER_MILLION = 0.75
DEFAULT_OUTPUT_PRICE_PER_MILLION = 4.50


def submit_project_for_evaluation(
    db: Session,
    roadmap: Roadmap,
    payload: ProjectSubmissionCreate,
) -> ProjectSubmission:
    blueprint = _get_blueprint(roadmap, payload.cycle_index)
    submission = next(
        (
            item
            for item in roadmap.project_submissions
            if item.cycle_index == payload.cycle_index
        ),
        None,
    )
    if submission is None:
        submission = ProjectSubmission(
            roadmap_id=roadmap.id,
            user_id=roadmap.user_id,
            cycle_index=payload.cycle_index,
            project_title=blueprint["title"],
            job_target=roadmap.job_target,
        )
        roadmap.project_submissions.append(submission)

    for field, value in _payload_dict(payload).items():
        setattr(submission, field, value)
    submission.project_title = blueprint["title"]
    submission.job_target = roadmap.job_target
    db.flush()

    evaluation_result = _evaluate_rules(submission, blueprint)
    if submission.evaluation is None:
        submission.evaluation = ProjectEvaluation(**evaluation_result)
    else:
        for field, value in evaluation_result.items():
            setattr(submission.evaluation, field, value)
        submission.evaluation.ai_review = None
        submission.evaluation.ai_model = None
        submission.evaluation.ai_input_tokens = None
        submission.evaluation.ai_output_tokens = None
    db.flush()
    return submission


def create_strict_ai_review(db: Session, submission: ProjectSubmission) -> ProjectSubmission:
    api_key = get_env("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPENAI_API_KEY가 설정되어 있지 않아 AI 리뷰를 실행할 수 없습니다.",
        )
    if submission.evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="먼저 무료 규칙 평가를 실행해주세요.",
        )
    if submission.evaluation.ai_review is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="현재 제출물의 AI 리뷰가 이미 완료되었습니다. 내용을 수정해 재평가한 뒤 요청해주세요.",
        )

    model = get_env("OPENAI_REVIEW_MODEL", DEFAULT_REVIEW_MODEL) or DEFAULT_REVIEW_MODEL
    max_output_tokens = int(
        get_env("OPENAI_REVIEW_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS))
        or DEFAULT_MAX_OUTPUT_TOKENS
    )
    budget = float(
        get_env("OPENAI_REVIEW_MONTHLY_BUDGET_USD", str(DEFAULT_MONTHLY_BUDGET_USD))
        or DEFAULT_MONTHLY_BUDGET_USD
    )
    input_price = float(
        get_env(
            "OPENAI_REVIEW_INPUT_USD_PER_MTOK",
            str(DEFAULT_INPUT_PRICE_PER_MILLION),
        )
        or DEFAULT_INPUT_PRICE_PER_MILLION
    )
    output_price = float(
        get_env(
            "OPENAI_REVIEW_OUTPUT_USD_PER_MTOK",
            str(DEFAULT_OUTPUT_PRICE_PER_MILLION),
        )
        or DEFAULT_OUTPUT_PRICE_PER_MILLION
    )
    prompt = _build_ai_prompt(submission)
    projected_cost = _estimate_cost(
        max(1, len(prompt) * 2),
        max_output_tokens,
        input_price,
        output_price,
    )
    monthly_spend = _monthly_ai_review_spend(db)
    if monthly_spend + projected_cost > budget:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"AI 리뷰 예상 비용이 월 상한 ${budget:.2f}를 넘습니다. "
                f"현재 기록 ${monthly_spend:.4f}, 이번 호출 최대 예상 ${projected_cost:.4f}입니다."
            ),
        )

    payload = {
        "model": model,
        "instructions": _review_instructions(),
        "input": prompt,
        "max_output_tokens": max_output_tokens,
        "store": False,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "strict_project_review",
                "strict": True,
                "schema": _review_schema(),
            },
            "verbosity": "low",
        },
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=(10, 60),
        )
        response.raise_for_status()
        response_json = response.json()
        ai_review = json.loads(_extract_output_text(response_json))
    except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI 리뷰 응답을 처리하지 못했습니다. 잠시 후 다시 시도해주세요.",
        ) from error

    usage = response_json.get("usage") or {}
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    actual_cost = _estimate_cost(input_tokens, output_tokens, input_price, output_price)
    submission.evaluation.ai_review = ai_review
    submission.evaluation.ai_model = model
    submission.evaluation.ai_input_tokens = input_tokens
    submission.evaluation.ai_output_tokens = output_tokens
    submission.evaluation.ai_estimated_cost_usd = (
        float(submission.evaluation.ai_estimated_cost_usd or 0.0) + actual_cost
    )
    submission.evaluation.ai_reviewed_at = datetime.utcnow()
    db.flush()
    return submission


def serialize_submission(submission: ProjectSubmission) -> dict:
    evaluation = submission.evaluation
    return {
        "id": submission.id,
        "cycle_index": submission.cycle_index,
        "project_title": submission.project_title,
        "github_url": submission.github_url,
        "submitted_at": submission.submitted_at.isoformat()
        if submission.submitted_at
        else None,
        "evaluation": {
            "id": evaluation.id,
            "rule_score": evaluation.rule_score,
            "project_evidence_points": evaluation.project_evidence_points,
            "status": evaluation.status,
            "score_breakdown": evaluation.score_breakdown or {},
            "passed_checks": evaluation.passed_checks or [],
            "missing_checks": evaluation.missing_checks or [],
            "critical_issues": evaluation.critical_issues or [],
            "ai_review": evaluation.ai_review,
            "ai_model": evaluation.ai_model,
            "ai_estimated_cost_usd": evaluation.ai_estimated_cost_usd,
        },
    }


def _get_blueprint(roadmap: Roadmap, cycle_index: int) -> dict:
    blueprints = (roadmap.content or {}).get("project_blueprints", [])
    if cycle_index > len(blueprints):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="선택한 프로젝트가 현재 로드맵에 없습니다.",
        )
    return blueprints[cycle_index - 1]


def _payload_dict(payload: ProjectSubmissionCreate) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude={"cycle_index"})
    return payload.dict(exclude={"cycle_index"})


def _evaluate_rules(submission: ProjectSubmission, blueprint: dict) -> dict:
    passed: list[str] = []
    missing: list[str] = []
    critical: list[str] = []
    breakdown: dict[str, int] = {}

    problem_score = 0
    if len(submission.problem_statement.strip()) >= 60:
        problem_score += 8
        passed.append("문제 정의가 검토 가능한 길이로 작성되었습니다.")
    else:
        missing.append("문제 정의에 대상, 목표, 활용 판단을 구체적으로 작성하세요.")
    if len(submission.data_description.strip()) >= 30:
        problem_score += 4
        passed.append("사용 데이터의 설명이 제출되었습니다.")
    else:
        missing.append("데이터 출처, 주요 변수, 목표 변수를 적어주세요.")
    if _contains_any(submission.problem_statement, ["예측", "분석", "목표", "문제", "개선", "분류", "회귀", "구현"]):
        problem_score += 3
    breakdown["문제 정의"] = problem_score

    evidence_text = " ".join(
        [
            *submission.skills_used,
            *submission.methods_used,
            submission.result_summary,
            submission.readme_text or "",
        ]
    )
    matched_methods = [
        technique
        for technique in blueprint.get("techniques", [])
        if _technique_is_evidenced(technique, evidence_text)
    ]
    implementation_score = 0
    if len(submission.skills_used) >= 2:
        implementation_score += 5
        passed.append("적용 기술 목록이 제출되었습니다.")
    else:
        missing.append("실제로 사용한 기술을 최소 2개 적어주세요.")
    if len(submission.methods_used) >= 2:
        implementation_score += 10
        passed.append("모델 또는 구현 방식을 비교할 수 있습니다.")
    else:
        missing.append("베이스라인과 비교 대상을 포함해 구현 방식을 적어주세요.")
        critical.append("핵심 구현 방식의 증거가 부족합니다.")
    method_points = min(15, len(matched_methods) * 5)
    implementation_score += method_points
    if matched_methods:
        passed.append(f"권장 구현 기술 중 {len(matched_methods)}개가 제출 내용에서 확인됩니다.")
    else:
        missing.append("추천 프로젝트의 핵심 기술이 결과물 설명에서 확인되지 않습니다.")
    breakdown["핵심 구현"] = implementation_score

    validation_score = 0
    if submission.metrics_used:
        validation_score += 8
        passed.append("평가 지표가 기재되었습니다.")
    else:
        missing.append("수치로 확인할 평가 지표를 제출하세요.")
        critical.append("평가 지표가 없습니다.")
    if re.search(r"\d", submission.result_summary):
        validation_score += 5
        passed.append("결과 요약에 수치 결과가 포함되었습니다.")
    else:
        missing.append("결과 요약에 실제 측정값을 포함하세요.")
    validation_text = f"{submission.result_summary} {submission.improvement_notes} {submission.readme_text or ''}"
    for phrase in ["baseline", "베이스라인", "비교", "cross-validation", "교차검증", "오차", "실패", "test", "검증"]:
        if phrase.lower() in validation_text.lower():
            validation_score += 12
            passed.append("비교 또는 검증 과정이 설명되어 있습니다.")
            break
    else:
        missing.append("베이스라인 비교, 검증 방식, 실패 분석 중 하나를 제시하세요.")
    breakdown["검증"] = min(validation_score, 25)

    explanation_score = 0
    if len(submission.result_summary.strip()) >= 70:
        explanation_score += 7
        passed.append("결과 해석을 검토할 수 있습니다.")
    else:
        missing.append("결과가 의미하는 바를 더 구체적으로 설명하세요.")
    if len(submission.improvement_notes.strip()) >= 40:
        explanation_score += 8
        passed.append("한계 또는 개선 계획이 작성되었습니다.")
    else:
        missing.append("실패 사례, 한계, 다음 개선 실험을 작성하세요.")
    breakdown["해석 및 개선"] = explanation_score

    delivery_score = 0
    if submission.github_url and submission.github_url.startswith(("https://github.com/", "http://github.com/")):
        delivery_score += 5
        passed.append("GitHub 주소가 제출되었습니다.")
    else:
        missing.append("검토 가능한 GitHub 저장소 주소를 제출하세요.")
        critical.append("코드 저장소 링크가 없습니다.")
    if submission.readme_text and len(submission.readme_text.strip()) >= 160:
        delivery_score += 5
        passed.append("README 근거 텍스트가 포함되었습니다.")
    else:
        missing.append("README의 문제, 실행법, 결과 부분을 붙여 넣어주세요.")
    if _contains_any(submission.readme_text or "", ["실행", "install", "pip", "npm", "requirements", "docker", "사용법"]):
        delivery_score += 5
        passed.append("실행 또는 재현 절차가 확인됩니다.")
    else:
        missing.append("설치 및 실행 방법을 README에 명시하세요.")
    breakdown["전달 가능성"] = delivery_score

    total = min(100, sum(breakdown.values()))
    if total >= 75 and not critical:
        evaluation_status = "evidence_ready"
    elif total >= 45:
        evaluation_status = "needs_revision"
    else:
        evaluation_status = "insufficient_evidence"
    maximum_points = 12 if submission.cycle_index == 1 else 13
    evidence_points = round(total / 100 * maximum_points)
    return {
        "rule_score": total,
        "project_evidence_points": evidence_points,
        "status": evaluation_status,
        "score_breakdown": breakdown,
        "passed_checks": passed,
        "missing_checks": missing,
        "critical_issues": list(dict.fromkeys(critical)),
    }


def _technique_is_evidenced(technique: str, submitted_text: str) -> bool:
    lowered = submitted_text.lower()
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]+|[가-힣]{2,}", technique)
    meaningful = [
        token
        for token in tokens
        if token.lower() not in {"기반", "또는", "비교", "모델", "분석", "구현", "처리"}
    ]
    return any(token.lower() in lowered for token in meaningful)


def _contains_any(value: str, keywords: list[str]) -> bool:
    lowered = value.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _build_ai_prompt(submission: ProjectSubmission) -> str:
    evaluation = submission.evaluation
    content = {
        "직무": submission.job_target,
        "프로젝트": submission.project_title,
        "문제정의": submission.problem_statement,
        "데이터": submission.data_description,
        "기술": submission.skills_used,
        "모델_구현방식": submission.methods_used,
        "지표": submission.metrics_used,
        "결과": submission.result_summary,
        "한계_개선": submission.improvement_notes,
        "README_발췌": submission.readme_text or "",
        "규칙평가": {
            "점수": evaluation.rule_score,
            "통과": evaluation.passed_checks,
            "누락": evaluation.missing_checks,
            "중대누락": evaluation.critical_issues,
        },
    }
    return "다음 프로젝트 제출물을 검토하세요.\n" + json.dumps(content, ensure_ascii=False)


def _review_instructions() -> str:
    return (
        "당신은 주니어 IT 취업 프로젝트의 엄격한 검토자입니다. 한국어로만 작성하세요. "
        "제출 내용에 적힌 증거만 인정하고 추측하지 마세요. 규칙 평가 점수를 변경하거나 "
        "새 점수를 제안하지 마세요. 칭찬, 응원, 과장된 긍정 표현은 쓰지 마세요. "
        "반대로 비하, 조롱, 인격 평가, 막연한 혹평도 금지합니다. "
        "문제는 관찰 가능한 사실로 말하고, 각 보완 지시는 사용자가 바로 수정할 수 있게 "
        "구체적인 산출물 또는 검증 방법을 포함하세요."
    )


def _review_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["evidence_missing", "needs_revision", "acceptable"],
            },
            "summary": {"type": "string"},
            "verified_points": {"type": "array", "items": {"type": "string"}},
            "unverified_claims": {"type": "array", "items": {"type": "string"}},
            "critical_issues": {"type": "array", "items": {"type": "string"}},
            "next_actions": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "verdict",
            "summary",
            "verified_points",
            "unverified_claims",
            "critical_issues",
            "next_actions",
        ],
        "additionalProperties": False,
    }


def _extract_output_text(response_json: dict) -> str:
    for item in response_json.get("output", []):
        for content in item.get("content", []):
            if content.get("type") == "output_text":
                return content["text"]
    raise ValueError("AI response did not contain output text.")


def _monthly_ai_review_spend(db: Session) -> float:
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    spent = (
        db.query(func.coalesce(func.sum(ProjectEvaluation.ai_estimated_cost_usd), 0.0))
        .filter(ProjectEvaluation.ai_reviewed_at >= month_start)
        .scalar()
    )
    return float(spent or 0.0)


def _estimate_cost(
    input_tokens: int,
    output_tokens: int,
    input_price_per_million: float,
    output_price_per_million: float,
) -> float:
    return round(
        (input_tokens * input_price_per_million + output_tokens * output_price_per_million)
        / 1_000_000,
        6,
    )
