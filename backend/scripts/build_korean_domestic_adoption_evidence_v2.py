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


EXTRA_SKILL_PATTERNS = {
    "Analytics": [r"analytics", r"데이터\s*분석", r"지표\s*분석", r"통계\s*분석", r"ga\s*/\s*aa"],
    "OpenAI API": [r"openai\s*api", r"오픈\s*ai\s*api"],
    "LangGraph": [r"lang\s*graph", r"langgraph", r"랭\s*그래프"],
    "Vector Database": [r"vector\s*db", r"vectordb", r"vector\s*database", r"벡터\s*db", r"벡터\s*데이터베이스", r"vector\s*store"],
    "Embedding": [r"embedding", r"임베딩"],
    "Retrieval": [r"retrieval", r"검색\s*(?:최적화|시스템|api|엔진)?", r"하이브리드\s*검색"],
    "Model Serving": [r"model\s*serving", r"모델\s*서빙", r"서빙\s*(?:환경|시스템)"],
    "Inference Serving": [r"inference\s*serving", r"추론\s*(?:환경|서빙|시스템)", r"모델\s*추론"],
    "FastAPI": [r"fast\s*api", r"fastapi"],
    "CI/CD": [r"ci\s*/\s*cd", r"cicd"],
    "MCP": [r"\bmcp\b"],
    "LLMOps": [r"llmops", r"llm\s*ops"],
    "Agent": [r"\bagent\b", r"에이전트", r"멀티\s*에이전트"],
    "Snowflake": [r"snowflake"],
    "Databricks": [r"databricks"],
    "Airflow": [r"airflow", r"air\s*flow", r"에어\s*플로우"],
    "Data Pipeline": [r"data\s*pipeline", r"데이터\s*파이프라인", r"데이터\s*파이브라인"],
    "ETL": [r"\betl\b", r"\belt\b", r"etl\s*파이프라인", r"데이터\s*(?:수집|정제).*etl"],
    "Kafka": [r"kafka", r"카프카"],
}

ADOPTION_FOCUS_SKILLS = {
    "RAG",
    "FastAPI",
    "LangChain",
    "LangGraph",
    "Vector Database",
    "Embedding",
    "Docker",
    "Model Serving",
    "LLM",
    "API",
    "OpenAI API",
    "Retrieval",
    "Airflow",
    "Data Pipeline",
    "ETL",
    "React",
    "TypeScript",
    "Next.js",
    "PostgreSQL",
    "Inference Serving",
}

