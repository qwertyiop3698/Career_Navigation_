import json
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

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
TECHNIQUE_STOPWORDS = {
    "기반",
    "또는",
    "비교",
    "모델",
    "분석",
    "구현",
    "처리",
    "프로젝트",
    "평가",
    "엔진",
    "설계",
    "구조",
    "환경",
    "서비스",
    "기술",
}

TECH_SKILL_ALIASES = {
    "RAG": [r"\brag\b", "검색증강생성"],
    "Retrieval": [r"\bretrieval\b", "검색"],
    "LLM": [r"\bllm\b", "large language model", "거대언어모델"],
    "API": [r"\bapi\b", "REST API", "엔드포인트"],
    "FastAPI": [r"\bfastapi\b", "Fast API"],
    "Vector Database": ["vector database", "vector db", "vectordb", "pgvector", "벡터db", "벡터 db"],
    "Embedding": [r"\bembedding\b", "임베딩"],
    "PostgreSQL": [r"\bpostgresql\b", r"\bpostgres\b"],
    "Docker": [r"\bdocker\b", "컨테이너"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b"],
    "LangChain": [r"\blangchain\b", "랭체인"],
    "LangGraph": [r"\blanggraph\b", "랭그래프"],
    "Model Serving": ["model serving", "모델 서빙", "서빙"],
    "Inference Serving": ["inference serving", "추론"],
    "Data Pipeline": ["data pipeline", "데이터 파이프라인"],
    "ETL": [r"\betl\b", "elt"],
    "Airflow": [r"\bairflow\b", "에어플로우"],
    "Spark": [r"\bspark\b", "스파크"],
    "SQL": [r"\bsql\b"],
    "Python": [r"\bpython\b", "파이썬"],
    "React": [r"\breact\b", "리액트"],
    "TypeScript": [r"\btypescript\b", "타입스크립트"],
    "JavaScript": [r"\bjavascript\b", "자바스크립트"],
    "Spring": [r"\bspring\b", "스프링"],
    "LightGBM": [r"\blightgbm\b"],
    "Logistic Regression": ["logistic regression", "로지스틱 회귀"],
}

ROLE_FALLBACK_SKILLS = {
    "AI Backend Developer": {"RAG", "Retrieval", "LLM", "API", "FastAPI", "Vector Database", "Embedding", "PostgreSQL", "Docker", "LangChain", "Model Serving", "Inference Serving"},
    "Backend Developer": {"API", "FastAPI", "PostgreSQL", "Docker", "Kubernetes", "Python", "Spring", "SQL"},
    "Builder": {"LLM", "API", "FastAPI", "React", "TypeScript", "JavaScript", "Python", "Automation", "LangChain"},
    "Data Analyst": {"SQL", "Python", "Analytics", "Dashboard", "Statistics"},
    "Data Engineer": {"Data Pipeline", "ETL", "Airflow", "Spark", "SQL", "Python", "PostgreSQL", "Docker"},
    "Data Scientist": {"Python", "Machine Learning", "Statistics", "Regression", "Classification", "Deep Learning"},
    "Frontend Developer": {"React", "TypeScript", "JavaScript", "HTML", "CSS", "Next.js"},
}


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
    if submission.github_url and not submission.readme_text:
        fetched_readme = _fetch_github_readme_excerpt(submission.github_url)
        if fetched_readme:
            submission.readme_text = f"[GitHub README 자동 수집]\n{fetched_readme}"
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

    features = _build_portfolio_features(submission, blueprint)

    consistency_score = 0
    if len(submission.problem_statement.strip()) >= 60:
        consistency_score += 5
        passed.append("사용자 설명: 해결하려는 문제와 프로젝트 의도를 검토할 수 있는 길이로 작성했습니다.")
    else:
        missing.append("사용자 설명: 해결하려는 문제와 목표 사용자를 한 문단으로 구체화하세요.")
    if features["claimed_skill_count"] >= 2:
        consistency_score += 4
        passed.append(f"사용자 설명: 보여주고 싶은 직무 스킬 {features['claimed_skill_count']}개가 제출되었습니다.")
    else:
        missing.append("사용자 설명: 이 프로젝트로 증명하려는 직무 스킬을 최소 2개 이상 입력하세요.")
    if features["readme_claim_overlap_count"] >= 2:
        consistency_score += 7
        passed.append("주장-README 일치: 사용자가 주장한 기술 중 2개 이상이 README에서도 확인됩니다.")
    elif features["readme_claim_overlap_count"] >= 1:
        consistency_score += 4
        missing.append("주장-README 일치: README에서 확인되는 사용자 주장 기술이 1개뿐입니다.")
    else:
        missing.append("주장-README 일치: 사용자가 주장한 핵심 기술이 README 증거에서 확인되지 않습니다.")
        critical.append("사용자 주장과 README 증거의 연결이 약합니다.")
    if features["technology_reason_present"]:
        consistency_score += 4
        passed.append("기술 선택 이유: 왜 이 기술/모델을 선택했는지 사용자가 설명했습니다.")
    else:
        missing.append("기술 선택 이유: 왜 이 기술/모델을 사용했는지, 목표 직무와의 연결을 적어주세요.")
    breakdown["사용자-README 일치"] = min(consistency_score, 20)

    readme_score = 0
    if features["readme_length"] >= 500:
        readme_score += 5
        passed.append("README 증거: README 본문이 충분한 길이로 자동 수집되었습니다.")
    elif features["readme_length"] >= 160:
        readme_score += 3
        missing.append("README 증거: README는 수집됐지만 포트폴리오 증빙으로는 조금 짧습니다.")
    else:
        missing.append("README 증거: GitHub README가 없거나 너무 짧습니다.")
        if not submission.github_url and not submission.execution_url:
            critical.append("검토 가능한 README 또는 결과물 증빙이 부족합니다.")
    if features["readme_has_problem"]:
        readme_score += 3
    else:
        missing.append("README 증거: 문제 정의 또는 프로젝트 목적 섹션을 추가하세요.")
    if features["readme_has_implementation"]:
        readme_score += 4
        passed.append("README 증거: 구현 방식, 아키텍처, API, 데이터 흐름 중 하나가 설명되어 있습니다.")
    else:
        missing.append("README 증거: 구현 흐름, API, 모델 구조, 데이터 흐름 중 하나를 README에 명시하세요.")
    if features["readme_has_result"]:
        readme_score += 4
        passed.append("README 증거: 결과, 예시, 화면, 지표 또는 테스트 근거가 확인됩니다.")
    else:
        missing.append("README 증거: 실행 결과, 예시 응답, 화면 캡처, 지표 중 하나를 추가하세요.")
    if features["readme_has_limitation"]:
        readme_score += 2
    else:
        missing.append("README 증거: 한계와 다음 개선 계획을 README에 추가하세요.")
    if features["readme_has_runbook"]:
        readme_score += 2
        passed.append("README 증거: 실행 또는 재현 절차가 확인됩니다.")
    else:
        missing.append("README 증거: 설치 및 실행 방법을 README에 명시하세요.")
    breakdown["README 증빙력"] = min(readme_score, 20)

    market_score = 0
    if features["global_evidence_match_count"]:
        market_score += min(10, features["global_evidence_match_count"] * 3)
        passed.append(
            f"GLOBAL 근거: 목표 직무의 해외 선행 신호와 {features['global_evidence_match_count']}개 기술이 연결됩니다."
        )
    else:
        missing.append("GLOBAL 근거: 사용 기술이 목표 직무의 해외 선행 신호와 충분히 매칭되지 않습니다.")
    if features["kr_evidence_match_count"]:
        market_score += min(7, features["kr_evidence_match_count"] * 3)
        passed.append(
            f"KR 근거: 국내 적용 사례와 {features['kr_evidence_match_count']}개 기술이 연결됩니다."
        )
    else:
        missing.append("KR 근거: 현재 국내 적용 사례와 직접 연결되는 기술이 부족합니다.")
    if features["role_fallback_match_count"] >= 2:
        market_score += 5
    elif features["role_fallback_match_count"] >= 1:
        market_score += 3
    else:
        critical.append("목표 직무의 핵심 기술 근거와 프로젝트 기술이 거의 맞지 않습니다.")
    if features["unrelated_skill_count"] == 0:
        market_score += 3
    else:
        missing.append(
            f"직무 적합성: 목표 직무 근거와 약한 기술 {features['unrelated_skill_count']}개는 README에서 역할을 더 설명해야 합니다."
        )
    breakdown["직무/시장 근거 적합성"] = min(market_score, 25)

    reasoning_score = 0
    reason_text = features["technology_reason_text"]
    if len(reason_text) >= 60:
        reasoning_score += 5
    elif len(reason_text) >= 20:
        reasoning_score += 3
    else:
        missing.append("기술 선택 이유: 기술을 쓴 목적, 직무 연결, 대안을 더 구체화하세요.")
    if _contains_any(reason_text, ["왜", "목적", "필요", "문제", "해결", "선택", "위해"]):
        reasoning_score += 4
    else:
        missing.append("기술 선택 이유: 문제 해결 목적과 기술 선택을 직접 연결하세요.")
    if _contains_any(reason_text, [submission.job_target, "직무", "역량", "채용", "백엔드", "데이터", "프론트", "AI"]):
        reasoning_score += 4
    else:
        missing.append("기술 선택 이유: 목표 직무에서 어떤 역량을 보여주려는 선택인지 적어주세요.")
    if _contains_any(reason_text, ["대신", "비교", "대안", "tradeoff", "과적합", "설명 가능", "비용", "데이터가 적"]):
        reasoning_score += 4
        passed.append("기술 선택 이유: 대안, 제약, 비용, 설명 가능성 중 하나를 고려했습니다.")
    else:
        missing.append("기술 선택 이유: 다른 방법 대신 이 방식을 선택한 이유나 한계를 추가하세요.")
    if len(submission.improvement_notes.strip()) >= 40:
        reasoning_score += 3
    else:
        missing.append("한계 인식: 실패 사례, 한계, 다음 개선 실험을 구체적으로 작성하세요.")
    breakdown["기술 선택 타당성"] = min(reasoning_score, 20)

    result_score = 0
    if submission.metrics_used:
        result_score += 4
        passed.append(f"결과 증빙: 결과 증빙 또는 측정 항목 {len(submission.metrics_used)}개가 확인됩니다.")
    if re.search(r"\d", submission.result_summary):
        result_score += 4
        passed.append("결과 증빙: 결과 요약에 수치가 포함되어 있습니다.")
    else:
        missing.append("결과 증빙: 실제 측정값, 건수, 점수, 시간, 비용 중 하나를 포함하세요.")
        critical.append("측정 결과 근거가 부족합니다.")
    if _contains_any(
        f"{submission.result_summary} {submission.readme_text or ''}",
        ["baseline", "베이스라인", "비교", "before", "after", "테스트", "test", "pytest", "통과", "캡처", "스크린샷", "screenshot"],
    ):
        result_score += 5
        passed.append("결과 증빙: 비교, 테스트, 실행 화면, 캡처 중 하나가 확인됩니다.")
    else:
        missing.append("결과 증빙: 비교 결과, 테스트 로그, 실행 화면 캡처, 예시 응답 중 하나를 README에 추가하세요.")
    if len(submission.result_summary.strip()) >= 70:
        result_score += 2
    else:
        missing.append("결과 증빙: 결과가 직무 역량 증명에 어떤 의미가 있는지 설명하세요.")
    breakdown["결과 증빙"] = min(result_score, 15)

    total = min(100, sum(breakdown.values()))
    scope_cap = _evidence_scope_score_cap(submission)
    if scope_cap < total:
        total = scope_cap
        missing.append(
            "평가 범위: README와 입력 텍스트만으로는 코드 실행 성공을 확정할 수 없습니다. "
            "실행 로그, 테스트 통과 결과, 캡처, 배포 URL 중 하나를 추가하면 신뢰도가 올라갑니다."
        )
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
        "passed_checks": passed + [_format_feature_summary(features)],
        "missing_checks": missing,
        "critical_issues": list(dict.fromkeys(critical)),
    }


