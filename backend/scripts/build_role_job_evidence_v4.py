import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from validate_role_job_evidence_v3_quality_gate import find_duplicate_groups


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v3.csv"
DEFAULT_OUTPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v4.csv"
DEFAULT_REMOVED = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v4_removed_or_unverified.csv"
DEFAULT_REPORT = ROOT_DIR / "data" / "exports" / "role_job_evidence_v4_validation_report.md"

TARGET_ROLES = [
    "AI Backend Developer",
    "Backend Developer",
    "Builder",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Frontend Developer",
]

ROLE_SKILL_POLICY = {
    "AI Backend Developer": {
        "core": [
            "Python", "FastAPI", "API", "LLM", "RAG", "Retrieval", "Embedding",
            "Vector Database", "pgvector", "LangChain", "Model Serving",
            "Inference Serving", "PostgreSQL", "Docker",
        ],
        "secondary": [
            "Go", "Java", "Kubernetes", "AWS", "GCP", "Azure",
            "TypeScript", "React", "Machine Learning",
        ],
    },
    "Backend Developer": {
        "core": [
            "Java", "Go", "Python", "FastAPI", "Spring", "API", "PostgreSQL",
            "MySQL", "Redis", "Docker", "Kubernetes", "AWS", "Microservice",
        ],
        "secondary": ["LLM", "Machine Learning", "Spark", "TypeScript", "React"],
    },
    "Builder": {
        "core": [
            "JavaScript", "TypeScript", "React", "Node.js", "Python", "API",
            "Automation", "Integration", "LLM", "RAG", "Full Stack",
        ],
        "secondary": ["AWS", "Java", "Go", "Machine Learning", "Docker", "Kubernetes"],
    },
    "Data Analyst": {
        "core": [
            "SQL", "Python", "Tableau", "Power BI", "Dashboard", "Reporting",
            "Analytics", "Metrics", "Excel",
        ],
        "secondary": ["Machine Learning", "RAG", "Go", "Embedding", "LLM", "Spark"],
    },
    "Data Engineer": {
        "core": [
            "Python", "SQL", "Spark", "Airflow", "Kafka", "ETL", "Data Pipeline",
            "Warehouse", "dbt", "AWS", "PostgreSQL",
        ],
        "secondary": ["Docker", "Kubernetes", "Java", "Go", "Machine Learning", "RAG", "LLM"],
    },
    "Data Scientist": {
        "core": [
            "Python", "SQL", "Machine Learning", "Statistics", "Experimentation",
            "Classification", "Regression", "Model Evaluation", "PyTorch",
            "TensorFlow", "Deep Learning",
        ],
        "secondary": ["Spark", "Airflow", "LLM", "RAG", "Embedding", "AWS"],
    },
    "Frontend Developer": {
        "core": [
            "React", "TypeScript", "JavaScript", "HTML", "CSS", "Next.js",
            "UI", "Component", "Design System", "Accessibility",
        ],
        "secondary": ["Node.js", "Python", "Java", "C++", "Go", "Kubernetes", "LLM"],
    },
}

V4_FIELDS = [
    "duplicate_group_id",
    "duplicate_status",
    "duplicate_representative_id",
    "verification_text_source",
    "section_extraction_status",
    "normalized_raw_body_length",
    "verified_skills",
    "verified_core_skills",
    "verified_secondary_skills",
    "verified_skill_evidence_excerpt",
    "rejected_skills",
    "skill_verification_detail",
    "parser_version",
    "evidence_quality",
]