HIGH_VALUE_IDS = [
    "kr_manual_0001",
    "kr_manual_0012",
    "kr_manual_0017",
    "kr_manual_0020",
    "kr_manual_0022",
    "kr_manual_0023",
    "kr_manual_0025",
    "kr_manual_0027",
    "kr_manual_0043",
    "kr_manual_0044",
    "kr_manual_0051",
    "kr_manual_0058",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build KR domestic adoption evidence v2 without DB/network/API calls.")
    parser.add_argument("--normalized-input", default=str(KOREAN_DIR / "korean_job_postings_normalized_kr_v1.csv"))
    parser.add_argument("--v4-input", default=str(KOREAN_DIR / "korean_job_postings_role_evidence_v4_kr_v1.csv"))
    parser.add_argument("--global-input", default=str(GLOBAL_V4))
    parser.add_argument("--output-dir", default=str(KOREAN_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    normalized_rows = read_csv(Path(args.normalized_input))
    v1_rows = read_csv(Path(args.v4_input))
    global_rows = read_csv(Path(args.global_input))
    v1_by_id = {row["source_posting_id"]: row for row in v1_rows}

    adoption_rows = [build_adoption_row(row, v1_by_id.get(row["source_posting_id"], {})) for row in normalized_rows]
    matrix_rows = build_matrix(global_rows, adoption_rows)
    cross_rows = [row for row in adoption_rows if row["adoption_evidence_status"] == "cross_role_adoption_evidence"]

    paths = {
        "adoption": output_dir / "korean_job_postings_domestic_adoption_v2.csv",
        "review": output_dir / "korean_job_postings_domestic_adoption_review_v2.csv",
        "matrix": output_dir / "global_to_korean_skill_adoption_matrix_kr_v2.csv",
        "report": output_dir / "korean_domestic_adoption_report_kr_v2.md",
        "cross": output_dir / "korean_cross_role_adoption_cases_kr_v2.csv",
    }

    adoption_ready = [
        row
        for row in adoption_rows
        if row["adoption_evidence_status"]
        in {"adoption_evidence_ready", "cross_role_adoption_evidence", "limited_adoption_evidence"}
    ]
    adoption_review = [
        row
        for row in adoption_rows
        if row["adoption_evidence_status"] in {"insufficient_evidence", "excluded"}
    ]

    write_csv(paths["adoption"], adoption_fields(), adoption_ready)
    write_csv(paths["review"], adoption_fields(), adoption_review)
    write_csv(paths["matrix"], matrix_fields(), matrix_rows)
    write_csv(paths["cross"], adoption_fields(), cross_rows)
    paths["report"].write_text(build_report(adoption_rows, matrix_rows, global_rows), encoding="utf-8")

    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, indent=2))
    return 0


def build_adoption_row(row: dict[str, str], previous: dict[str, str]) -> dict[str, str]:
    text = evidence_text(row)
    detected = detect_skills(text)
    reference = set(v1.parse_reference_skills(row))
    details = []
    excerpts = []
    for skill in sorted(detected):
        status = "direct_and_reference_confirmed" if skill in reference else "direct_body_confirmed"
        ex = skill_excerpt(text, skill)
        details.append(f"{skill}:{status}:{ex}")
        excerpts.append(f"{skill}: {ex}")

    candidates = parse_candidate_roles(previous.get("candidate_roles", ""))
    if not candidates:
        candidates = infer_roles_from_text(text, detected)
    primary_role, related_roles = choose_roles(candidates, detected, row)
    boundary = role_boundary(primary_role, related_roles)
    status = adoption_status(row, previous, detected, primary_role, related_roles, text)
    scoring_eligible = (
        previous.get("evidence_status") == "accepted"
        and previous.get("evidence_quality") == "skill_evidence_ready"
        and status == "adoption_evidence_ready"
        and not related_roles
    )

    return {
        **row,
        "previous_evidence_status": previous.get("evidence_status", ""),
        "previous_evidence_quality": previous.get("evidence_quality", ""),
        "primary_role": primary_role,
        "related_roles": "; ".join(related_roles),
        "role_boundary_type": boundary,
        "adoption_evidence_status": status,
        "scoring_eligible": str(scoring_eligible).lower(),
        "adoption_context": adoption_context(primary_role, related_roles, detected, row),
        "verified_adoption_skills": "; ".join(sorted(detected)),
        "adoption_evidence_excerpt": " | ".join(excerpts[:8]),
        "adoption_skill_verification_detail": " | ".join(details),
        "time_lag_analysis_possible": "false",
        "url_missing": str(not bool(row.get("job_url"))).lower(),
        "published_at_missing": str(not bool(row.get("published_at"))).lower(),
    }


def adoption_status(
    row: dict[str, str],
    previous: dict[str, str],
    detected: set[str],
    primary_role: str,
    related_roles: list[str],
    text: str,
) -> str:
    if previous.get("evidence_status") == "excluded" and exclusion_still_applies(text):
        return "excluded"
    if not detected:
        return "insufficient_evidence"
    if not primary_role:
        return "limited_adoption_evidence"
    if related_roles:
        return "cross_role_adoption_evidence"
    if previous.get("evidence_status") == "review":
        return "limited_adoption_evidence"
    return "adoption_evidence_ready"


def exclusion_still_applies(text: str) -> bool:
    qa = re.search(r"qa|test|테스트|검증|품질", text, re.I)
    target = re.search(r"llm|rag|api|backend|백엔드|데이터\s*파이프라인|airflow|vector|벡터", text, re.I)
    operation_only = re.search(r"데이터\s*(?:입력|운영|관리)\b", text)
    return bool((qa and not target) or operation_only)


def detect_skills(text: str) -> set[str]:
    patterns = dict(v1.SKILL_PATTERNS)
    patterns.update(EXTRA_SKILL_PATTERNS)
    detected = set()
    for skill, skill_patterns in patterns.items():
        for pattern in skill_patterns:
            if re.search(pattern, text, flags=re.I):
                detected.add(skill)
                break
    if "JavaScript" in detected and "Java" in detected and not re.search(r"java(?!script)", text, flags=re.I):
        detected.discard("Java")
    return detected


def parse_candidate_roles(raw: str) -> list[str]:
    roles = []
    for item in v1.parse_semicolon(raw):
        role = item.split(":", 1)[0].strip()
        if role in v1.TARGET_ROLES and role not in roles:
            roles.append(role)
    return roles


def infer_roles_from_text(text: str, skills: set[str]) -> list[str]:
    roles = []
    if {"LLM", "RAG", "Vector Database", "Embedding", "OpenAI API", "LangChain", "LangGraph"} & skills:
        roles.append("AI Backend Developer")
    if {"API", "REST API", "Spring", "PostgreSQL", "MySQL", "Redis", "Docker"} & skills:
        roles.append("Backend Developer")
    if {"Airflow", "ETL", "Data Pipeline", "Spark", "Kafka", "Databricks", "Snowflake", "Vector Database"} & skills:
        roles.append("Data Engineer")
    if {"Machine Learning", "Deep Learning", "PyTorch", "TensorFlow", "Model Training"} & skills:
        roles.append("Data Scientist")
    if {"Analytics", "SQL", "Excel", "Power BI", "Tableau", "Metrics", "GA"} & skills:
        roles.append("Data Analyst")
    if {"React", "TypeScript", "JavaScript", "Next.js"} & skills:
        roles.append("Frontend Developer")
    if re.search(r"자동화|업무툴|프로토타입|프로토타이핑|mvp|fde|forward deployed|product engineer|end-to-end|현장\s*맞춤형|솔루션\s*커스터마이징", text, re.I):
        roles.append("Builder")
    return [role for role in v1.TARGET_ROLES if role in roles]


def choose_roles(candidates: list[str], skills: set[str], row: dict[str, str]) -> tuple[str, list[str]]:
    text = evidence_text(row)
    role_scores = {role: 0 for role in v1.TARGET_ROLES}
    for role in candidates:
        role_scores[role] += 2
    for skill in skills:
        for role, core in v1.ROLE_CORE_SKILLS.items():
            if skill in core:
                role_scores[role] += 2
        for role, secondary in v1.ROLE_SECONDARY_SKILLS.items():
            if skill in secondary:
                role_scores[role] += 1

    if re.search(r"rag|llm|langchain|langgraph|vector|벡터|openai", text, re.I):
        role_scores["AI Backend Developer"] += 3
    if {"RAG", "LLM", "OpenAI API", "Vector Database", "Embedding", "Retrieval", "Model Serving", "Inference Serving"} & skills:
        role_scores["AI Backend Developer"] += 3
    if re.search(r"airflow|etl|pipeline|파이프라인|databricks|snowflake", text, re.I):
        role_scores["Data Engineer"] += 3
    if {"Airflow", "ETL", "Data Pipeline", "Spark", "Kafka", "Databricks", "Snowflake"} & skills:
        role_scores["Data Engineer"] += 3
    if re.search(r"백엔드|backend|rest\s*api|api\s*(?:설계|개발|서버)", text, re.I):
        role_scores["Backend Developer"] += 2
    if re.search(r"모델\s*(?:학습|개발)|machine learning|deep learning|딥러닝|머신러닝", text, re.I):
        role_scores["Data Scientist"] += 2
    if re.search(r"dashboard|리포팅|지표|ga/aa|analytics|데이터\s*분석", text, re.I):
        role_scores["Data Analyst"] += 2
    if re.search(r"react|typescript|next\.?js|프론트", text, re.I):
        role_scores["Frontend Developer"] += 2
    if re.search(r"forward deployed|\bfde\b", text, re.I):
        role_scores["Builder"] += 8
    if re.search(r"자동화|업무툴|prototype|프로토타이핑|mvp|forward deployed|product engineer|end-to-end|현장\s*맞춤형|솔루션\s*커스터마이징", text, re.I):
        role_scores["Builder"] += 8

    ranked = [(role, score) for role, score in sorted(role_scores.items(), key=lambda item: (-item[1], item[0])) if score > 0]
    if not ranked:
        return "", []
    primary = ranked[0][0]
    related = [role for role, score in ranked[1:] if score >= max(2, ranked[0][1] - 3)]
    for role in candidates:
        if role != primary and role not in related:
            related.append(role)
    return primary, related[:4]


def role_boundary(primary: str, related: list[str]) -> str:
    if not primary or not related:
        return ""
    return f"{primary} vs {' vs '.join(related)}"


def adoption_context(primary: str, related: list[str], skills: set[str], row: dict[str, str]) -> str:
    role_label = primary or "복합 역할"
    if related:
        role_label = f"{primary}와 {', '.join(related)} 경계"
    if {"RAG", "Vector Database", "Embedding", "Retrieval"} & skills:
        return f"국내 {role_label} 공고에서 RAG 검색, 벡터 저장소, 임베딩/검색 최적화가 업무 요구로 관찰됩니다."
    if {"LLM", "OpenAI API", "LangChain", "LangGraph", "Agent"} & skills:
        return f"국내 {role_label} 공고에서 LLM 연동, 에이전트/워크플로우 구현, 생성형 AI 서비스 운영 요구가 관찰됩니다."
    if {"Airflow", "ETL", "Data Pipeline", "Spark"} & skills:
        return f"국내 {role_label} 공고에서 데이터 파이프라인과 AI 서비스 기반 데이터 처리 요구가 관찰됩니다."
    if {"API", "REST API", "FastAPI", "Docker", "Model Serving", "Inference Serving"} & skills:
        return f"국내 {role_label} 공고에서 API 구현, 배포/컨테이너화, 모델 서빙 운영 요구가 관찰됩니다."
    return f"국내 {role_label} 공고에서 {', '.join(sorted(skills)[:5])} 기술의 업무 적용이 본문에서 직접 확인됩니다."


def build_matrix(global_rows: list[dict[str, str]], adoption_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    global_index = v1.skill_role_index(global_rows, "verified_skills")
    kr_index = defaultdict(lambda: {"primary_roles": Counter(), "related_roles": Counter(), "posting_ids": set(), "companies": set(), "contexts": [], "titles": []})
    for row in adoption_rows:
        if row["adoption_evidence_status"] not in {
            "adoption_evidence_ready",
            "cross_role_adoption_evidence",
            "limited_adoption_evidence",
        }:
            continue
        for skill in v1.parse_semicolon(row["verified_adoption_skills"]):
            data = kr_index[skill]
            data["posting_ids"].add(row["source_posting_id"])
            if row.get("company"):
                data["companies"].add(row["company"])
            if row["primary_role"]:
                data["primary_roles"][row["primary_role"]] += 1
            for role in v1.parse_semicolon(row["related_roles"]):
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
        elif global_count:
            status = "global_signal_only"
        elif kr_count:
            status = "domestic_specific_signal"
        else:
            status = "metadata_missing_for_time_lag"
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
                "evidence_note": "URL/published_at missing; domestic application can be observed, but time-lag diffusion cannot be claimed.",
            }
        )
    return rows