def _technique_is_evidenced(technique: str, submitted_text: str) -> bool:
    lowered = submitted_text.lower()
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9-]+|[가-힣]{2,}", technique)
    meaningful = [
        token
        for token in tokens
        if token.lower() not in TECHNIQUE_STOPWORDS
    ]
    if not meaningful:
        return False
    return any(token.lower() in lowered for token in meaningful)


def _build_portfolio_features(submission: ProjectSubmission, blueprint: dict) -> dict:
    readme = submission.readme_text or ""
    user_text = " ".join(
        [
            submission.problem_statement or "",
            submission.data_description or "",
            " ".join(submission.skills_used or []),
            " ".join(submission.methods_used or []),
            submission.result_summary or "",
            submission.improvement_notes or "",
        ]
    )
    combined_text = f"{user_text} {readme}"
    claimed_skills = _extract_canonical_skills(
        " ".join([*submission.skills_used, *submission.methods_used, submission.data_description or ""])
    )
    readme_skills = _extract_canonical_skills(readme)
    all_detected_skills = sorted(set(claimed_skills) | set(readme_skills))
    overlap = sorted(set(claimed_skills) & set(readme_skills))
    evidence = _load_role_evidence_index()
    role = submission.job_target
    role_fallback = ROLE_FALLBACK_SKILLS.get(role, set())
    global_matches = sorted(
        skill
        for skill in all_detected_skills
        if skill in evidence["global"].get(role, set())
    )
    kr_matches = sorted(
        skill
        for skill in all_detected_skills
        if skill in evidence["kr"].get(role, set())
    )
    role_matches = sorted(skill for skill in all_detected_skills if skill in role_fallback)
    weak_skills = [
        skill
        for skill in all_detected_skills
        if skill not in set(global_matches) | set(kr_matches) | set(role_matches)
    ]
    technology_reason_text = _extract_technology_reason_text(submission)
    return {
        "target_role": role,
        "claimed_skill_count": len(claimed_skills),
        "readme_skill_count": len(readme_skills),
        "readme_claim_overlap_count": len(overlap),
        "claimed_skills": claimed_skills,
        "readme_skills": readme_skills,
        "overlap_skills": overlap,
        "global_evidence_match_count": len(global_matches),
        "kr_evidence_match_count": len(kr_matches),
        "role_fallback_match_count": len(role_matches),
        "global_evidence_matched_skills": global_matches,
        "kr_evidence_matched_skills": kr_matches,
        "role_fallback_matched_skills": role_matches,
        "unrelated_skill_count": len(weak_skills),
        "unrelated_skills": weak_skills,
        "readme_length": len(readme.strip()),
        "readme_has_problem": _contains_any(readme, ["문제", "problem", "purpose", "목표", "배경", "해결"]),
        "readme_has_implementation": _contains_any(
            readme,
            ["구현", "architecture", "아키텍처", "api", "model", "모델", "pipeline", "파이프라인", "flow", "흐름"],
        ),
        "readme_has_result": _contains_any(
            readme,
            ["결과", "result", "평가", "metric", "accuracy", "정확도", "화면", "캡처", "screenshot", "test", "테스트"],
        ),
        "readme_has_limitation": _contains_any(readme, ["한계", "limitation", "개선", "todo", "future", "실패"]),
        "readme_has_runbook": _contains_any(readme, ["실행", "install", "pip", "npm", "requirements", "docker", "사용법", "run"]),
        "technology_reason_present": len(technology_reason_text.strip()) >= 20,
        "technology_reason_text": technology_reason_text,
        "ml_model_feature_note": "LightGBM 학습 전 단계의 rule-based pseudo-label/feature입니다.",
    }


