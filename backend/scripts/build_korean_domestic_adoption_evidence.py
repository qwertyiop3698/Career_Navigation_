from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT_GLOB = "한국 구인공고 일부- 시트1.csv"
DEFAULT_GLOBAL = (
    ROOT_DIR
    / "data"
    / "exports"
    / "additional_batches"
    / "external_job_postings_role_evidence_v4_evidence_boost_20260529_01_parserfix_v2.csv"
)
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "exports" / "korean_batches"
VERSION = "kr_v1"
PARSER_VERSION = "role_evidence_parser_v2_kr"

TARGET_ROLES = [
    "AI Backend Developer",
    "Backend Developer",
    "Builder",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Frontend Developer",
]

ROLE_CORE_SKILLS = {
    "AI Backend Developer": [
        "Python", "FastAPI", "API", "LLM", "RAG", "Retrieval", "Embedding",
        "Vector Database", "LangChain", "LangGraph", "OpenAI API", "PostgreSQL",
        "Docker",
    ],
    "Backend Developer": [
        "Java", "Spring", "Python", "FastAPI", "API", "REST API", "PostgreSQL",
        "MySQL", "Docker", "AWS", "Redis",
    ],
    "Builder": [
        "Python", "API", "OpenAI API", "LangChain", "LangGraph", "LLM",
        "Automation", "RPA", "Full Stack", "React", "TypeScript", "FastAPI",
    ],
    "Data Analyst": [
        "SQL", "Python", "Tableau", "Power BI", "Dashboard", "Reporting",
        "Analytics", "Metrics", "GA", "Excel",
    ],
    "Data Engineer": [
        "Python", "SQL", "Spark", "Airflow", "ETL", "Data Pipeline",
        "Data Warehouse", "Kafka", "AWS", "PostgreSQL",
    ],
    "Data Scientist": [
        "Python", "Machine Learning", "Deep Learning", "Statistics",
        "Prediction Model", "Algorithm", "Model Training", "Model Evaluation",
        "PyTorch", "TensorFlow",
    ],
    "Frontend Developer": [
        "React", "TypeScript", "JavaScript", "Next.js", "HTML", "CSS",
        "UI", "Design System",
    ],
}

ROLE_SECONDARY_SKILLS = {
    "AI Backend Developer": ["AWS", "MySQL", "NoSQL", "Prompt Engineering", "Machine Learning"],
    "Backend Developer": ["LLM", "AWS", "NoSQL", "Kubernetes", "Machine Learning"],
    "Builder": ["AWS", "Docker", "MySQL", "PostgreSQL", "NoSQL", "Prompt Engineering"],
    "Data Analyst": ["Machine Learning", "Spark"],
    "Data Engineer": ["Docker", "Kubernetes", "Machine Learning", "LLM"],
    "Data Scientist": ["LLM", "RAG", "Spark", "AWS"],
    "Frontend Developer": ["Node.js", "Python", "AWS"],
}