def build_report(adoption_rows: list[dict[str, str]], matrix_rows: list[dict[str, str]], global_rows: list[dict[str, str]]) -> str:
    v1_status = Counter(row["previous_evidence_status"] for row in adoption_rows)
    status = Counter(row["adoption_evidence_status"] for row in adoption_rows)
    recovered_review = sum(
        row["previous_evidence_status"] == "review"
        and row["adoption_evidence_status"] in {"adoption_evidence_ready", "cross_role_adoption_evidence", "limited_adoption_evidence"}
        for row in adoption_rows
    )
    matrix_by_skill = {row["canonical_skill"]: row for row in matrix_rows}
    lines = [
        "# Korean Domestic Adoption Evidence Report v2",
        "",
        "## Scope Correction",
        "",
        "- v1 was intentionally conservative for role scoring, but it under-counted KR domestic adoption evidence from cross-role AI/data postings.",
        "- v2 separates `scoring_eligible` from `adoption_evidence_status`.",
        "- Review postings can now be used as KR domestic adoption evidence when the body directly mentions verified skills and business/engineering usage context.",
        "- GLOBAL counts and KR counts remain separate and are not merged into one market score.",
        "- URL and published date are still missing, so time-lag diffusion claims are not allowed.",
        "",
        "## v1 vs v2 Summary",
        "",
        f"- v1 accepted: {v1_status.get('accepted', 0)}",
        f"- v1 review: {v1_status.get('review', 0)}",
        f"- v1 excluded: {v1_status.get('excluded', 0)}",
        f"- v2 adoption_evidence_ready: {status.get('adoption_evidence_ready', 0)}",
        f"- v2 cross_role_adoption_evidence: {status.get('cross_role_adoption_evidence', 0)}",
        f"- v2 limited_adoption_evidence: {status.get('limited_adoption_evidence', 0)}",
        f"- v2 insufficient_evidence: {status.get('insufficient_evidence', 0)}",
        f"- v2 excluded: {status.get('excluded', 0)}",
        f"- scoring_eligible: {sum(row['scoring_eligible'] == 'true' for row in adoption_rows)}",
        f"- Existing review postings recovered as domestic adoption evidence: {recovered_review}",
        "",
        "## Required Skill Recheck",
        "",
        "| Skill | v2 KR Count | Status | KR Primary Roles | KR Context |",
        "|---|---:|---|---|---|",
    ]
    for skill in [
        "RAG",
        "FastAPI",
        "LangChain",
        "LangGraph",
        "Vector Database",
        "Embedding",
        "Docker",
        "Model Serving",
        "LLM",
        "API",
        "Retrieval",
        "Airflow",
        "Data Pipeline",
        "ETL",
        "React",
        "TypeScript",
        "Next.js",
        "PostgreSQL",
        "Inference Serving",
    ]:
        row = matrix_by_skill.get(skill, {})
        lines.append(
            f"| {skill} | {row.get('kr_verified_posting_count', '0')} | {row.get('domestic_adoption_status', 'global_signal_only')} | {row.get('kr_primary_roles', '')} | {md(row.get('domestic_application_context', ''))} |"
        )

    lines.extend(
        [
            "",
            "## High-Value Cross-Role Cases",
            "",
            "| ID | Title | Previous Status | Primary Role | Related Roles | Adoption Status | Scoring Eligible | Verified Adoption Skills | Context |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
    )
    rows_by_id = {row["source_posting_id"]: row for row in adoption_rows}
    for posting_id in HIGH_VALUE_IDS:
        row = rows_by_id.get(posting_id)
        if not row:
            continue
        lines.append(
            f"| {posting_id} | {md(row['title'])} | {row['previous_evidence_status']} | {row['primary_role']} | {row['related_roles']} | {row['adoption_evidence_status']} | {row['scoring_eligible']} | {row['verified_adoption_skills']} | {md(row['adoption_context'])} |"
        )

    lines.extend(
        [
            "",
            "## GLOBAL To KR To User Action Design",
            "",
            "- GLOBAL leading signal: explain which overseas roles require the skill.",
            "- KR domestic adoption: explain how Korean postings apply the same skill in cross-role work.",
            "- User action: recommend a portfolio task that proves the skill with implementation evidence.",
            "",
            "Example: GLOBAL AI Backend postings show Retrieval, LLM, and API signals. KR AI MLOps/Data Engineer postings show RAG, VectorDB, API integration, and data pipelines appearing together. User action should be a FastAPI + pgvector RAG API with pipeline/evaluation notes in README.",
            "",
            "## RAG Storage Policy Proposal",
            "",
            "- GLOBAL collection: `role_job_evidence_global_v1`, evidence_purpose=`leading_signal`.",
            "- KR collection: `role_job_evidence_kr_v2`, evidence_purpose=`domestic_adoption`.",
            "- KR RAG candidates: `adoption_evidence_ready` and `cross_role_adoption_evidence`.",
            "- KR metadata should include `scoring_eligible`, `primary_role`, `related_roles`, `role_boundary_type`, `verified_adoption_skills`, `adoption_context`, `url_missing`, and `published_at_missing`.",
            "- Skill score candidates should be limited to `scoring_eligible=true`; cross-role KR postings should be used for Agent explanations and adoption cards only.",
            "- KR and GLOBAL scores must not be summed.",
            "",
            "## Manual Metadata Fill Priority",
            "",
            "| Priority | ID | Title | Company | Missing Fields | Reason |",
            "|---:|---|---|---|---|---|",
        ]
    )
    priority_rows = sorted(
        [
            row
            for row in adoption_rows
            if row["adoption_evidence_status"] in {"adoption_evidence_ready", "cross_role_adoption_evidence"}
        ],
        key=lambda row: (row["source_posting_id"] not in HIGH_VALUE_IDS, -len(v1.parse_semicolon(row["verified_adoption_skills"]))),
    )[:10]
    for idx, row in enumerate(priority_rows, 1):
        lines.append(
            f"| {idx} | {row['source_posting_id']} | {md(row['title'])} | {row['company']} | URL, published_at | High-value domestic adoption evidence for {row['verified_adoption_skills']} |"
        )

    lines.extend(
        [
            "",
            "## Safety Confirmation",
            "",
            "- This script reads local CSV files only.",
            "- No DB read/write, ATS network collection, OpenAI call, embedding, RAG document save, JobRoleSkillEvidence rebuild, recommendation API change, or frontend change was performed.",
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


def adoption_fields() -> list[str]:
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
        "primary_role",
        "related_roles",
        "role_boundary_type",
        "adoption_evidence_status",
        "scoring_eligible",
        "adoption_context",
        "verified_adoption_skills",
        "adoption_evidence_excerpt",
        "adoption_skill_verification_detail",
        "time_lag_analysis_possible",
        "url_missing",
        "published_at_missing",
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


def skill_excerpt(text: str, skill: str, radius: int = 90) -> str:
    patterns = dict(v1.SKILL_PATTERNS)
    patterns.update(EXTRA_SKILL_PATTERNS)
    for pattern in patterns.get(skill, [re.escape(skill)]):
        match = re.search(pattern, text, flags=re.I)
        if match:
            return v1.excerpt(text, match.start(), match.end(), radius)
    return ""


if __name__ == "__main__":
    raise SystemExit(main())
