from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import build_korean_domestic_adoption_evidence as v1


ROOT_DIR = Path(__file__).resolve().parents[1]
KOREAN_DIR = ROOT_DIR / "data" / "exports" / "korean_batches"
GLOBAL_V4 = (
    ROOT_DIR
    / "data"
    / "exports"
    / "additional_batches"
    / "external_job_postings_role_evidence_v4_evidence_boost_20260529_01_parserfix_v2.csv"
)

HIGH_CONFIDENCE_REVIEW_ORDER = [
    "kr_manual_0023",
    "kr_manual_0027",
    "kr_manual_0051",
    "kr_manual_0012",
    "kr_manual_0022",
    "kr_manual_0025",
    "kr_manual_0043",
    "kr_manual_0017",
    "kr_manual_0020",
    "kr_manual_0001",
]

HIGH_CONFIDENCE_REVIEW_IDS = set(HIGH_CONFIDENCE_REVIEW_ORDER)

HIGH_CONFIDENCE_REVIEW_IDS.update(
    {
        "kr_manual_0021",
        "kr_manual_0028",
    }
)

MANDATORY_HIGH_CONFIDENCE_IDS = {
    "kr_manual_0023",
    "kr_manual_0027",
    "kr_manual_0051",
    "kr_manual_0012",
    "kr_manual_0022",
    "kr_manual_0025",
    "kr_manual_0043",
    "kr_manual_0017",
    "kr_manual_0020",
    "kr_manual_0001",
}

FORCED_EXCLUDE = {
    "kr_manual_0002": "QA/test automation is not Builder domestic adoption evidence.",
    "kr_manual_0005": "Role body is too thin; statistics appears as degree/major context, not domestic technology application.",
    "kr_manual_0014": "Distributed storage/system engineering role is outside current seven-role domestic adoption scope.",
}

FORCED_DOWNGRADE = {
    "kr_manual_0019": "Analysis/statistics program development is not enough for Data Scientist domestic adoption without ML/DL/prediction evidence.",
}

MAPPING_PENDING_SKILLS = {"Agent", "Generative AI", "LLMOps", "LangGraph", "OpenAI API", "MCP", "CI/CD", "Snowflake", "Databricks"}