def _extract_technology_reason_text(submission: ProjectSubmission) -> str:
    marker = "기술/모델 선택 이유:"
    text = submission.data_description or ""
    if marker in text:
        return text.split(marker, 1)[1].strip()
    return " ".join(
        [
            submission.data_description or "",
            submission.improvement_notes or "",
        ]
    ).strip()


def _format_feature_summary(features: dict) -> str:
    return (
        "ML-ready feature: "
        f"claimed_skills={features['claimed_skills']}, "
        f"readme_overlap={features['overlap_skills']}, "
        f"global_matches={features['global_evidence_matched_skills']}, "
        f"kr_matches={features['kr_evidence_matched_skills']}, "
        f"weak_skills={features['unrelated_skills']}"
    )


def _extract_canonical_skills(text: str) -> list[str]:
    if not text:
        return []
    found: list[str] = []
    for skill, aliases in TECH_SKILL_ALIASES.items():
        for alias in aliases:
            if alias.startswith("\\b") or any(ch in alias for ch in ["[", "(", "|", "\\"]):
                if re.search(alias, text, flags=re.IGNORECASE):
                    found.append(skill)
                    break
            elif alias.lower() in text.lower():
                found.append(skill)
                break
    return sorted(dict.fromkeys(found))


@lru_cache(maxsize=1)
def _load_role_evidence_index() -> dict:
    backend_root = Path(__file__).resolve().parents[2]
    global_path = backend_root / "data" / "exports" / "rag_dryrun" / "global_rag_documents_dryrun_v1.jsonl"
    kr_path = backend_root / "data" / "exports" / "rag_dryrun" / "kr_rag_documents_dryrun_v1.jsonl"
    index = {"global": {}, "kr": {}}
    _read_evidence_jsonl(global_path, index["global"], market="global")
    _read_evidence_jsonl(kr_path, index["kr"], market="kr")
    for role, skills in ROLE_FALLBACK_SKILLS.items():
        index["global"].setdefault(role, set()).update(skills)
    return index