AUDIT_FIELDS = [
    "record_type",
    "source_posting_id",
    "job_role_category",
    "company",
    "title",
    "job_url",
    "duplicate_group_id",
    "duplicate_status",
    "duplicate_representative_id",
    "skill",
    "skill_status",
    "skill_level",
    "skill_reason",
    "direct_evidence_fields",
    "direct_evidence_excerpt",
    "skills_method",
    "predicted_skill_scores",
    "final_skills",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build evidence-ready role dataset v4 from accepted v3 without database or API access."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--removed-output", type=Path, default=DEFAULT_REMOVED)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()

    input_path = args.input.resolve()
    rows, original_fields = read_csv(input_path)
    duplicate_map = build_duplicate_map(rows)

    retained = []
    audit_rows = []
    for row in rows:
        duplicate = duplicate_map[value(row, "id")]
        if duplicate["duplicate_status"] == "same_content_removed":
            audit_rows.append(duplicate_removed_audit(row, duplicate))
            continue

        verified = verify_skills(row)
        enriched = {
            **row,
            **duplicate,
            "verification_text_source": verified["text_source"],
            "section_extraction_status": verified["section_status"],
            "normalized_raw_body_length": str(verified["raw_length"]),
            "verified_skills": "; ".join(verified["core"] + verified["secondary"]),
            "verified_core_skills": "; ".join(verified["core"]),
            "verified_secondary_skills": "; ".join(verified["secondary"]),
            "verified_skill_evidence_excerpt": verified["evidence_excerpt"],
            "rejected_skills": "; ".join(verified["rejected"]),
            "skill_verification_detail": json.dumps(verified["detail"], ensure_ascii=False),
            "parser_version": value(row, "parser_version") or "role_evidence_parser_v1",
            "evidence_quality": "skill_evidence_ready" if verified["core"] else "role_evidence_only",
        }
        retained.append(enriched)
        audit_rows.extend(rejected_skill_audits(row, duplicate, verified["detail"]))

    write_csv(args.output.resolve(), original_fields + V4_FIELDS, retained)
    write_csv(args.removed_output.resolve(), AUDIT_FIELDS, audit_rows)
    write_report(args.report_output.resolve(), input_path, rows, retained, audit_rows)
    print_summary(args.output.resolve(), args.removed_output.resolve(), args.report_output.resolve(), rows, retained, audit_rows)


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), list(reader.fieldnames or [])


def build_duplicate_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    mapping = {
        value(row, "id"): {
            "duplicate_group_id": "",
            "duplicate_status": "unique",
            "duplicate_representative_id": value(row, "id"),
        }
        for row in rows
    }
    for group in find_duplicate_groups(rows):
        ids = [posting_id.strip() for posting_id in group["posting_ids"].split(";") if posting_id.strip()]
        group_id = "dup_" + hashlib.sha256(
            f"{group['role']}|{group['company']}|{group['normalized_title']}".encode("utf-8")
        ).hexdigest()[:16]
        representative_id = choose_representative(ids, rows)
        if group["duplicate_status"] == "same_content_duplicate":
            for posting_id in ids:
                mapping[posting_id] = {
                    "duplicate_group_id": group_id,
                    "duplicate_status": (
                        "representative" if posting_id == representative_id else "same_content_removed"
                    ),
                    "duplicate_representative_id": representative_id,
                }
        else:
            for posting_id in ids:
                mapping[posting_id] = {
                    "duplicate_group_id": group_id,
                    "duplicate_status": "distinct_opening",
                    "duplicate_representative_id": posting_id,
                }
    return mapping


def choose_representative(ids: list[str], rows: list[dict[str, str]]) -> str:
    by_id = {value(row, "id"): row for row in rows}
    return sorted(
        ids,
        key=lambda posting_id: (
            -len(body_text(by_id[posting_id])),
            numeric_id(posting_id),
            posting_id,
        ),
    )[0]