SKILL_PATTERNS = {
    "RAG": [r"\brag\b", r"검색\s*증강\s*생성"],
    "Vector Database": [r"vector\s*db", r"vectordb", r"vector\s*database", r"벡터\s*db", r"벡터\s*데이터베이스", r"vector\s*store"],
    "Embedding": [r"\bembedding\b", r"임베딩"],
    "Retrieval": [r"\bretrieval\b", r"하이브리드\s*검색", r"검색\s*(?:프로그램|솔루션|엔진|최적화|시스템|api)"],
    "LLM": [r"\bllm\b", r"large\s*language\s*model", r"거대\s*언어\s*모델"],
    "API": [r"\bapi\b", r"api\s*(?:설계|개발|연동|라우팅|서버|구현)"],
    "REST API": [r"rest\s*api"],
    "OpenAI API": [r"openai\s*api", r"오픈\s*ai\s*api"],
    "FastAPI": [r"fast\s*api", r"fastapi"],
    "LangChain": [r"lang\s*chain", r"langchain", r"랭\s*체인"],
    "LangGraph": [r"lang\s*graph", r"langgraph", r"랭\s*그래프"],
    "Docker": [r"\bdocker\b", r"도커", r"컨테이너화"],
    "Model Serving": [r"model\s*serving", r"모델\s*서빙", r"서빙\s*(?:환경|시스템)"],
    "Inference Serving": [r"inference\s*serving", r"추론\s*(?:환경|서빙|시스템)", r"모델\s*추론"],
    "Data Pipeline": [r"data\s*pipeline", r"데이터\s*파이프라인", r"데이터\s*파이브라인"],
    "Airflow": [r"\bairflow\b", r"air\s*flow", r"에어\s*플로우"],
    "ETL": [r"\betl\b", r"\belt\b", r"etl\s*파이프라인"],
    "React": [r"\breact\b", r"리액트"],
    "TypeScript": [r"\btypescript\b", r"타입\s*스크립트"],
    "Next.js": [r"next\.?\s*js", r"nextjs"],
    "PostgreSQL": [r"postgresql", r"postgres"],
    "Java": [r"java(?!script)"],
    "Python": [r"\bpython\b", r"파이썬"],
    "Spring": [r"\bspring\b", r"스프링"],
    "Redis": [r"\bredis\b"],
    "Kafka": [r"\bkafka\b", r"카프카"],
    "Kubernetes": [r"\bkubernetes\b", r"\bk8s\b", r"쿠버네티스"],
    "AWS": [r"\baws\b", r"아마존\s*웹\s*서비스"],
    "Azure": [r"\bazure\b"],
    "SQL": [r"\bsql\b"],
    "Spark": [r"\bspark\b", r"스파크"],
    "Generative AI": [r"generative\s*ai", r"생성형\s*ai"],
    "Agent": [r"\bagent\b", r"에이전트", r"멀티\s*에이전트"],
    "LLMOps": [r"\bllmops\b", r"llm\s*ops"],
    "LangGraph": [r"lang\s*graph", r"langgraph", r"랭\s*그래프"],
    "MCP": [r"\bmcp\b"],
    "CI/CD": [r"ci\s*/\s*cd", r"\bcicd\b"],
    "Snowflake": [r"\bsnowflake\b"],
    "Databricks": [r"\bdatabricks\b"],
    "Machine Learning": [r"machine\s*learning", r"머신\s*러닝"],
    "Deep Learning": [r"deep\s*learning", r"딥\s*러닝"],
    "Prompt Engineering": [r"prompt\s*engineering", r"프롬프트\s*엔지니어링"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit KR domestic adoption v2 and produce v2.1 quality gate outputs.")
    parser.add_argument("--adoption-input", default=str(KOREAN_DIR / "korean_job_postings_domestic_adoption_v2.csv"))
    parser.add_argument("--review-input", default=str(KOREAN_DIR / "korean_job_postings_domestic_adoption_review_v2.csv"))
    parser.add_argument("--global-input", default=str(GLOBAL_V4))
    parser.add_argument("--output-dir", default=str(KOREAN_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    adoption_rows = read_csv(Path(args.adoption_input))
    review_rows = read_csv(Path(args.review_input))
    v2_rows = adoption_rows + review_rows
    global_rows = read_csv(Path(args.global_input))

    audited_rows = [audit_row(row) for row in v2_rows]
    matrix_rows = build_matrix(global_rows, audited_rows)

    paths = {
        "quality_gate": output_dir / "korean_domestic_adoption_quality_gate_v21.csv",
        "rag_candidates": output_dir / "korean_domestic_adoption_rag_candidates_v21.csv",
        "excluded_or_downgraded": output_dir / "korean_domestic_adoption_excluded_or_downgraded_v21.csv",
        "matrix": output_dir / "global_to_korean_skill_adoption_matrix_kr_v21.csv",
        "report": output_dir / "korean_domestic_adoption_quality_gate_report_kr_v21.md",
    }

    write_csv(paths["quality_gate"], quality_fields(), audited_rows)
    write_csv(paths["rag_candidates"], quality_fields(), [row for row in audited_rows if row["rag_candidate_status"] == "high_confidence"])
    write_csv(
        paths["excluded_or_downgraded"],
        quality_fields(),
        [
            row
            for row in audited_rows
            if row["rag_candidate_status"] != "high_confidence"
            or row["v21_change_type"] in {"downgraded", "excluded", "cleaned_state_conflict"}
        ],
    )
    write_csv(paths["matrix"], matrix_fields(), matrix_rows)
    paths["report"].write_text(build_report(v2_rows, audited_rows, matrix_rows), encoding="utf-8")

    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, indent=2))
    return 0


def audit_row(row: dict[str, str]) -> dict[str, str]:
    text = evidence_text(row)
    original_status = row.get("adoption_evidence_status", "")
    original_skills = parse_semicolon(row.get("verified_adoption_skills", ""))
    skills, details = detect_direct_skills(text)
    reason = ""
    change_type = "maintained"

    if row["source_posting_id"] in FORCED_EXCLUDE:
        final_status = "excluded"
        skills = []
        details = []
        context = ""
        rag_status = "exclude_from_rag"
        reason = FORCED_EXCLUDE[row["source_posting_id"]]
        false_positive_risk = "high"
        change_type = "excluded"
    elif original_status in {"excluded", "insufficient_evidence"}:
        final_status = original_status
        skills = []
        details = []
        context = ""
        rag_status = "exclude_from_rag"
        reason = "State conflict cleaned: no adoption claim is emitted for excluded/insufficient rows."
        false_positive_risk = "high" if row.get("adoption_context") or original_skills else "medium"
        change_type = "cleaned_state_conflict"
    elif row["source_posting_id"] in FORCED_DOWNGRADE:
        final_status = "limited_adoption_evidence"
        skills = [skill for skill in skills if skill not in {"Statistics", "Machine Learning", "Deep Learning"}]
        context = limited_context(row, skills, FORCED_DOWNGRADE[row["source_posting_id"]])
        rag_status = "manual_review_needed"
        reason = FORCED_DOWNGRADE[row["source_posting_id"]]
        false_positive_risk = "high"
        change_type = "downgraded"
    else:
        skills = apply_row_skill_guardrails(row, skills)
        if not skills:
            final_status = "insufficient_evidence"
            context = ""
            rag_status = "exclude_from_rag"
            reason = "No direct body skill evidence remained after v2.1 guardrails."
            false_positive_risk = "medium"
            change_type = "downgraded" if original_status not in {"insufficient_evidence", "excluded"} else "maintained"
        elif row["source_posting_id"] == "kr_manual_0007":
            final_status = "limited_adoption_evidence"
            context = "국내 검색 솔루션 개발 역할에서 검색 프로그램 개발과 Java/Python 활용 경험이 요구됩니다."
            rag_status = "supporting_context_only"
            reason = "Search/retrieval context is direct, but RAG, Vector Database, and Embedding are not directly stated."
            false_positive_risk = "medium"
            change_type = "downgraded"
        elif row["source_posting_id"] in HIGH_CONFIDENCE_REVIEW_IDS and has_substantive_skill_context(skills):
            final_status = "cross_role_adoption_evidence" if row.get("related_roles") else "adoption_evidence_ready"
            context = safe_context(row, skills)
            rag_status = "high_confidence"
            reason = "Direct body skill evidence and domestic work context are strong enough for KR RAG candidate use."
            false_positive_risk = "low"
        elif original_status == "limited_adoption_evidence":
            final_status = "limited_adoption_evidence"
            context = limited_context(row, skills, "Limited or secondary skill evidence; not a core KR RAG candidate by default.")
            rag_status = "manual_review_needed"
            reason = "Limited evidence remains outside high-confidence KR RAG candidates."
            false_positive_risk = "medium"
        elif original_status == "adoption_evidence_ready" and row.get("scoring_eligible") == "true":
            final_status = "adoption_evidence_ready"
            context = safe_context(row, skills)
            rag_status = "high_confidence"
            reason = "Single-role scoring-eligible evidence remains safe after v2.1 audit."
            false_positive_risk = "low"
        elif original_status == "cross_role_adoption_evidence" and has_substantive_skill_context(skills):
            final_status = "cross_role_adoption_evidence"
            context = safe_context(row, skills)
            rag_status = "supporting_context_only"
            reason = "Cross-role evidence is useful for role context, but not promoted to high-confidence without manual metadata."
            false_positive_risk = "low"
        else:
            final_status = "limited_adoption_evidence"
            context = limited_context(row, skills, "Direct skills exist, but role/application context is not strong enough for high-confidence RAG.")
            rag_status = "manual_review_needed"
            reason = "Downgraded to limited evidence."
            false_positive_risk = "medium"

    context_claim_safe = bool(context and skills and rag_status in {"high_confidence", "supporting_context_only", "manual_review_needed"})
    if final_status in {"excluded", "insufficient_evidence"}:
        context_claim_safe = False

    audited = dict(row)
    audited["v2_adoption_evidence_status"] = original_status
    audited["adoption_evidence_status"] = final_status
    audited["verified_adoption_skills_v2"] = row.get("verified_adoption_skills", "")
    audited["verified_adoption_skills"] = "; ".join(skills)
    audited["adoption_context_v2"] = row.get("adoption_context", "")
    audited["adoption_context"] = context
    audited["adoption_evidence_excerpt"] = " | ".join(detail["excerpt"] for detail in details if detail["skill"] in skills)[:1200]
    audited["adoption_skill_verification_detail"] = " | ".join(
        f"{detail['skill']}:direct_body_confirmed:{detail['excerpt']}" for detail in details if detail["skill"] in skills
    )
    audited["rag_candidate_status"] = rag_status
    audited["rag_candidate_reason"] = reason
    audited["context_claim_safe"] = str(context_claim_safe).lower()
    audited["false_positive_risk"] = false_positive_risk
    audited["manual_metadata_priority"] = manual_priority(audited)
    audited["v21_change_type"] = change_type
    return audited


def apply_row_skill_guardrails(row: dict[str, str], skills: list[str]) -> list[str]:
    skill_set = set(skills)
    text = evidence_text(row)
    if row["source_posting_id"] == "kr_manual_0012":
        skill_set -= {"Vector Database", "Embedding"}
    if row["source_posting_id"] == "kr_manual_0007":
        skill_set -= {"RAG", "Vector Database", "Embedding"}
    if re.search(r"전공|학과|수학\s*/\s*통계|수학|통계학", text) and not re.search(r"통계\s*(?:분석|모델|검정|실험|지표)|statistical\s*(?:analysis|model)", text, re.I):
        skill_set.discard("Statistics")
    if re.search(r"qa|test|테스트|검증|품질", text, re.I) and not re.search(r"llm|rag|api|vector|벡터|데이터\s*파이프라인", text, re.I):
        skill_set.discard("Automation")
        skill_set.discard("Python")
    return sorted(skill_set)


def detect_direct_skills(text: str) -> tuple[list[str], list[dict[str, str]]]:
    skills = []
    details = []
    for skill, patterns in SKILL_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.I)
            if match:
                skills.append(skill)
                details.append({"skill": skill, "excerpt": excerpt(text, match.start(), match.end())})
                break
    return sorted(set(skills)), details


def has_substantive_skill_context(skills: list[str]) -> bool:
    substantive = {
        "RAG",
        "Vector Database",
        "Embedding",
        "LLM",
        "OpenAI API",
        "FastAPI",
        "LangChain",
        "LangGraph",
        "Docker",
        "Model Serving",
        "Data Pipeline",
        "Airflow",
        "ETL",
        "Agent",
        "LLMOps",
        "API",
        "REST API",
    }
    return bool(substantive & set(skills))


def safe_context(row: dict[str, str], skills: list[str]) -> str:
    skill_set = set(skills)
    role = row.get("primary_role") or "복합 역할"
    related = parse_semicolon(row.get("related_roles", ""))
    role_text = f"{role}와 {', '.join(related)} 경계" if related else role
    title = row.get("title", "")

    if row["source_posting_id"] == "kr_manual_0012":
        return "국내 AI 서비스 백엔드 역할에서 REST API와 LLM/RAG 파이프라인 구축, OpenAI API 연동 경험이 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0023":
        return "국내 AI MLOps 역할에서 RAG 파이프라인 운영, VectorDB 관리, 임베딩·하이브리드 검색 최적화, ETL/Airflow 경험이 함께 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0027":
        return "국내 Data Engineer 역할에서 LLM/RAG/Agent 서비스를 위한 Vector Store 구축과 ETL/Airflow 기반 데이터 파이프라인 역량이 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0051":
        return "국내 AI Backend 역할에서 LLM/RAG 파이프라인, FastAPI 기반 백엔드 연계, Vector DB, API 라우팅·서빙 경험이 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0022":
        return "국내 AI DevOps/백엔드 역할에서 AI 애플리케이션 백엔드 개발, LLM Gateway, API 설계, Docker 컨테이너화와 배포 운영 경험이 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0025":
        return "국내 AI 서비스 개발 역할에서 Python AI/ML 모델과 Java 백엔드 연동, API 설계, 모델 서빙·추론 환경 운영이 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0043":
        return "국내 Data & Analytics Engineer 역할에서 데이터 통합 파이프라인, AI 에이전트용 데이터 자산화, RAG 아키텍처용 Vector DB 구축이 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0017":
        return "국내 AI 전환 백엔드 역할에서 LLM/RAG/MCP/멀티 에이전트 서비스 개발과 Vector DB, Kafka, Airflow, Spark 활용이 함께 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0020":
        return "국내 AI 지식그래프/온톨로지 개발 역할에서 LLM 기반 API 개발과 검색 API 구현 경험이 요구됩니다."
    if row["source_posting_id"] == "kr_manual_0001":
        return "국내 마케팅 자동화 개발 역할에서 Python 기반 자동화, LLM 연동, LangChain/LangGraph와 Prompt Engineering 활용 경험이 요구됩니다."

    if {"RAG", "Vector Database", "Embedding", "Retrieval"} & skill_set:
        used = ", ".join(skill for skill in ["RAG", "Vector Database", "Embedding", "Retrieval"] if skill in skill_set)
        return f"국내 {role_text} 공고에서 {used} 기술이 본문 업무 또는 경험 요구로 직접 확인됩니다."
    if {"LLM", "OpenAI API", "LangChain", "LangGraph", "Agent"} & skill_set:
        used = ", ".join(skill for skill in ["LLM", "OpenAI API", "LangChain", "LangGraph", "Agent"] if skill in skill_set)
        return f"국내 {role_text} 공고에서 {used} 기반 서비스 구현 또는 운영 경험이 요구됩니다."
    if {"Data Pipeline", "Airflow", "ETL", "Spark"} & skill_set:
        used = ", ".join(skill for skill in ["Data Pipeline", "Airflow", "ETL", "Spark"] if skill in skill_set)
        return f"국내 {role_text} 공고에서 {used} 기반 데이터 처리 업무가 요구됩니다."
    used = ", ".join(skills[:5])
    return f"국내 {role_text} 공고에서 {used} 기술이 본문 직접 근거로 확인됩니다."


def limited_context(row: dict[str, str], skills: list[str], reason: str) -> str:
    if not skills:
        return ""
    return f"제한적 국내 적용 근거입니다. {', '.join(skills[:4])} 직접 언급은 있으나 핵심 기술 카드로 쓰기에는 약합니다. 판단 사유: {reason}"


def manual_priority(row: dict[str, str]) -> str:
    if row["rag_candidate_status"] == "high_confidence":
        return "high"
    if row["rag_candidate_status"] == "supporting_context_only":
        return "medium"
    if row["rag_candidate_status"] == "manual_review_needed":
        return "medium"
    return "none"


def build_matrix(global_rows: list[dict[str, str]], audited_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    global_index = v1.skill_role_index(global_rows, "verified_skills")
    kr_index = defaultdict(lambda: {"primary_roles": Counter(), "related_roles": Counter(), "posting_ids": set(), "companies": set(), "contexts": [], "titles": []})
    for row in audited_rows:
        if row["rag_candidate_status"] != "high_confidence":
            continue
        for skill in parse_semicolon(row["verified_adoption_skills"]):
            data = kr_index[skill]
            data["posting_ids"].add(row["source_posting_id"])
            if row.get("company"):
                data["companies"].add(row["company"])
            if row.get("primary_role"):
                data["primary_roles"][row["primary_role"]] += 1
            for role in parse_semicolon(row.get("related_roles", "")):
                data["related_roles"][role] += 1
            data["contexts"].append(row["adoption_context"])
            data["titles"].append(row["title"])

    rows = []
    for skill in sorted(set(global_index) | set(kr_index)):
        global_count = len(global_index[skill]["posting_ids"]) if skill in global_index else 0
        kr_count = len(kr_index[skill]["posting_ids"]) if skill in kr_index else 0
        if global_count and kr_count >= 3:
            status = "domestic_application_observed"
        elif global_count and kr_count:
            status = "domestic_application_limited"
        elif kr_count and skill in MAPPING_PENDING_SKILLS:
            status = "domestic_observed_global_mapping_pending"
        elif kr_count:
            status = "domestic_specific_signal"
        else:
            status = "global_signal_only"
        rows.append(
            {
                "canonical_skill": skill,
                "global_roles": "; ".join(sorted(global_index[skill]["roles"])) if skill in global_index else "",
                "global_verified_posting_count": str(global_count),
                "global_verified_company_count_if_available": str(len(global_index[skill]["companies"])) if skill in global_index else "0",
                "kr_primary_roles": "; ".join(role for role, _ in kr_index[skill]["primary_roles"].most_common()) if skill in kr_index else "",
                "kr_related_roles": "; ".join(role for role, _ in kr_index[skill]["related_roles"].most_common()) if skill in kr_index else "",
                "kr_verified_posting_count": str(kr_count),
                "kr_company_count_if_available": str(len(kr_index[skill]["companies"])) if skill in kr_index else "0",
                "domestic_adoption_status": status,
                "time_lag_analysis_possible": "false",
                "domestic_application_context": " | ".join(dict.fromkeys(kr_index[skill]["contexts"][:3])) if skill in kr_index else "",
                "kr_title_samples": " | ".join(kr_index[skill]["titles"][:5]) if skill in kr_index else "",
                "evidence_note": "URL/published_at missing; KR domestic application can be observed, but time-lag diffusion cannot be claimed.",
            }
        )
    return rows


def build_report(v2_rows: list[dict[str, str]], audited_rows: list[dict[str, str]], matrix_rows: list[dict[str, str]]) -> str:
    v2_status = Counter(row["adoption_evidence_status"] for row in v2_rows)
    v21_status = Counter(row["adoption_evidence_status"] for row in audited_rows)
    rag_status = Counter(row["rag_candidate_status"] for row in audited_rows)
    change_status = Counter(row["v21_change_type"] for row in audited_rows)
    v2_cross = [row for row in v2_rows if row["adoption_evidence_status"] == "cross_role_adoption_evidence"]
    v2_cross_ids = {row["source_posting_id"] for row in v2_cross}
    v21_cross_high = sum(row["source_posting_id"] in v2_cross_ids and row["rag_candidate_status"] == "high_confidence" for row in audited_rows)
    matrix = {row["canonical_skill"]: row for row in matrix_rows}

    lines = [
        "# KR Domestic Adoption v2.1 Quality Gate Report",
        "",
        "## Scope",
        "",
        "- v2 separation between role scoring and KR domestic adoption evidence is preserved.",
        "- v2.1 removes over-recovered evidence, state conflicts, and exaggerated adoption context.",
        "- GLOBAL remains `leading_signal`; KR remains `domestic_adoption`.",
        "- KR and GLOBAL counts are not merged into one market score.",
        "- URL and published date are missing, so time-lag diffusion is not claimed.",
        "",
        "## v2 Status Distribution",
        "",
    ]
    for key, count in v2_status.items():
        lines.append(f"- {key}: {count}")

    lines.extend(["", "## v2.1 Quality Gate Distribution", ""])
    for key, count in v21_status.items():
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## RAG Candidate Status", ""])
    for key, count in rag_status.items():
        lines.append(f"- {key}: {count}")
    lines.extend(
        [
            "",
            "## Change Summary",
            "",
            f"- Maintained: {change_status.get('maintained', 0)}",
            f"- Downgraded: {change_status.get('downgraded', 0)}",
            f"- Excluded: {change_status.get('excluded', 0)}",
            f"- Cleaned state conflict: {change_status.get('cleaned_state_conflict', 0)}",
            f"- Existing cross_role_adoption_evidence high_confidence retained: {v21_cross_high} / {len(v2_cross)}",
            "",
            "## State Conflicts Fixed",
            "",
            "- Excluded rows now have empty `verified_adoption_skills` and empty `adoption_context`.",
            "- Insufficient rows no longer emit generic adoption-context sentences.",
            "- Limited rows are marked as weak evidence and are not high-confidence RAG candidates.",
            "- QA/test automation is excluded from Builder domestic adoption evidence.",
            "- Degree/major terms such as math/statistics are not treated as applied Statistics evidence.",
            "- Search engine roles are not expanded into RAG, Vector Database, or Embedding without direct text evidence.",
            "",
            "## Required Skill Final Judgment",
            "",
            "| Skill | v2.1 KR Count | Status | KR Primary Roles | Final Context |",
            "|---|---:|---|---|---|",
        ]
    )
    for skill in [
        "RAG",
        "Vector Database",
        "Embedding",
        "Retrieval",
        "LLM",
        "API",
        "FastAPI",
        "LangChain",
        "LangGraph",
        "Docker",
        "Model Serving",
        "Data Pipeline",
        "Airflow",
        "ETL",
        "React",
        "Statistics",
        "Generative AI",
        "Agent",
        "LLMOps",
    ]:
        row = matrix.get(skill, {})
        lines.append(
            f"| {skill} | {row.get('kr_verified_posting_count', '0')} | {row.get('domestic_adoption_status', 'global_signal_only')} | {row.get('kr_primary_roles', '')} | {md(row.get('domestic_application_context', ''))} |"
        )

    high = [row for row in audited_rows if row["rag_candidate_status"] == "high_confidence"]
    excluded = [row for row in audited_rows if row["rag_candidate_status"] == "exclude_from_rag"]
    lines.extend(
        [
            "",
            "## High-Confidence KR RAG Candidates",
            "",
            "| ID | Title | Primary Role | Related Roles | Skills | Safe Context |",
            "|---|---|---|---|---|---|",
        ]
    )
    for row in high:
        lines.append(
            f"| {row['source_posting_id']} | {md(row['title'])} | {row['primary_role']} | {row['related_roles']} | {row['verified_adoption_skills']} | {md(row['adoption_context'])} |"
        )

    lines.extend(
        [
            "",
            "## Excluded From RAG",
            "",
            "| ID | Title | v2 Status | v2.1 Status | Reason |",
            "|---|---|---|---|---|",
        ]
    )
    for row in excluded:
        lines.append(
            f"| {row['source_posting_id']} | {md(row['title'])} | {row['v2_adoption_evidence_status']} | {row['adoption_evidence_status']} | {md(row['rag_candidate_reason'])} |"
        )

    lines.extend(
        [
            "",
            "## Manual Metadata Priority TOP 10",
            "",
            "| Priority | ID | Title | Company | Reason |",
            "|---:|---|---|---|---|",
        ]
    )
    high_by_id = {row["source_posting_id"]: row for row in high}
    priority_rows = [high_by_id[posting_id] for posting_id in HIGH_CONFIDENCE_REVIEW_ORDER if posting_id in high_by_id]
    priority_rows.extend([row for row in high if row["source_posting_id"] not in HIGH_CONFIDENCE_REVIEW_ORDER])
    for idx, row in enumerate(priority_rows[:10], 1):
        lines.append(
            f"| {idx} | {row['source_posting_id']} | {md(row['title'])} | {row.get('company', '')} | URL and published_at are required before time-lag analysis. |"
        )

    lines.extend(
        [
            "",
            "## Agent Policy",
            "",
            "- GLOBAL leading signal: use overseas evidence to explain where the skill is observed first or strongly.",
            "- KR domestic adoption: use only v2.1 high-confidence KR candidates to explain how the skill appears in Korean work requirements.",
            "- Supporting-context rows may help role narratives, but should not be used as core skill cards.",
            "- User action: translate GLOBAL signal and KR adoption into an implementation portfolio task.",
            "- KR/GLOBAL counts remain separate and are not summed.",
            "",
            "## Safety Confirmation",
            "",
            "- No DB modification, DB read, ATS network collection, OpenAI call, embedding generation, RAG save, JobRoleSkillEvidence recalculation, recommendation API change, or frontend change was performed.",
        ]
    )
    return "\n".join(lines) + "\n"


def evidence_text(row: dict[str, str]) -> str:
    return v1.normalize_text(
        " ".join(
            [
                row.get("responsibilities", ""),
                row.get("requirements", ""),
                row.get("preferred_qualifications", ""),
            ]
        )
    )


def excerpt(text: str, start: int, end: int, radius: int = 90) -> str:
    return v1.excerpt(text, start, end, radius)


def parse_semicolon(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def quality_fields() -> list[str]:
    return [
        "source_posting_id",
        "company",
        "company_needs_manual_fill",
        "title",
        "responsibilities",
        "requirements",
        "preferred_qualifications",
        "reference_skills",
        "search_keyword",
        "job_url",
        "url_needs_manual_fill",
        "published_at",
        "published_at_needs_manual_fill",
        "source",
        "source_market",
        "market_region",
        "evidence_purpose",
        "language",
        "parser_version",
        "previous_evidence_status",
        "previous_evidence_quality",
        "v2_adoption_evidence_status",
        "primary_role",
        "related_roles",
        "role_boundary_type",
        "adoption_evidence_status",
        "scoring_eligible",
        "verified_adoption_skills_v2",
        "verified_adoption_skills",
        "adoption_context_v2",
        "adoption_context",
        "adoption_evidence_excerpt",
        "adoption_skill_verification_detail",
        "rag_candidate_status",
        "rag_candidate_reason",
        "context_claim_safe",
        "false_positive_risk",
        "manual_metadata_priority",
        "time_lag_analysis_possible",
        "url_missing",
        "published_at_missing",
        "v21_change_type",
    ]


def matrix_fields() -> list[str]:
    return [
        "canonical_skill",
        "global_roles",
        "global_verified_posting_count",
        "global_verified_company_count_if_available",
        "kr_primary_roles",
        "kr_related_roles",
        "kr_verified_posting_count",
        "kr_company_count_if_available",
        "domestic_adoption_status",
        "time_lag_analysis_possible",
        "domestic_application_context",
        "kr_title_samples",
        "evidence_note",
    ]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def md(value: str) -> str:
    return (value or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