def _read_evidence_jsonl(path: Path, target: dict[str, set[str]], market: str) -> None:
    if not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        metadata = item.get("metadata") or {}
        if market == "global":
            role = metadata.get("job_role_category")
            skills = [
                *(metadata.get("verified_core_skills") or []),
                *(metadata.get("verified_secondary_skills") or []),
            ]
            _add_role_skills(target, role, skills)
        else:
            primary = metadata.get("primary_role")
            related = metadata.get("related_roles") or []
            skills = metadata.get("verified_adoption_skills") or []
            _add_role_skills(target, primary, skills)
            for role in related:
                _add_role_skills(target, role, skills)


def _add_role_skills(target: dict[str, set[str]], role: str | None, skills: list[str]) -> None:
    if not role:
        return
    normalized = {skill for skill in skills if isinstance(skill, str) and skill}
    if normalized:
        target.setdefault(role, set()).update(normalized)


def _contains_any(value: str, keywords: list[str]) -> bool:
    lowered = value.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _evidence_scope_score_cap(submission: ProjectSubmission) -> int:
    text = " ".join(
        [
            submission.result_summary or "",
            submission.improvement_notes or "",
            submission.readme_text or "",
            submission.execution_url or "",
        ]
    ).lower()
    has_readme = bool((submission.readme_text or "").strip())
    has_execution_proof = any(
        keyword in text
        for keyword in [
            "실행 로그",
            "테스트 통과",
            "테스트 결과",
            "성공 로그",
            "배포 url",
            "배포 링크",
            "실행 캡처",
            "스크린샷",
            "pytest",
            "npm test",
            "curl",
            "ci",
            "passed",
            "screenshot",
        ]
    )
    has_measured_result = bool(re.search(r"\d", submission.result_summary or ""))

    if has_readme and has_execution_proof and has_measured_result:
        return 100
    if has_readme and has_measured_result:
        return 90
    if has_readme:
        return 82
    return 70


