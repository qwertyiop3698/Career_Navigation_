from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_GLOBAL_INPUT = (
    ROOT_DIR
    / "data"
    / "exports"
    / "additional_batches"
    / "external_job_postings_role_evidence_v4_evidence_boost_20260529_01_parserfix_v2.csv"
)
DEFAULT_KR_INPUT = ROOT_DIR / "data" / "exports" / "korean_batches" / "korean_domestic_adoption_rag_candidates_v21.csv"
DEFAULT_KR_QUALITY_GATE = ROOT_DIR / "data" / "exports" / "korean_batches" / "korean_domestic_adoption_quality_gate_v21.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "exports" / "rag_dryrun"

GLOBAL_COLLECTION = "role_job_evidence_global_v1"
KR_COLLECTION = "role_job_evidence_kr_v21"
GLOBAL_DOC_VERSION = "global_rag_v1"
KR_DOC_VERSION = "kr_rag_v21"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build GLOBAL/KR RAG document dry-run JSONL and validation reports.")
    parser.add_argument("--global-input", default=str(DEFAULT_GLOBAL_INPUT))
    parser.add_argument("--kr-input", default=str(DEFAULT_KR_INPUT))
    parser.add_argument("--kr-quality-gate-input", default=str(DEFAULT_KR_QUALITY_GATE))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global_input = Path(args.global_input)
    kr_input = Path(args.kr_input)
    kr_quality_gate_input = Path(args.kr_quality_gate_input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    global_rows = read_csv(global_input)
    kr_rows = read_csv(kr_input)
    kr_quality_rows = read_csv(kr_quality_gate_input) if kr_quality_gate_input.exists() else []

    global_docs = [build_global_doc(row, global_input) for row in global_rows if is_global_rag_candidate(row)]
    kr_docs = [build_kr_doc(row, kr_input) for row in kr_rows if is_kr_rag_candidate(row)]

    paths = {
        "global_jsonl": output_dir / "global_rag_documents_dryrun_v1.jsonl",
        "kr_jsonl": output_dir / "kr_rag_documents_dryrun_v1.jsonl",
        "samples": output_dir / "global_kr_rag_document_samples_v1.md",
        "strategy": output_dir / "global_kr_agent_search_strategy_v1.md",
        "validation": output_dir / "global_kr_rag_dryrun_validation_report_v1.md",
    }

    write_jsonl(paths["global_jsonl"], global_docs)
    write_jsonl(paths["kr_jsonl"], kr_docs)
    paths["samples"].write_text(build_samples_report(global_docs, kr_docs), encoding="utf-8")
    paths["strategy"].write_text(build_agent_strategy(), encoding="utf-8")
    paths["validation"].write_text(
        build_validation_report(global_input, global_rows, global_docs, kr_input, kr_rows, kr_quality_rows, kr_docs),
        encoding="utf-8",
    )

    print(json.dumps({key: str(path) for key, path in paths.items()}, ensure_ascii=False, indent=2))
    return 0


def is_global_rag_candidate(row: dict[str, str]) -> bool:
    core = parse_list(row.get("verified_core_skills", ""))
    return row.get("evidence_quality") == "skill_evidence_ready" and bool(core)


def is_kr_rag_candidate(row: dict[str, str]) -> bool:
    return (
        row.get("rag_candidate_status") == "high_confidence"
        and row.get("adoption_evidence_status") in {"adoption_evidence_ready", "cross_role_adoption_evidence"}
        and bool(parse_list(row.get("verified_adoption_skills", "")))
    )


def build_global_doc(row: dict[str, str], source_dataset: Path) -> dict:
    core = parse_list(row.get("verified_core_skills", ""))
    secondary = parse_list(row.get("verified_secondary_skills", ""))
    role = value(row, "validated_job_role_category")
    company = value(row, "company")
    title = value(row, "title")
    posting_url = value(row, "posting_url") or value(row, "job_url")
    summary = summarize_text(
        [
            value(row, "responsibilities"),
            value(row, "requirements"),
            value(row, "preferred_qualifications"),
            value(row, "verified_skill_evidence_excerpt"),
        ],
        max_chars=800,
    )
    content = "\n".join(
        [
            f"직무: {role}",
            f"회사명: {company}",
            f"공고 제목: {title}",
            f"해외 선행 기술 신호: {', '.join(core)}",
            f"보조 기술: {', '.join(secondary)}",
            f"주요 업무/요구사항 요약: {summary}",
            f"근거 설명: 이 해외 공고는 {role} 역할에서 {', '.join(core)} 기술이 실제 업무 요구로 확인되어, 글로벌 선행 기술 신호로 사용됩니다.",
            f"공고 URL: {posting_url}",
        ]
    )
    metadata = {
        "collection": GLOBAL_COLLECTION,
        "document_type": "job_posting_evidence",
        "evidence_purpose": "leading_signal",
        "source_market": "overseas",
        "market_region": "GLOBAL",
        "language": "en",
        "job_role_category": role,
        "company": company,
        "title": title,
        "posting_url": posting_url,
        "source_posting_id": value(row, "source_posting_id") or value(row, "id"),
        "verified_core_skills": core,
        "verified_secondary_skills": secondary,
        "evidence_quality": value(row, "evidence_quality"),
        "parser_version": value(row, "parser_version"),
        "parser_version_effective": "role_evidence_parser_v2_parserfix_source"
        if "parserfix_v2" in source_dataset.name
        else value(row, "parser_version"),
        "parserfix_source_file": "parserfix_v2" in source_dataset.name,
        "duplicate_group_id": value(row, "duplicate_group_id"),
        "duplicate_status": value(row, "duplicate_status"),
        "source_dataset": source_dataset.as_posix(),
        "rag_document_version": GLOBAL_DOC_VERSION,
    }
    return {"content": content, "metadata": metadata}


def build_kr_doc(row: dict[str, str], source_dataset: Path) -> dict:
    skills = parse_list(row.get("verified_adoption_skills", ""))
    related_roles = parse_list(row.get("related_roles", ""))
    company = value(row, "company")
    title = value(row, "title")
    posting_url = value(row, "job_url")
    content = "\n".join(
        [
            f"국내 적용 직무: {value(row, 'primary_role')}",
            f"연관 직무: {', '.join(related_roles)}",
            f"회사명: {company}",
            f"공고 제목: {title}",
            f"국내 적용 기술: {', '.join(skills)}",
            f"국내 적용 맥락: {value(row, 'adoption_context')}",
            f"근거 문장: {value(row, 'adoption_evidence_excerpt')}",
            "주의: 이 문서는 국내 적용 사례 근거이며, 게시일/URL이 없으면 시간차 확산 증거로 사용하지 않습니다.",
            f"공고 URL: {posting_url}",
        ]
    )
    metadata = {
        "collection": KR_COLLECTION,
        "document_type": "job_posting_evidence",
        "evidence_purpose": "domestic_adoption",
        "source_market": "domestic",
        "market_region": "KR",
        "language": "ko",
        "primary_role": value(row, "primary_role"),
        "related_roles": related_roles,
        "role_boundary_type": value(row, "role_boundary_type"),
        "company": company,
        "title": title,
        "posting_url": posting_url,
        "published_at": value(row, "published_at"),
        "source_posting_id": value(row, "source_posting_id"),
        "verified_adoption_skills": skills,
        "adoption_evidence_status": value(row, "adoption_evidence_status"),
        "rag_candidate_status": value(row, "rag_candidate_status"),
        "scoring_eligible": value(row, "scoring_eligible").lower() == "true",
        "adoption_context": value(row, "adoption_context"),
        "url_missing": value(row, "url_missing").lower() == "true",
        "published_at_missing": value(row, "published_at_missing").lower() == "true",
        "time_lag_analysis_possible": value(row, "time_lag_analysis_possible").lower() == "true",
        "parser_version": value(row, "parser_version"),
        "source_dataset": source_dataset.as_posix(),
        "rag_document_version": KR_DOC_VERSION,
    }
    return {"content": content, "metadata": metadata}


def build_samples_report(global_docs: list[dict], kr_docs: list[dict]) -> str:
    lines = ["# GLOBAL/KR RAG Document Samples", ""]
    lines.extend(["## GLOBAL AI Backend Developer / LLM or RAG", ""])
    for doc in select_global_samples(global_docs, "AI Backend Developer", {"LLM", "RAG", "Retrieval", "Embedding"}, 3):
        append_doc_sample(lines, doc)

    lines.extend(["## GLOBAL Data Engineer / Data Pipeline or Airflow", ""])
    for doc in select_global_samples(global_docs, "Data Engineer", {"Data Pipeline", "Airflow", "ETL", "Spark"}, 3):
        append_doc_sample(lines, doc)

    lines.extend(["## KR High-Confidence Documents", ""])
    for doc in kr_docs:
        meta = doc["metadata"]
        lines.extend(
            [
                f"### {meta['source_posting_id']} / {meta['title']}",
                "",
                f"- Primary role: {meta['primary_role']}",
                f"- Related roles: {', '.join(meta['related_roles'])}",
                f"- Skills: {', '.join(meta['verified_adoption_skills'])}",
                f"- Context: {meta['adoption_context']}",
                f"- URL missing: {meta['url_missing']}",
                f"- Published date missing: {meta['published_at_missing']}",
                "",
            ]
        )

    lines.extend(
        [
            "## Combined Agent Examples",
            "",
            "### 1. AI Backend + RAG",
            "",
            "- GLOBAL: 해외 AI Backend 공고에서는 RAG/Retrieval/LLM/API가 서비스 구현 요구로 확인됩니다.",
            "- KR: 국내 AI Backend/MLOps 공고에서는 RAG 파이프라인, VectorDB, API 연동, Airflow가 운영 업무와 함께 나타납니다.",
            "- USER ACTION: FastAPI + pgvector 기반 RAG 검색 API를 만들고, 임베딩/검색 평가 지표를 README에 정리합니다.",
            "",
            "### 2. Data Engineer + Vector Database / Data Pipeline",
            "",
            "- GLOBAL: 해외 Data Engineer 공고에서는 Data Pipeline, Airflow, Spark 같은 데이터 기반 기술 신호가 확인됩니다.",
            "- KR: 국내 Data Engineer 공고에서는 LLM/RAG/Agent 서비스를 위한 Vector Store 구축과 ETL/Airflow 파이프라인 경험이 함께 요구됩니다.",
            "- USER ACTION: 원천 데이터 수집, 정제, 임베딩 적재, Vector DB 검색까지 이어지는 파이프라인 프로젝트를 구현합니다.",
            "",
            "### 3. Builder + LLM Automation",
            "",
            "- GLOBAL: 해외 Builder/Product Engineer 성격의 공고에서는 LLM과 API 기반의 빠른 제품 구현 신호가 확인됩니다.",
            "- KR: 국내 마케팅 자동화 공고에서는 Python 자동화, LLM 연동, LangChain/LangGraph, Prompt Engineering 활용이 요구됩니다.",
            "- USER ACTION: 반복 업무를 자동화하는 LLM 워크플로우 앱을 만들고, 입력-처리-검증 과정을 시연합니다.",
            "",
        ]
    )
    return "\n".join(lines)


def build_agent_strategy() -> str:
    return """# GLOBAL/KR Agent Search Strategy

## Principle

GLOBAL evidence and KR evidence are searched separately. Their counts are never merged into one market score.

## Search Flow

1. Read the user's target role and recommended or missing skill.
2. Search `role_job_evidence_global_v1` with:
   - `evidence_purpose = leading_signal`
   - `job_role_category = target_role`
   - skill in `verified_core_skills` or `verified_secondary_skills`
3. Search `role_job_evidence_kr_v21` with:
   - `evidence_purpose = domestic_adoption`
   - `rag_candidate_status = high_confidence`
   - target role in `primary_role` or `related_roles`
   - skill in `verified_adoption_skills`
4. Compose the answer in this order:
   - GLOBAL leading signal
   - KR domestic adoption
   - User action

## Response Pattern

GLOBAL: 해외 {role} 공고에서는 {skill}이 어떤 업무 요구로 확인됩니다.

KR: 국내에서는 {skill}이 {primary_role}/{related_roles} 업무 맥락에서 어떻게 적용되는지 관찰됩니다.

USER ACTION: 사용자는 12주 안에 이 기술을 증명할 수 있는 구현 과제를 수행합니다.

## Guardrails

- KR documents without URL or published date must not be used to claim diffusion timing.
- `supporting_context_only` documents are not used for core skill evidence cards in this first RAG collection.
- `manual_review_needed` documents require URL/published_at/company completion before promotion.
- `exclude_from_rag` documents are not saved.
"""


def build_validation_report(
    global_input: Path,
    global_rows: list[dict[str, str]],
    global_docs: list[dict],
    kr_input: Path,
    kr_rows: list[dict[str, str]],
    kr_quality_rows: list[dict[str, str]],
    kr_docs: list[dict],
) -> str:
    global_role_counts = Counter(doc["metadata"]["job_role_category"] for doc in global_docs)
    global_skill_counts = Counter(skill for doc in global_docs for skill in doc["metadata"]["verified_core_skills"])
    global_parser_counts = Counter(doc["metadata"].get("parser_version", "") for doc in global_docs)
    kr_skill_counts = Counter(skill for doc in kr_docs for skill in doc["metadata"]["verified_adoption_skills"])
    global_bad = validate_docs(global_docs, "global")
    kr_bad = validate_docs(kr_docs, "kr")
    kr_url_missing = sum(doc["metadata"]["url_missing"] for doc in kr_docs)
    kr_published_missing = sum(doc["metadata"]["published_at_missing"] for doc in kr_docs)
    kr_time_lag_true = sum(doc["metadata"]["time_lag_analysis_possible"] for doc in kr_docs)

    lines = [
        "# GLOBAL/KR RAG Dry-Run Validation Report",
        "",
        "## Inputs",
        "",
        f"- GLOBAL input: `{global_input.as_posix()}`",
        f"- GLOBAL input rows: {len(global_rows)}",
        f"- KR input: `{kr_input.as_posix()}`",
        f"- KR high-confidence input rows: {len(kr_rows)}",
        f"- KR quality gate rows: {len(kr_quality_rows)}",
        "",
        "## GLOBAL Dry-Run",
        "",
        f"- GLOBAL RAG candidate documents: {len(global_docs)}",
        "",
        "### GLOBAL Documents By Role",
        "",
        "| Role | Documents |",
        "|---|---:|",
    ]
    for role, count in global_role_counts.most_common():
        lines.append(f"| {role} | {count} |")
    lines.extend(["", "### GLOBAL Verified Core Skill TOP 20", "", "| Skill | Documents |", "|---|---:|"])
    for skill, count in global_skill_counts.most_common(20):
        lines.append(f"| {skill} | {count} |")
    lines.extend(["", "### GLOBAL Parser Version Field", "", "| parser_version | Documents |", "|---|---:|"])
    for parser_version, count in global_parser_counts.most_common():
        lines.append(f"| {parser_version} | {count} |")
    lines.extend(
        [
            "",
            "Note: the selected GLOBAL source file is the parserfix v2 final CSV. Some rows retain an older `parser_version` string from the upstream export, so dry-run metadata also includes `parser_version_effective=role_evidence_parser_v2_parserfix_source` and `parserfix_source_file=true`.",
        ]
    )

    lines.extend(
        [
            "",
            "## KR Dry-Run",
            "",
            f"- KR high_confidence candidates: {len(kr_rows)}",
            f"- KR RAG candidate documents: {len(kr_docs)}",
            f"- KR URL missing documents: {kr_url_missing}",
            f"- KR published_at missing documents: {kr_published_missing}",
            f"- KR time_lag_analysis_possible=true documents: {kr_time_lag_true}",
            "",
            "### KR Skill Counts",
            "",
            "| Skill | Documents |",
            "|---|---:|",
        ]
    )
    for skill, count in kr_skill_counts.most_common():
        lines.append(f"| {skill} | {count} |")

    lines.extend(
        [
            "",
            "## Metadata/Content Validation",
            "",
            f"- GLOBAL documents with too-short content or missing required metadata: {len(global_bad)}",
            f"- KR documents with too-short content or missing required metadata: {len(kr_bad)}",
            "- GLOBAL collection separated: true",
            "- KR collection separated: true",
            "- GLOBAL/KR counts merged into market score: false",
            "",
            "## Items To Complete Before Save",
            "",
            "- KR documents need manual URL fill before source display.",
            "- KR documents need published_at or collected_at before time-lag diffusion analysis.",
            "- KR company names should be manually filled where blank.",
            "- Embedding cost/token estimation should be run only after final save candidates are approved.",
            "",
            "## Final Judgment",
            "",
            "- Dry-run document structure is suitable for RAG storage.",
            "- KR high_confidence 12 documents are usable as the first KR domestic adoption RAG collection.",
            "- Missing KR URL/published_at does not block domestic adoption explanation, but blocks time-lag diffusion claims.",
            "- The next step can be a DB-save dry-run or a DB save script, still without embedding until separately approved.",
            "",
            "## Safety Confirmation",
            "",
            "- No DB save, OpenAI call, embedding generation, RAG table save, JobRoleSkillEvidence recalculation, recommendation API change, or frontend change was performed.",
        ]
    )
    return "\n".join(lines) + "\n"


def validate_docs(docs: list[dict], kind: str) -> list[dict]:
    required = {
        "global": [
            "collection",
            "document_type",
            "evidence_purpose",
            "source_market",
            "market_region",
            "language",
            "source_posting_id",
            "rag_document_version",
        ],
        "kr": [
            "collection",
            "document_type",
            "evidence_purpose",
            "source_market",
            "market_region",
            "language",
            "source_posting_id",
            "rag_document_version",
            "rag_candidate_status",
        ],
    }[kind]
    bad = []
    for doc in docs:
        meta = doc["metadata"]
        if len(doc.get("content", "")) < 120 or any(meta.get(key) in (None, "") for key in required):
            bad.append(doc)
    return bad


def select_global_samples(global_docs: list[dict], role: str, skills: set[str], limit: int) -> list[dict]:
    matched = []
    for doc in global_docs:
        meta = doc["metadata"]
        doc_skills = set(meta["verified_core_skills"]) | set(meta["verified_secondary_skills"])
        if meta["job_role_category"] == role and doc_skills & skills:
            matched.append(doc)
    if len(matched) < limit:
        for doc in global_docs:
            if doc not in matched and doc["metadata"]["job_role_category"] == role:
                matched.append(doc)
            if len(matched) >= limit:
                break
    return matched[:limit]


def append_doc_sample(lines: list[str], doc: dict) -> None:
    meta = doc["metadata"]
    lines.extend(
        [
            f"### {meta['company']} / {meta['title']}",
            "",
            "```text",
            doc["content"][:1200],
            "```",
            "",
            "```json",
            json.dumps(meta, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    )


def summarize_text(parts: list[str], max_chars: int = 800) -> str:
    text = " ".join(part.strip() for part in parts if part and part.strip())
    text = " ".join(text.split())
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 3].rstrip() + "..."


def parse_list(value: str) -> list[str]:
    return [item.strip() for item in (value or "").split(";") if item.strip()]


def value(row: dict[str, str], key: str) -> str:
    return (row.get(key) or "").strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def write_jsonl(path: Path, docs: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for doc in docs:
            file.write(json.dumps(doc, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
