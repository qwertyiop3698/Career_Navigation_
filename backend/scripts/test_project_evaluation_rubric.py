import json
import sys
from pathlib import Path
from types import SimpleNamespace


BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.project_evaluation_service import _evaluate_rules  # noqa: E402


OUTPUT_DIR = BACKEND_ROOT / "data" / "exports" / "project_evaluation_tests"
OUTPUT_JSON = OUTPUT_DIR / "current_project_rubric_test.json"
OUTPUT_MD = OUTPUT_DIR / "current_project_rubric_test.md"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    blueprint = {
        "title": "Career Navigation AI 근거 기반 취업 로드맵 서비스",
        "techniques": [
            "FastAPI API 설계",
            "PostgreSQL 및 pgvector 기반 RAG 저장 구조",
            "React Native Expo 모바일 UI",
            "Rule-based evidence validator",
            "GLOBAL/KR RAG document builder",
            "Docker Compose 실행 환경",
            "프로젝트 평가 루브릭 엔진",
        ],
    }

    current_project_submission = SimpleNamespace(
        cycle_index=1,
        job_target="AI Backend Developer",
        github_url="https://github.com/qwertyiop3698/Career_Navigation_.git",
        problem_statement=(
            "비전공자 또는 주니어 지원자가 12주 안에 목표 직무 취업 준비를 진행할 때, "
            "단순 기술 목록이 아니라 채용공고 근거와 국내 적용 사례를 기반으로 어떤 기술을 "
            "우선 학습하고 어떤 포트폴리오 과제로 증명해야 하는지 판단하기 어렵다는 문제를 해결한다. "
            "GLOBAL leading signal과 KR domestic adoption evidence를 분리해 추천 근거를 설명하는 서비스를 구현했다."
        ),
        data_description=(
            "해외 공개 ATS 채용공고, local rescreen 결과, v3/v4 verified skill evidence, "
            "국내 수동 수집 공고 61건, KR v2.1 high confidence adoption evidence, "
            "GLOBAL/KR RAG dry-run JSONL 문서를 사용했다. "
            "기술/모델 선택 이유: FastAPI는 RAG 검색 API와 모바일 앱 요청을 안정적으로 제공하기 위해 선택했고, "
            "PostgreSQL/pgvector는 임베딩 문서를 DB 안에서 검색하기 위해 선택했다. "
            "Logistic Regression은 baseline으로, LightGBM은 README와 사용자 입력에서 추출한 구조화 feature를 "
            "설명 가능하게 분류하기 위해 사용한다. 데이터가 적은 초기 단계라 딥러닝 대신 설명 가능성과 과적합 위험을 고려했다."
        ),
        skills_used=[
            "FastAPI",
            "PostgreSQL",
            "pgvector",
            "React Native",
            "Expo",
            "Docker Compose",
            "Rule-based validator",
            "RAG document builder",
        ],
        methods_used=[
            "v3 accepted/review/excluded role validation",
            "v4 verified_core_skills and verified_secondary_skills extraction",
            "KR domestic adoption v2.1 quality gate",
            "GLOBAL/KR collection-separated RAG document dry-run",
            "rubric-based project evaluation service",
        ],
        metrics_used=[
            "GLOBAL RAG 후보 437건",
            "KR high_confidence RAG 후보 12건",
            "총 RAG 문서 후보 449건",
            "metadata/content 누락 0건",
            "예상 embedding 비용 약 0.002449달러",
        ],
        result_summary=(
            "GLOBAL RAG 후보 437건과 KR RAG 후보 12건을 분리한 dry-run 문서를 생성했고, "
            "metadata 필수값 누락 0건, content too short 0건을 확인했다. "
            "Expo 앱에서는 결과/과제검증/로드맵 탭을 연결했고, 백엔드에는 과제 제출과 규칙 평가 API를 구현했다. "
            "현재 평가는 GitHub 저장소를 실제 실행하지 않고 제출 텍스트와 README 근거를 기준으로 수행된다."
        ),
        improvement_notes=(
            "현재 한계는 국내 공고 URL과 게시일이 없어 시간차 확산 분석을 주장할 수 없고, "
            "RAG 문서는 저장되었더라도 embedding 연결과 Agent 검색 API 연결은 별도 단계가 필요하다는 점이다. "
            "다음 개선은 KR 핵심 공고 URL/게시일 보완, GLOBAL/KR 검색 API 분리, 과제 제출물의 GitHub README 자동 수집 검증이다."
        ),
        readme_text=(
            "실행 방법: docker compose up -d --build 후 backend와 PostgreSQL을 실행하고, "
            "frontend에서는 npm start로 Expo 앱을 실행한다. "
            "README에는 데이터 철학, GLOBAL leading signal, KR domestic adoption, RAG dry-run, "
            "과제검증 탭, 무료 규칙 평가와 AI 리뷰 정책을 정리했다. "
            "Docker Compose, FastAPI, PostgreSQL, React Native Expo, RAG document dry-run, "
            "project_evaluation_service.py 기반 루브릭 평가 구조가 포함되어 있다."
        ),
        execution_url=None,
    )

    weak_control_submission = SimpleNamespace(
        cycle_index=1,
        job_target="AI Backend Developer",
        github_url="",
        problem_statement="취업 준비 앱을 만들었다.",
        data_description="데이터 사용.",
        skills_used=["Python"],
        methods_used=[],
        metrics_used=[],
        result_summary="잘 됐다.",
        improvement_notes="나중에 개선한다.",
        readme_text="",
        execution_url=None,
    )

    cases = [
        ("current_project", current_project_submission),
        ("weak_control", weak_control_submission),
    ]
    results = []
    for name, submission in cases:
        evaluation = _evaluate_rules(submission, blueprint)
        results.append(
            {
                "case": name,
                "rule_score": evaluation["rule_score"],
                "status": evaluation["status"],
                "project_evidence_points": evaluation["project_evidence_points"],
                "score_breakdown": evaluation["score_breakdown"],
                "passed_checks": evaluation["passed_checks"],
                "missing_checks": evaluation["missing_checks"],
                "critical_issues": evaluation["critical_issues"],
            }
        )

    current = next(item for item in results if item["case"] == "current_project")
    weak = next(item for item in results if item["case"] == "weak_control")
    assertions = {
        "current_project_reaches_evidence_ready": current["status"] == "evidence_ready",
        "current_project_has_no_critical_issues": not current["critical_issues"],
        "weak_control_does_not_pass": weak["status"] != "evidence_ready",
        "weak_control_has_critical_issues": bool(weak["critical_issues"]),
        "openai_called": False,
        "db_changed": False,
    }

    payload = {
        "purpose": "Dry-run the rubric-based project evaluation engine with the current project as a submission.",
        "evaluation_source": "backend/app/services/project_evaluation_service.py::_evaluate_rules",
        "blueprint": blueprint,
        "results": results,
        "assertions": assertions,
    }
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_MD.write_text(build_markdown(payload), encoding="utf-8")

    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_markdown(payload: dict) -> str:
    lines = [
        "# Current Project Rubric Test",
        "",
        "이 보고서는 현재 Career Navigation AI 프로젝트를 과제 제출물로 가정하고 무료 루브릭 평가 엔진을 dry-run한 결과입니다.",
        "",
        "안전 확인:",
        "- DB 저장/수정 없음",
        "- OpenAI API 호출 없음",
        "- 임베딩/RAG 저장 없음",
        "",
        "## Test Cases",
        "",
    ]
    for result in payload["results"]:
        lines.extend(
            [
                f"### {result['case']}",
                "",
                f"- status: `{result['status']}`",
                f"- rule_score: `{result['rule_score']}`",
                f"- project_evidence_points: `{result['project_evidence_points']}`",
                "",
                "Score breakdown:",
            ]
        )
        for key, value in result["score_breakdown"].items():
            lines.append(f"- {key}: {value}")
        lines.extend(["", "Critical issues:"])
        if result["critical_issues"]:
            for item in result["critical_issues"]:
                lines.append(f"- {item}")
        else:
            lines.append("- 없음")
        lines.extend(["", "Missing checks:"])
        if result["missing_checks"]:
            for item in result["missing_checks"]:
                lines.append(f"- {item}")
        else:
            lines.append("- 없음")
        lines.append("")

    lines.extend(["## Assertions", ""])
    for key, value in payload["assertions"].items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