def _fetch_github_readme_excerpt(github_url: str, max_chars: int = 12000) -> str | None:
    parsed = urlparse(github_url.strip())
    if parsed.netloc.lower() != "github.com":
        return None

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None

    owner, repo = parts[0], parts[1].removesuffix(".git")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", owner) or not re.fullmatch(r"[A-Za-z0-9_.-]+", repo):
        return None

    candidates = [
        f"https://raw.githubusercontent.com/{owner}/{repo}/main/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/master/README.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/main/readme.md",
        f"https://raw.githubusercontent.com/{owner}/{repo}/master/readme.md",
    ]
    for url in candidates:
        try:
            response = requests.get(url, timeout=(5, 12))
        except requests.RequestException:
            continue
        if response.status_code != 200:
            continue
        text = response.text.strip()
        if not text:
            continue
        return text[:max_chars]
    return None


def _build_ai_prompt(submission: ProjectSubmission) -> str:
    evaluation = submission.evaluation
    content = {
        "직무": submission.job_target,
        "프로젝트": submission.project_title,
        "GitHub_URL_선택증빙": submission.github_url or "",
        "실행_URL_선택증빙": submission.execution_url or "",
        "문제정의": submission.problem_statement,
        "데이터": submission.data_description,
        "기술": submission.skills_used,
        "모델_구현방식": submission.methods_used,
        "측정_결과_항목": submission.metrics_used,
        "결과": submission.result_summary,
        "한계_개선": submission.improvement_notes,
        "README_PDF_캡처_증빙_발췌": submission.readme_text or "",
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
        "GitHub URL이나 실행 URL은 제출 여부만 확인하고, 실제 링크 내용을 열람했다고 말하지 마세요. "
        "README, PDF, 캡처 증빙 발췌에 없는 내용은 확인된 사실로 취급하지 마세요. "
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