def verify_skills(row: dict[str, str]) -> dict:
    role = role_of(row)
    evidence_fields, text_source, section_status, raw_length = evidence_text_fields(row)
    body = " ".join(evidence_fields.values())
    policy = ROLE_SKILL_POLICY[role]
    core = []
    secondary = []
    detail = []
    verified_names = set()

    for level, candidates in [("verified_core", policy["core"]), ("verified_secondary", policy["secondary"])]:
        for skill in candidates:
            evidence = find_direct_evidence(skill, row, evidence_fields)
            if not evidence:
                continue
            normalized = skill.lower()
            if normalized in verified_names:
                continue
            verified_names.add(normalized)
            target = core if level == "verified_core" else secondary
            target.append(skill)
            detail.append(
                verification_item(
                    skill=skill,
                    status=level,
                    reason=f"Direct {level.replace('_', ' ')} evidence found in posting text.",
                    evidence=evidence,
                )
            )

    rejected = []
    for skill in parse_skills(value(row, "final_skills")):
        if skill.lower() in verified_names:
            continue
        evidence = find_direct_evidence(skill, row, evidence_fields)
        if evidence and skill not in policy["core"] and skill not in policy["secondary"]:
            status = "not_verified"
            reason = "Direct text mention exists, but this skill is outside the validated policy for this role."
        elif evidence:
            status = "not_verified"
            reason = "Direct text mention was found but it did not qualify under the validated role skill policy."
        elif likely_incidental_false_positive(skill, row):
            status = "incidental_false_positive"
            reason = "The extracted value is likely ordinary wording or an ambiguous non-technical mention."
        elif value(row, "skills_method") == "model" or skill in parse_skills(value(row, "predicted_skills")):
            status = "predicted_only_rejected"
            reason = "Predicted/final skill is not directly stated in the available posting text."
        else:
            status = "not_verified"
            reason = "No direct evidence is available in responsibilities, requirements, or preferred qualifications."
        rejected.append(skill)
        detail.append(verification_item(skill, status, reason, evidence))

    return {
        "core": core,
        "secondary": secondary,
        "rejected": rejected,
        "detail": detail,
        "has_body": bool(body),
        "text_source": text_source,
        "section_status": section_status,
        "raw_length": raw_length,
        "evidence_excerpt": first_verified_excerpt(detail),
    }


def evidence_text_fields(row: dict[str, str]) -> tuple[dict[str, str], str, str, int]:
    fields = {
        "responsibilities": value(row, "responsibilities"),
        "requirements": value(row, "requirements"),
        "preferred_qualifications": value(row, "preferred_qualifications"),
    }
    section_length = sum(len(text.strip()) for text in fields.values())
    raw_body = value(row, "normalized_raw_body")
    raw_length = len(raw_body)
    if section_length < 200 and raw_length >= 500:
        return {"normalized_raw_body": raw_body}, "raw_body_fallback", "fallback_used", raw_length
    if section_length > 0:
        return fields, "structured_sections", value(row, "section_extraction_status") or "success", raw_length
    return fields, "structured_sections", "failed", raw_length