SKILL_PATTERNS = {
    "Generative AI": [r"생성형\s*ai", r"generative\s*ai"],
    "LLM": [r"\bllm\b", r"거대언어모델", r"대규모\s*언어\s*모델", r"large language model"],
    "RAG": [r"\brag\b", r"검색\s*증강\s*생성", r"retrieval[- ]augmented"],
    "Retrieval": [r"검색\s*(시스템|api|엔진|기반)", r"\bretrieval\b"],
    "Embedding": [r"임베딩", r"\bembedding(s)?\b"],
    "Vector Database": [r"벡터\s*(db|database|데이터베이스)", r"vector\s*(db|database)"],
    "LangChain": [r"langchain", r"랭체인"],
    "LangGraph": [r"langgraph", r"랭그래프"],
    "OpenAI API": [r"openai\s*api", r"오픈ai\s*api"],
    "Prompt Engineering": [r"prompt engineering", r"프롬프트\s*엔지니어링"],
    "FastAPI": [r"fastapi"],
    "API": [r"\bapi\b", r"api\s*(서버|개발|연동|구현|설계)"],
    "REST API": [r"rest\s*api"],
    "Python": [r"python", r"파이썬"],
    "Java": [r"(?<!script)java(?!script)", r"자바(?!스크립트)"],
    "Spring": [r"spring\s*boot", r"spring", r"스프링"],
    "JavaScript": [r"javascript", r"자바스크립트"],
    "TypeScript": [r"typescript", r"타입스크립트"],
    "React": [r"react", r"리액트"],
    "Next.js": [r"next\.?js"],
    "HTML": [r"\bhtml\b"],
    "CSS": [r"\bcss\b"],
    "UI": [r"\bui\b", r"사용자\s*인터페이스"],
    "Design System": [r"design system", r"디자인\s*시스템"],
    "PostgreSQL": [r"postgresql", r"postgres"],
    "MySQL": [r"mysql"],
    "NoSQL": [r"nosql", r"mongo\s*db", r"mongodb"],
    "Redis": [r"redis"],
    "Docker": [r"docker", r"도커"],
    "AWS": [r"\baws\b", r"amazon web services"],
    "Kubernetes": [r"kubernetes", r"\bk8s\b", r"쿠버네티스"],
    "Automation": [r"업무\s*자동화", r"프로세스\s*자동화", r"자동화\s*(솔루션|시스템|도구|툴)", r"automation"],
    "RPA": [r"\brpa\b"],
    "Full Stack": [r"full[- ]?stack", r"풀스택"],
    "SQL": [r"\bsql\b"],
    "Tableau": [r"tableau", r"태블로"],
    "Power BI": [r"power\s*bi", r"파워\s*bi"],
    "Dashboard": [r"dashboard", r"대시보드"],
    "Reporting": [r"reporting", r"리포팅", r"보고서"],
    "Analytics": [r"analytics", r"데이터\s*분석", r"분석"],
    "Metrics": [r"metrics", r"지표", r"kpi"],
    "GA": [r"\bga4?\b", r"google analytics", r"구글\s*애널리틱스"],
    "Excel": [r"excel", r"엑셀"],
    "Spark": [r"spark", r"스파크"],
    "Airflow": [r"airflow", r"에어플로우"],
    "ETL": [r"\betl\b", r"\belt\b"],
    "Data Pipeline": [r"데이터\s*파이프라인", r"data pipeline"],
    "Data Warehouse": [r"데이터\s*웨어하우스", r"data warehouse", r"\bdw\b"],
    "Kafka": [r"kafka", r"카프카"],
    "Machine Learning": [r"machine learning", r"머신러닝", r"기계학습"],
    "Deep Learning": [r"deep learning", r"딥러닝"],
    "Statistics": [r"통계", r"statistics", r"statistical"],
    "Prediction Model": [r"예측\s*모델", r"prediction model", r"predictive model"],
    "Algorithm": [r"알고리즘", r"algorithm"],
    "Model Training": [r"모델\s*(학습|훈련)", r"model training"],
    "Model Evaluation": [r"모델\s*(평가|검증)", r"model evaluation"],
    "PyTorch": [r"pytorch", r"파이토치"],
    "TensorFlow": [r"tensorflow", r"텐서플로"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build KR domestic adoption evidence from manually collected job CSV.")
    parser.add_argument("--input", type=Path, default=None)
    parser.add_argument("--global-input", type=Path, default=DEFAULT_GLOBAL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = args.input or find_default_input()
    raw_rows, raw_fields = read_csv_flexible(input_path)
    normalized = [normalize_row(row, index) for index, row in enumerate(raw_rows, start=1)]
    assessed = [assess_role(row) for row in normalized]
    accepted = [row for row in assessed if row["evidence_status"] == "accepted"]
    review = [row for row in assessed if row["evidence_status"] != "accepted"]
    v4_rows, audit_rows = build_v4(assessed)
    global_rows = read_csv(args.global_input)
    matrix_rows = build_global_kr_matrix(global_rows, v4_rows)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "normalized": args.output_dir / f"korean_job_postings_normalized_{VERSION}.csv",
        "v3": args.output_dir / f"korean_job_postings_role_evidence_v3_{VERSION}.csv",
        "review": args.output_dir / f"korean_job_postings_role_evidence_review_v3_{VERSION}.csv",
        "v4": args.output_dir / f"korean_job_postings_role_evidence_v4_{VERSION}.csv",
        "audit": args.output_dir / f"korean_job_postings_role_evidence_removed_or_unverified_v4_{VERSION}.csv",
        "report": args.output_dir / f"korean_domestic_adoption_report_{VERSION}.md",
        "matrix": args.output_dir / f"global_to_korean_skill_adoption_matrix_{VERSION}.csv",
    }
    write_csv(paths["normalized"], list(normalized[0].keys()) if normalized else [], normalized)
    write_csv(paths["v3"], list(accepted[0].keys()) if accepted else list(assessed[0].keys()), accepted)
    write_csv(paths["review"], list(review[0].keys()) if review else list(assessed[0].keys()), review)
    write_csv(paths["v4"], list(v4_rows[0].keys()) if v4_rows else [], v4_rows)
    write_csv(paths["audit"], list(audit_rows[0].keys()) if audit_rows else audit_fields(), audit_rows)
    write_csv(paths["matrix"], matrix_fields(), matrix_rows)
    paths["report"].write_text(build_report(input_path, raw_fields, normalized, assessed, v4_rows, matrix_rows), encoding="utf-8")
    print(json.dumps({name: str(path) for name, path in paths.items()}, ensure_ascii=False, indent=2))
    return 0


def find_default_input() -> Path:
    matches = list((ROOT_DIR / "data").glob(DEFAULT_INPUT_GLOB))
    if not matches:
        matches = list((ROOT_DIR / "data").glob("*구인공고*.csv"))
    if not matches:
        raise FileNotFoundError("Korean job posting CSV was not found under backend/data.")
    return matches[0]


def read_csv_flexible(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    for encoding in ["utf-8-sig", "cp949", "utf-8"]:
        try:
            with path.open("r", encoding=encoding, newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                return list(reader), list(reader.fieldnames or [])
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"Could not read {path}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def normalize_row(row: dict[str, str], index: int) -> dict[str, str]:
    title = value(row, "공고제목")
    company = extract_company(title)
    return {
        "source_posting_id": f"kr_manual_{index:04d}",
        "company": company,
        "company_needs_manual_fill": str(not bool(company)).lower(),
        "title": title,
        "responsibilities": normalize_text(value(row, "담당업무")),
        "requirements": normalize_text(value(row, "자격요건")),
        "preferred_qualifications": normalize_text(value(row, "우대사항")),
        "reference_skills": normalize_text(value(row, "스킬")),
        "search_keyword": value(row, "검색어"),
        "job_url": "",
        "url_needs_manual_fill": "true",
        "published_at": "",
        "published_at_needs_manual_fill": "true",
        "source": "manual_korean_job_posting",
        "source_market": "domestic",
        "market_region": "KR",
        "evidence_purpose": "domestic_adoption",
        "language": "ko",
        "parser_version": PARSER_VERSION,
    }


def extract_company(title: str) -> str:
    match = re.match(r"\s*\[([^\]]+)\]", title or "")
    return match.group(1).strip() if match else ""


def assess_role(row: dict[str, str]) -> dict[str, str]:
    text = evidence_text(row)
    title = row["title"]
    candidates = role_candidates(title, text)
    exclusion = exclusion_reason(title, text)
    if exclusion:
        status = "excluded"
        validated = ""
        reason = exclusion
        boundary = exclusion
    elif not candidates:
        status = "excluded"
        validated = ""
        reason = "No clear target role evidence for the seven supported roles."
        boundary = ""
    elif len(candidates) > 1 and boundary_is_strong(candidates):
        status = "review"
        validated = ""
        reason = "Multiple target-role contexts are present; manual role boundary review required."
        boundary = " vs ".join(role for role, _ in candidates[:3])
    else:
        role, score = candidates[0]
        if score < 2:
            status = "review"
            validated = ""
            reason = "Role signal is present but too weak for automatic acceptance."
            boundary = role
        else:
            status = "accepted"
            validated = role
            reason = f"Accepted based on direct Korean posting text signals for {role}."
            boundary = ""
    return {
        **row,
        "candidate_roles": "; ".join(f"{role}:{score}" for role, score in candidates),
        "validated_job_role_category": validated,
        "evidence_status": status,
        "evidence_reason": reason,
        "role_boundary_reason": boundary,
    }


def role_candidates(title: str, text: str) -> list[tuple[str, int]]:
    haystack = f"{title}\n{text}".lower()
    signals = {
        "AI Backend Developer": [
            r"llm", r"rag", r"langchain", r"langgraph", r"openai\s*api", r"fastapi",
            r"벡터\s*(db|데이터베이스)", r"ai\s*서비스", r"api\s*서버", r"생성형\s*ai",
        ],
        "Backend Developer": [
            r"백엔드", r"서버\s*개발", r"rest\s*api", r"spring", r"fastapi",
            r"postgresql", r"mysql", r"docker",
        ],
        "Builder": [
            r"업무\s*자동화", r"프로세스\s*자동화", r"\brpa\b", r"내부\s*(툴|도구|시스템)",
            r"mvp", r"프로토타입", r"풀스택", r"llm.*자동화", r"자동화\s*솔루션",
        ],
        "Data Analyst": [
            r"데이터\s*분석", r"지표", r"리포팅", r"대시보드", r"tableau", r"power\s*bi",
            r"\bsql\b.*분석", r"비즈니스\s*인사이트", r"ga4?",
        ],
        "Data Engineer": [
            r"데이터\s*엔지니어", r"데이터\s*파이프라인", r"\betl\b", r"airflow",
            r"spark", r"데이터\s*플랫폼", r"데이터\s*웨어하우스",
        ],
        "Data Scientist": [
            r"데이터\s*사이언티스트", r"머신러닝", r"딥러닝", r"모델\s*(개발|학습|평가)",
            r"예측\s*모델", r"알고리즘", r"pytorch", r"tensorflow",
        ],
        "Frontend Developer": [
            r"프론트엔드", r"frontend", r"react", r"typescript", r"javascript",
            r"next\.?js", r"ui\s*구현", r"웹\s*클라이언트",
        ],
    }
    output = []
    for role, patterns in signals.items():
        score = sum(1 for pattern in patterns if re.search(pattern, haystack, re.I))
        if score:
            output.append((role, score))
    return sorted(output, key=lambda item: (-item[1], TARGET_ROLES.index(item[0])))


def boundary_is_strong(candidates: list[tuple[str, int]]) -> bool:
    return len(candidates) > 1 and candidates[0][1] <= candidates[1][1] + 1


def exclusion_reason(title: str, text: str) -> str:
    haystack = f"{title}\n{text}".lower()
    if re.search(r"qa|test|테스트|검증", haystack) and re.search(r"자동화|python", haystack) and not re.search(r"api|llm|서비스|백엔드|데이터\s*분석", haystack):
        return "QA/test automation role; not accepted as Builder or target software role evidence."
    if re.search(r"데이터\s*(입력|운영|관리)", haystack) and not re.search(r"분석|sql|대시보드|지표", haystack):
        return "Data operation/entry context without analysis evidence."
    return ""


def build_v4(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    output = []
    audit = []
    for row in rows:
        verified = verify_skills(row) if row["evidence_status"] == "accepted" else empty_verification(row)
        quality = evidence_quality(row, verified)
        enriched = {
            **row,
            "verified_skills": "; ".join(verified["core"] + verified["secondary"]),
            "verified_core_skills": "; ".join(verified["core"]),
            "verified_secondary_skills": "; ".join(verified["secondary"]),
            "rejected_or_reference_only_skills": "; ".join(verified["rejected"]),
            "skill_verification_detail": json.dumps(verified["detail"], ensure_ascii=False),
            "verified_skill_evidence_excerpt": verified["excerpt"],
            "verification_text_source": "responsibilities_requirements_preferred",
            "evidence_quality": quality,
        }
        output.append(enriched)
        for item in verified["detail"]:
            if item["status"] not in {"verified_core", "verified_secondary"}:
                audit.append(audit_row(row, item))
    return output, audit


def empty_verification(row: dict[str, str]) -> dict:
    return {"core": [], "secondary": [], "rejected": parse_reference_skills(row), "detail": [], "excerpt": ""}


def verify_skills(row: dict[str, str]) -> dict:
    role = row["validated_job_role_category"]
    text = evidence_text(row)
    reference = set(parse_reference_skills(row))
    core = []
    secondary = []
    rejected = []
    detail = []
    for level, skills in [("verified_core", ROLE_CORE_SKILLS[role]), ("verified_secondary", ROLE_SECONDARY_SKILLS[role])]:
        for skill in skills:
            match = find_skill(skill, text)
            if match and skill not in core and skill not in secondary:
                target = core if level == "verified_core" else secondary
                target.append(skill)
                status = "direct_and_reference_confirmed" if skill in reference else level
                detail.append({
                    "skill": skill,
                    "status": level,
                    "reference_status": status,
                    "excerpt": excerpt(text, match.start(), match.end()),
                })
    verified = set(core + secondary)
    for skill in sorted(reference):
        if skill not in verified:
            rejected.append(skill)
            detail.append({
                "skill": skill,
                "status": "reference_only_rejected",
                "reference_status": "reference_only",
                "excerpt": "",
            })
    return {
        "core": core,
        "secondary": secondary,
        "rejected": rejected,
        "detail": detail,
        "excerpt": next((item["excerpt"] for item in detail if item["status"] in {"verified_core", "verified_secondary"} and item["excerpt"]), ""),
    }


def evidence_quality(row: dict[str, str], verified: dict) -> str:
    if row["evidence_status"] == "excluded":
        return "excluded"
    if row["evidence_status"] == "review":
        return "review_required"
    if verified["core"]:
        return "skill_evidence_ready"
    return "role_evidence_only"


def find_skill(skill: str, text: str):
    for pattern in SKILL_PATTERNS.get(skill, [re.escape(skill)]):
        match = re.search(pattern, text, re.I)
        if match:
            return match
    return None


def parse_reference_skills(row: dict[str, str]) -> list[str]:
    text = row.get("reference_skills", "")
    found = []
    for skill in SKILL_PATTERNS:
        if find_skill(skill, text) and skill not in found:
            found.append(skill)
    return found


def build_global_kr_matrix(global_rows: list[dict[str, str]], kr_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    global_index = skill_role_index(global_rows, source="global")
    kr_index = skill_role_index([row for row in kr_rows if row["evidence_quality"] == "skill_evidence_ready"], source="kr")
    skills = sorted(set(global_index) | set(kr_index))
    rows = []
    for skill in skills:
        global_item = global_index.get(skill, {})
        kr_item = kr_index.get(skill, {})
        global_count = len(global_item.get("posting_ids", set()))
        kr_count = len(kr_item.get("posting_ids", set()))
        if global_count and kr_count >= 3:
            status = "domestic_application_observed"
        elif global_count and kr_count:
            status = "domestic_application_limited"
        elif global_count:
            status = "global_signal_only"
        else:
            status = "domestic_specific_signal"
        rows.append({
            "canonical_skill": skill,
            "global_roles": "; ".join(sorted(global_item.get("roles", set()))),
            "global_verified_posting_count": str(global_count),
            "global_verified_company_count_if_available": str(len(global_item.get("companies", set()))),
            "kr_roles": "; ".join(sorted(kr_item.get("roles", set()))),
            "kr_verified_posting_count": str(kr_count),
            "kr_company_count_if_available": str(len(kr_item.get("companies", set()))),
            "domestic_adoption_status": status,
            "domestic_application_context": summarize_kr_context(skill, kr_rows),
            "evidence_note": "No URL or published_at in KR file; diffusion timing cannot be claimed.",
        })
    return rows


def skill_role_index(rows: list[dict[str, str]], source: str) -> dict[str, dict[str, set[str]]]:
    output: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"roles": set(), "posting_ids": set(), "companies": set()})
    for row in rows:
        skills = parse_semicolon(row.get("verified_skills", ""))
        role = row.get("validated_job_role_category") or row.get("job_role_category", "")
        posting_id = row.get("source_posting_id") or row.get("id", "")
        for skill in skills:
            output[skill]["roles"].add(role)
            output[skill]["posting_ids"].add(posting_id)
            if row.get("company"):
                output[skill]["companies"].add(row["company"])
    return output


def summarize_kr_context(skill: str, kr_rows: list[dict[str, str]]) -> str:
    contexts = []
    for row in kr_rows:
        if row["evidence_quality"] == "skill_evidence_ready" and skill in parse_semicolon(row["verified_skills"]):
            contexts.append(f"{row['validated_job_role_category']}: {row['title']}")
    return " | ".join(contexts[:3])


def build_report(input_path: Path, raw_fields: list[str], normalized: list[dict[str, str]], assessed: list[dict[str, str]], v4_rows: list[dict[str, str]], matrix_rows: list[dict[str, str]]) -> str:
    lines = [
        "# Korean Domestic Adoption Evidence Report",
        "",
        "## Scope",
        "",
        "- KR postings are not used to fill global sample shortages.",
        "- GLOBAL postings remain `leading_signal`; KR postings are `domestic_adoption` evidence.",
        "- Counts are not merged into one market score.",
        "- This dataset has no URL or published date, so diffusion timing cannot be claimed.",
        "",
        "## KR CSV Quality",
        "",
        f"- Input file: `{input_path.as_posix()}`",
        f"- Rows: {len(normalized)}",
        f"- Columns: {', '.join(field or 'Unnamed: 0' for field in raw_fields)}",
        f"- Company extracted: {sum(row['company_needs_manual_fill'] == 'false' for row in normalized)}",
        f"- Company needs manual fill: {sum(row['company_needs_manual_fill'] == 'true' for row in normalized)}",
        f"- URL missing: {sum(row['url_needs_manual_fill'] == 'true' for row in normalized)}",
        f"- Published date missing: {sum(row['published_at_needs_manual_fill'] == 'true' for row in normalized)}",
        "",
        "## Overall KR Evidence Status",
        "",
        f"- Accepted: {sum(row['evidence_status'] == 'accepted' for row in assessed)}",
        f"- Review: {sum(row['evidence_status'] == 'review' for row in assessed)}",
        f"- Excluded: {sum(row['evidence_status'] == 'excluded' for row in assessed)}",
        "",
        "Excluded rows are intentionally not forced into a target role. The role table below counts accepted/review rows by candidate role, while excluded rows are tracked at the overall dataset level.",
        "",
        "## KR Role Validation",
        "",
        "| Role | Candidate | Accepted | Review | Excluded | Skill-Ready | Role-Only |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for role in TARGET_ROLES:
        role_candidate = sum(role in row["candidate_roles"] for row in assessed)
        accepted = sum(row["validated_job_role_category"] == role and row["evidence_status"] == "accepted" for row in assessed)
        review = sum(role in row["candidate_roles"] and row["evidence_status"] == "review" for row in assessed)
        excluded = sum(role in row["candidate_roles"] and row["evidence_status"] == "excluded" for row in assessed)
        ready = sum(row["validated_job_role_category"] == role and row["evidence_quality"] == "skill_evidence_ready" for row in v4_rows)
        role_only = sum(row["validated_job_role_category"] == role and row["evidence_quality"] == "role_evidence_only" for row in v4_rows)
        lines.append(f"| {role} | {role_candidate} | {accepted} | {review} | {excluded} | {ready} | {role_only} |")

    lines.extend(["", "## KR Verified Core Skills", ""])
    for role in TARGET_ROLES:
        role_rows = [row for row in v4_rows if row["validated_job_role_category"] == role and row["evidence_quality"] == "skill_evidence_ready"]
        lines.extend([f"### {role}", "", "| Skill | Verified KR Postings |", "|---|---:|"])
        for skill, count in skill_counts(role_rows, "verified_core_skills").most_common(20):
            lines.append(f"| {skill} | {count} |")
        if not role_rows:
            lines.append("| No verified core skill evidence | 0 |")
        lines.append("")

    lines.extend(
        [
            "## Boundary Cases",
            "",
            "- AI Backend vs Builder: Python/LLM/API automation roles are kept as review when service backend and product automation signals are both strong.",
            "- AI Backend vs Data Scientist: model training/deep learning/research rows are not forced into AI Backend without API/service deployment context.",
            "- Data Analyst vs operation: data entry/operation-only rows are excluded unless SQL, dashboard, metrics, reporting, or analysis evidence exists.",
            "- Builder vs QA automation: test/verification automation is excluded or reviewed rather than counted as Builder skill evidence.",
            "",
            "## GLOBAL To KR Adoption Examples",
            "",
            "| Skill | Global Roles | KR Roles | KR Context | Status |",
            "|---|---|---|---|---|",
        ]
    )
    interesting = [row for row in matrix_rows if row["domestic_adoption_status"] in {"domestic_application_observed", "domestic_application_limited"}]
    for row in sorted(interesting, key=lambda item: (-int(item["kr_verified_posting_count"]), item["canonical_skill"]))[:25]:
        lines.append(
            f"| {row['canonical_skill']} | {md(row['global_roles'])} | {md(row['kr_roles'])} | "
            f"{md(row['domestic_application_context'])} | {row['domestic_adoption_status']} |"
        )

    global_only = [row["canonical_skill"] for row in matrix_rows if row["domestic_adoption_status"] == "global_signal_only"]
    lines.extend(
        [
            "",
            "## Global Signal Only In Current KR File",
            "",
            ", ".join(global_only[:50]) or "None",
            "",
            "## RAG Collection Design",
            "",
            "KR collection: `role_job_evidence_kr_v1`, source_market=`domestic`, evidence_purpose=`domestic_adoption`.",
            "GLOBAL collection: `role_job_evidence_global_v1`, source_market=`overseas`, evidence_purpose=`leading_signal`.",
            "",
            "Agent retrieval order should be: GLOBAL leading signal -> KR domestic adoption example -> user portfolio/roadmap recommendation.",
            "",
            "### KR Metadata Example",
            "",
            "```json",
            json.dumps({
                "collection": "role_job_evidence_kr_v1",
                "document_type": "job_posting_evidence",
                "source_market": "domestic",
                "market_region": "KR",
                "evidence_purpose": "domestic_adoption",
                "language": "ko",
                "job_role_category": "AI Backend Developer",
                "company": "",
                "title": "",
                "posting_url": "",
                "published_at": "",
                "verified_core_skills": ["FastAPI", "LLM", "RAG"],
                "verified_secondary_skills": ["Docker", "AWS"],
                "evidence_quality": "skill_evidence_ready",
                "parser_version": PARSER_VERSION,
                "source_posting_id": "kr_manual_0001",
            }, ensure_ascii=False, indent=2),
            "```",
            "",
            "### GLOBAL Metadata Example",
            "",
            "```json",
            json.dumps({
                "collection": "role_job_evidence_global_v1",
                "document_type": "job_posting_evidence",
                "source_market": "overseas",
                "market_region": "GLOBAL",
                "evidence_purpose": "leading_signal",
                "language": "en",
                "job_role_category": "AI Backend Developer",
                "verified_core_skills": ["LLM", "API", "Retrieval"],
                "evidence_quality": "skill_evidence_ready",
                "parser_version": "role_evidence_parser_v2",
            }, ensure_ascii=False, indent=2),
            "```",
            "",
            "## Data Fields To Manually Fill Next",
            "",
            "- Company name for rows without `[company]` in title.",
            "- Job URL for source traceability and later RAG citation.",
            "- Published date or at least collected date for future time-lag analysis.",
            "- Source platform, location, employment type, and seniority if available.",
        ]
    )
    return "\n".join(lines) + "\n"


def skill_counts(rows: list[dict[str, str]], field: str) -> Counter[str]:
    counts = Counter()
    for row in rows:
        counts.update(set(parse_semicolon(row.get(field, ""))))
    return counts


def audit_row(row: dict[str, str], item: dict[str, str]) -> dict[str, str]:
    return {
        "source_posting_id": row["source_posting_id"],
        "company": row["company"],
        "title": row["title"],
        "job_role_category": row["validated_job_role_category"],
        "skill": item["skill"],
        "skill_status": item["status"],
        "skill_reason": item.get("reference_status", ""),
        "evidence_excerpt": item.get("excerpt", ""),
        "reference_skills": row["reference_skills"],
    }


def audit_fields() -> list[str]:
    return ["source_posting_id", "company", "title", "job_role_category", "skill", "skill_status", "skill_reason", "evidence_excerpt", "reference_skills"]


def matrix_fields() -> list[str]:
    return [
        "canonical_skill", "global_roles", "global_verified_posting_count",
        "global_verified_company_count_if_available", "kr_roles", "kr_verified_posting_count",
        "kr_company_count_if_available", "domestic_adoption_status",
        "domestic_application_context", "evidence_note",
    ]


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def normalize_text(text: str) -> str:
    text = (text or "").replace("\u00a0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def evidence_text(row: dict[str, str]) -> str:
    return "\n".join([row["responsibilities"], row["requirements"], row["preferred_qualifications"]])


def excerpt(text: str, start: int, end: int, radius: int = 90) -> str:
    return " ".join(text[max(0, start - radius): min(len(text), end + radius)].split())[:240]


def parse_semicolon(text: str) -> list[str]:
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def md(text: str) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ")


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