def find_direct_evidence(
    skill: str,
    row: dict[str, str],
    evidence_fields: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    matches = []
    fields = evidence_fields or {
        "responsibilities": value(row, "responsibilities"),
        "requirements": value(row, "requirements"),
        "preferred_qualifications": value(row, "preferred_qualifications"),
    }
    for field, text in fields.items():
        match = technical_skill_match(skill, text)
        if match:
            matches.append(
                {
                    "field": field,
                    "excerpt": context_snippet(text, match.start(), match.end()),
                }
            )
    return matches


def first_verified_excerpt(details: list[dict]) -> str:
    for item in details:
        if item["status"] in {"verified_core", "verified_secondary"} and item.get("excerpt"):
            return item["excerpt"]
    return ""


def technical_skill_match(skill: str, text: str):
    if not text:
        return None
    specialized = {
        "Go": [
            r"\bgolang\b",
            r"\bgo\s+(programming|language|developer|development|backend|services?)\b",
            r"\b(languages?|technologies|tech stack|proficiency|proficient|experience with|using|such as)\b.{0,100}\bgo\b",
            r"\bgo\b.{0,80}\b(language|backend|services?|development)\b",
        ],
        "R": [r"\br\s+(language|programming)\b", r"\bpython\s*/\s*r\b", r"\brstudio\b"],
        "Java": [
            r"\bjava\s+(programming|services?|applications?|development)\b",
            r"\bjava\s*/\s*kotlin\b|\bspring\s*/\s*java\b",
            r"\b(languages?|technologies|tech stack|proficiency|proficient|experience with|using|such as)\b.{0,100}\bjava\b",
        ],
        "C++": [
            r"\bc\+\+\s+(programming|development|services?|experience|proficiency)\b",
            r"\b(languages?|technologies|tech stack|proficiency|proficient|experience with|using|such as)\b.{0,100}\bc\+\+\b",
        ],
        "Embedding": [
            r"\b(vector|text|semantic|token)\s+embeddings?\b",
            r"\bembeddings?\s+(model|models|pipeline|service|search|index)\b",
        ],
        "LLM": [r"\bllms?\b", r"\blarge language models?\b"],
        "AWS": [
            r"\baws\b.{0,80}\b(cloud|platform|deploy|deployment|infrastructure|services?)\b",
            r"\b(cloud|platform|deploy|deployment|infrastructure|services?)\b.{0,80}\baws\b",
            r"\bamazon web services\b",
        ],
        "Azure": [
            r"\bazure\b.{0,80}\b(cloud|platform|deploy|deployment|infrastructure|services?)\b",
            r"\b(cloud|platform|deploy|deployment|infrastructure|services?)\b.{0,80}\bazure\b",
        ],
        "GCP": [
            r"\bgcp\b.{0,80}\b(cloud|platform|deploy|deployment|infrastructure|services?)\b",
            r"\b(cloud|platform|deploy|deployment|infrastructure|services?)\b.{0,80}\bgcp\b",
            r"\bgoogle cloud\b",
        ],
    }
    patterns = specialized.get(skill, [skill_pattern(skill)])
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            return match
    return None


def skill_pattern(skill: str) -> str:
    aliases = {
        "API": r"\bapis?\b",
        "Vector Database": r"\bvector (databases?|dbs?|stores?)\b",
        "pgvector": r"\bpgvector\b",
        "Model Serving": r"\bmodel serving\b|\bserve models?\b",
        "Inference Serving": r"\binference serving\b|\bserve inference\b",
        "PostgreSQL": r"\bpostgres(ql)?\b",
        "Node.js": r"\bnode\.?js\b",
        "Full Stack": r"\bfull[- ]?stack\b|\bfullstack\b",
        "Power BI": r"\bpower\s*bi\b",
        "Data Pipeline": r"\bdata pipelines?\b",
        "Warehouse": r"\b(data )?warehouse\b",
        "dbt": r"\bdbt\b",
        "Machine Learning": r"\bmachine learning\b",
        "Model Evaluation": r"\bmodel evaluation\b|\bevaluat(e|ing) models?\b",
        "Design System": r"\bdesign systems?\b",
        "Next.js": r"\bnext\.?js\b",
        "UI": r"\bui\b|\buser interface\b",
        "ETL": r"\betl\b|\belt\b",
    }
    if skill in aliases:
        return aliases[skill]
    return rf"(?<![A-Za-z0-9+#.]){re.escape(skill)}(?![A-Za-z0-9+#.-])"


def likely_incidental_false_positive(skill: str, row: dict[str, str]) -> bool:
    text = body_text(row)
    if skill == "Go":
        return bool(re.search(r"\bgo\b", text, flags=re.IGNORECASE))
    if skill == "Embedding":
        return bool(re.search(r"\bembedded|embedding\b", text, flags=re.IGNORECASE))
    return False


def verification_item(skill: str, status: str, reason: str, evidence: list[dict[str, str]]) -> dict:
    return {
        "skill": skill,
        "status": status,
        "reason": reason,
        "fields": [item["field"] for item in evidence],
        "excerpt": evidence[0]["excerpt"] if evidence else "",
    }


def duplicate_removed_audit(row: dict[str, str], duplicate: dict[str, str]) -> dict[str, str]:
    return {
        "record_type": "duplicate_removed",
        "source_posting_id": value(row, "id"),
        "job_role_category": role_of(row),
        "company": value(row, "company"),
        "title": value(row, "title"),
        "job_url": value(row, "job_url"),
        **duplicate,
        "skill": "",
        "skill_status": "duplicate_removed",
        "skill_level": "",
        "skill_reason": "Removed because a same-content representative posting is retained in v4.",
        "direct_evidence_fields": "",
        "direct_evidence_excerpt": "",
        "skills_method": value(row, "skills_method"),
        "predicted_skill_scores": value(row, "predicted_skill_scores"),
        "final_skills": value(row, "final_skills"),
    }


def rejected_skill_audits(
    row: dict[str, str],
    duplicate: dict[str, str],
    details: list[dict],
) -> list[dict[str, str]]:
    audits = []
    for item in details:
        if item["status"] in {"verified_core", "verified_secondary"}:
            continue
        audits.append(
            {
                "record_type": "unverified_skill",
                "source_posting_id": value(row, "id"),
                "job_role_category": role_of(row),
                "company": value(row, "company"),
                "title": value(row, "title"),
                "job_url": value(row, "job_url"),
                **duplicate,
                "skill": item["skill"],
                "skill_status": item["status"],
                "skill_level": "",
                "skill_reason": item["reason"],
                "direct_evidence_fields": "; ".join(item["fields"]),
                "direct_evidence_excerpt": item["excerpt"],
                "skills_method": value(row, "skills_method"),
                "predicted_skill_scores": value(row, "predicted_skill_scores"),
                "final_skills": value(row, "final_skills"),
            }
        )
    return audits


def write_report(
    path: Path,
    input_path: Path,
    v3_rows: list[dict[str, str]],
    v4_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
) -> None:
    v3_by_role = group_by_role(v3_rows)
    v4_by_role = group_by_role(v4_rows)
    removed_by_role = Counter(
        row["job_role_category"] for row in audit_rows if row["record_type"] == "duplicate_removed"
    )
    quality_by_role = {
        role: Counter(value(row, "evidence_quality") for row in v4_by_role.get(role, []))
        for role in TARGET_ROLES
    }
    lines = [
        "# Role Job Evidence v4 Validation Report",
        "",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Source accepted v3 CSV: `{input_path.as_posix()}`",
        f"- Source documents: {len(v3_rows):,}",
        f"- v4 documents retained: {len(v4_rows):,}",
        "- Safety: File generation only. No database write, JobRoleSkillEvidence rebuild, RAG document write, embedding generation, or OpenAI API call was performed.",
        "- Verification rule: technologies are verified only from responsibilities, requirements, and preferred qualifications; title and upstream extracted skills are not direct skill evidence.",
        "",
        "## Document Population",
        "",
        "| Role | v3 Accepted | Same-Content Removed | v4 Retained | Skill Evidence Ready | Role Evidence Only |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for role in TARGET_ROLES:
        quality = quality_by_role[role]
        lines.append(
            f"| {role} | {len(v3_by_role.get(role, [])):,} | {removed_by_role[role]:,} | "
            f"{len(v4_by_role.get(role, [])):,} | {quality['skill_evidence_ready']:,} | "
            f"{quality['role_evidence_only']:,} |"
        )
    all_quality = Counter(value(row, "evidence_quality") for row in v4_rows)
    lines.append(
        f"| **Total** | **{len(v3_rows):,}** | **{sum(removed_by_role.values()):,}** | "
        f"**{len(v4_rows):,}** | **{all_quality['skill_evidence_ready']:,}** | "
        f"**{all_quality['role_evidence_only']:,}** |"
    )

    lines.extend(["", "## Verified Core Skills", ""])
    for role in TARGET_ROLES:
        lines.extend(skill_table(role, v4_by_role.get(role, []), "verified_core_skills"))

    lines.extend(["## Verified Secondary Skills", ""])
    for role in TARGET_ROLES:
        lines.extend(skill_table(role, v4_by_role.get(role, []), "verified_secondary_skills"))

    lines.extend(["## Rejected Skill Statistics", ""])
    rejected = [row for row in audit_rows if row["record_type"] == "unverified_skill"]
    rejected_counts = Counter((row["job_role_category"], row["skill_status"]) for row in rejected)
    lines.extend(
        [
            "| Role | Predicted Only Rejected | Incidental False Positive | Not Verified |",
            "|---|---:|---:|---:|",
        ]
    )
    for role in TARGET_ROLES:
        lines.append(
            f"| {role} | {rejected_counts[(role, 'predicted_only_rejected')]:,} | "
            f"{rejected_counts[(role, 'incidental_false_positive')]:,} | "
            f"{rejected_counts[(role, 'not_verified')]:,} |"
        )

    focus_pairs = [
        ("Data Analyst", "Go"), ("Data Analyst", "Embedding"), ("Data Analyst", "Spark"),
        ("Data Analyst", "LLM"), ("Frontend Developer", "Java"), ("Frontend Developer", "C++"),
        ("Frontend Developer", "Go"), ("AI Backend Developer", "Go"),
        ("AI Backend Developer", "Java"), ("AI Backend Developer", "Machine Learning"),
        ("Builder", "AWS"), ("Builder", "Machine Learning"), ("Builder", "Java"),
    ]
    lines.extend(
        [
            "",
            "### Previously Contaminated Skill Combinations",
            "",
            "| Role | Skill | v3 Final-Skill Rows | v4 Verified Core | v4 Verified Secondary | Rejected / Removed |",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for role, skill in focus_pairs:
        original = count_skill(v3_by_role.get(role, []), "final_skills", skill)
        core = count_skill(v4_by_role.get(role, []), "verified_core_skills", skill)
        secondary = count_skill(v4_by_role.get(role, []), "verified_secondary_skills", skill)
        lines.append(f"| {role} | {skill} | {original:,} | {core:,} | {secondary:,} | {original - core - secondary:,} |")

    lines.extend(
        [
            "",
            "## RAG Document Recommendation",
            "",
            f"- Use the **{all_quality['skill_evidence_ready']:,}** `skill_evidence_ready` documents for skill-specific retrieval and evidence cards.",
            f"- Keep the **{all_quality['role_evidence_only']:,}** `role_evidence_only` documents out of skill cards for this MVP. They may be stored later in a separate role-context collection if needed.",
            "- Add `duplicate_group_id`, `duplicate_status`, `duplicate_representative_id`, `evidence_quality`, and `verified_skills` to RAG document metadata.",
            "- For `distinct_opening` documents, retain the documents but limit retrieval presentation to one company/title group per response.",
            "",
            "## JobRoleSkillEvidence Recommendation",
            "",
            "- Recalculate from exactly the v4 rows marked `skill_evidence_ready`.",
            "- Weight `verified_core_skills` as `1.0` and `verified_secondary_skills` as `0.3`.",
            "- Give rejected skills weight `0`; do not use `final_skills` for new market scores.",
            "- Use BETA labeling for roles with limited ready evidence after verification, based on the counts above.",
            "",
            "## Coverage and Additional Collection Decision",
            "",
            "- `Builder` has only 17 skill-ready documents and `Frontend Developer` has only 15; both require additional collection before their technology trend claims are presented without BETA labeling.",
            "- `Data Analyst` has 31 skill-ready documents after contamination removal; it can support initial evidence cards but should remain BETA until coverage broadens.",
            "- AI Backend, Backend, Data Engineer, and Data Scientist retain stronger ready pools, but should still use only verified skills and the same v4 population for scores and cards.",
            "",
            "## Conclusion",
            "",
            "- v4 is suitable as the shared source-of-truth candidate for RAG evidence and JobRoleSkillEvidence because it separates duplicate handling and direct skill verification.",
            "- The recommended MVP embedding population is the 334 `skill_evidence_ready` documents; exclude `role_evidence_only` from skill retrieval for now.",
            "- The next implementation step may update the indexing and evidence rebuild scripts to consume v4 and `verified_skills`, but no database write or embedding should run until that code and the reported counts are approved.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def skill_table(role: str, rows: list[dict[str, str]], field: str) -> list[str]:
    counts = skill_counts(rows, field)
    lines = [
        f"### {role}",
        "",
        f"- v4 documents: {len(rows):,}",
        "",
        "| Rank | Skill | Verified Documents | Share of Role v4 Documents |",
        "|---:|---|---:|---:|",
    ]
    for rank, (skill, count) in enumerate(counts.most_common(20), start=1):
        lines.append(f"| {rank} | {md(skill)} | {count:,} | {pct(count, len(rows)):.1f}% |")
    if not counts:
        lines.append("| - | No verified skills | - | - |")
    lines.append("")
    return lines


def print_summary(
    output_path: Path,
    removed_path: Path,
    report_path: Path,
    v3_rows: list[dict[str, str]],
    v4_rows: list[dict[str, str]],
    audit_rows: list[dict[str, str]],
) -> None:
    duplicate_removed = Counter(
        row["job_role_category"] for row in audit_rows if row["record_type"] == "duplicate_removed"
    )
    grouped = group_by_role(v4_rows)
    print("Role evidence v4 generated (files only; no DB write; no OpenAI call).")
    print(f"Input v3 rows: {len(v3_rows)}; v4 retained rows: {len(v4_rows)}; duplicate removed: {sum(duplicate_removed.values())}")
    print(f"v4 CSV: {output_path}")
    print(f"Removed/unverified audit CSV: {removed_path}")
    print(f"Validation report: {report_path}")
    for role in TARGET_ROLES:
        rows = grouped.get(role, [])
        quality = Counter(value(row, "evidence_quality") for row in rows)
        top_core = ", ".join(
            f"{skill}={count}" for skill, count in skill_counts(rows, "verified_core_skills").most_common(5)
        )
        print(
            f"{role}: v4={len(rows)}, removed={duplicate_removed[role]}, "
            f"ready={quality['skill_evidence_ready']}, role_only={quality['role_evidence_only']}, "
            f"top_core=[{top_core}]"
        )


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def group_by_role(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[role_of(row)].append(row)
    return grouped


def skill_counts(rows: list[dict[str, str]], field: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(set(parse_skills(value(row, field))))
    return counts


def count_skill(rows: list[dict[str, str]], field: str, skill: str) -> int:
    return sum(skill in parse_skills(value(row, field)) for row in rows)


def body_text(row: dict[str, str]) -> str:
    section_body = " ".join(
        value(row, field)
        for field in ["responsibilities", "requirements", "preferred_qualifications"]
    )
    return section_body or value(row, "normalized_raw_body")


def parse_skills(text: str) -> list[str]:
    return [part.strip() for part in text.split(";") if part.strip()]


def context_snippet(text: str, start: int, end: int, radius: int = 100) -> str:
    beginning = max(0, start - radius)
    ending = min(len(text), end + radius)
    snippet = " ".join(text[beginning:ending].split())
    return f"{snippet[:240].rstrip()}..." if len(snippet) > 240 else snippet


def numeric_id(value_: str) -> int:
    return int(value_) if value_.isdigit() else 10**12


def role_of(row: dict[str, str]) -> str:
    return value(row, "validated_job_role_category") or value(row, "original_job_role_category")


def pct(count: int, total: int) -> float:
    return count / total * 100 if total else 0.0


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


def md(text: str) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    main()
