from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parents[0]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from build_role_job_evidence_v4 import ROLE_SKILL_POLICY, technical_skill_match  # noqa: E402


BATCH_ID = "evidence_boost_20260529_01"
DEFAULT_DIR = ROOT_DIR / "data" / "exports" / "additional_batches"
DEFAULT_V3 = DEFAULT_DIR / f"external_job_postings_role_evidence_v3_{BATCH_ID}.csv"
DEFAULT_V4 = DEFAULT_DIR / f"external_job_postings_role_evidence_v4_{BATCH_ID}.csv"
DEFAULT_AUDIT = DEFAULT_DIR / f"external_job_postings_role_evidence_v4_removed_or_unverified_{BATCH_ID}.csv"
DEFAULT_RAW = DEFAULT_DIR / f"external_job_postings_additional_raw_{BATCH_ID}.csv"
DEFAULT_REPORT = DEFAULT_DIR / f"v4_role_only_failure_audit_{BATCH_ID}.md"
DEFAULT_SAMPLES = DEFAULT_DIR / f"v4_role_only_failure_samples_{BATCH_ID}.csv"

SECTION_FIELDS = ["responsibilities", "requirements", "preferred_qualifications"]
SUGGESTED_VOCABULARY_PATTERNS = {
    "Agent Infrastructure": r"\bagent infrastructure\b|\bagentic infrastructure\b|\bagent platform\b",
    "Model Inference": r"\bmodel inference\b|\binference engine\b|\binference platform\b|\binference data plane\b",
    "AI Platform": r"\bai platform\b|\bai infrastructure\b|\bai agents?\b",
    "Developer Platform": r"\bdeveloper platform\b|\bdeveloper experience\b|\bdevex\b",
    "Product Engineering": r"\bproduct engineer(ing)?\b|\bproduct-minded\b",
    "Build Integrations": r"\bbuild integrations?\b|\bintegrat(e|ing|ions?)\b",
    "API Integration": r"\bapi integrations?\b|\bintegrat(e|ing).{0,80}\bapis?\b",
    "End-to-End Product": r"\bend[- ]to[- ]end\b.{0,80}\b(product|features?|applications?|workflows?)\b",
    "Ship Product": r"\bship(ping)?\b.{0,80}\b(product|features?|customer|workflows?)\b",
    "Customer Workflow": r"\bcustomer workflows?\b|\bworkflows?\b.{0,80}\bcustomer\b",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit v3 accepted additional batch rows that became v4 role_evidence_only."
    )
    parser.add_argument("--batch-id", default=BATCH_ID)
    parser.add_argument("--v3-input", type=Path, default=DEFAULT_V3)
    parser.add_argument("--v4-input", type=Path, default=DEFAULT_V4)
    parser.add_argument("--audit-input", type=Path, default=DEFAULT_AUDIT)
    parser.add_argument("--raw-input", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--samples-output", type=Path, default=DEFAULT_SAMPLES)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    v3_rows = read_csv(args.v3_input)
    v4_rows = read_csv(args.v4_input)
    audit_rows = read_csv(args.audit_input)
    raw_rows = read_csv(args.raw_input)

    raw_by_id = {
        f"{value(row, 'source')}:{value(row, 'external_id')}": row
        for row in raw_rows
        if value(row, "source") and value(row, "external_id")
    }
    new_v3 = [row for row in v3_rows if value(row, "batch_id") == args.batch_id]
    new_v4 = [row for row in v4_rows if value(row, "batch_id") == args.batch_id]
    ready_rows = [row for row in new_v4 if value(row, "evidence_quality") == "skill_evidence_ready"]
    role_only_rows = [row for row in new_v4 if value(row, "evidence_quality") == "role_evidence_only"]

    audit_by_id: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in audit_rows:
        audit_by_id[value(row, "source_posting_id")].append(row)

    assessed = [assess_role_only(row, raw_by_id.get(value(row, "id"), {}), audit_by_id) for row in role_only_rows]

    args.samples_output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.samples_output, sample_fields(), assessed)
    args.report_output.write_text(
        build_report(new_v3, ready_rows, role_only_rows, assessed),
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "batch_id": args.batch_id,
                "new_v3_accepted": len(new_v3),
                "new_v4_ready": len(ready_rows),
                "new_v4_role_only": len(role_only_rows),
                "report": str(args.report_output),
                "samples": str(args.samples_output),
                "database_writes": False,
                "network_requests": False,
                "openai_calls": False,
                "embedding_requests": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def assess_role_only(
    row: dict[str, str],
    raw: dict[str, str],
    audit_by_id: dict[str, list[dict[str, str]]],
) -> dict[str, str]:
    section_text = "\n".join(value(row, field) for field in SECTION_FIELDS)
    raw_body = value(raw, "description")
    title = value(row, "title")
    role = role_of(row)
    section_lengths = {field: len(value(row, field)) for field in SECTION_FIELDS}
    raw_len = len(raw_body)
    section_len = len(section_text)
    final_skills = parse_skills(value(row, "final_skills"))

    policy = ROLE_SKILL_POLICY.get(role, {"core": [], "secondary": []})
    policy_hits_section = find_policy_hits(policy, row)
    policy_hits_raw = find_text_policy_hits(policy, raw_body)
    suggested_hits_section = find_suggested_hits(section_text)
    suggested_hits_raw = find_suggested_hits(raw_body)
    title_skill_hits = [skill for skill in policy["core"] + policy["secondary"] if text_has_skill(skill, title)]
    rejected_statuses = Counter(
        value(item, "skill_status")
        for item in audit_by_id.get(value(row, "id"), [])
        if value(item, "skill_status")
    )

    status, reason = classify_failure(
        role=role,
        title=title,
        raw_len=raw_len,
        section_len=section_len,
        policy_hits_section=policy_hits_section,
        policy_hits_raw=policy_hits_raw,
        suggested_hits_section=suggested_hits_section,
        suggested_hits_raw=suggested_hits_raw,
        final_skills=final_skills,
    )

    excerpt_source = raw_body if raw_body else section_text
    return {
        "failure_status": status,
        "failure_reason": reason,
        "company": value(row, "company"),
        "title": title,
        "validated_job_role_category": role,
        "job_url": value(row, "job_url"),
        "source_posting_id": value(row, "id"),
        "responsibilities_len": str(section_lengths["responsibilities"]),
        "requirements_len": str(section_lengths["requirements"]),
        "preferred_qualifications_len": str(section_lengths["preferred_qualifications"]),
        "section_text_len": str(section_len),
        "raw_body_len": str(raw_len),
        "raw_body_exists": str(bool(raw_body)).lower(),
        "policy_hits_in_sections": "; ".join(policy_hits_section),
        "policy_hits_in_raw_body": "; ".join(policy_hits_raw),
        "suggested_vocab_hits_in_sections": "; ".join(suggested_hits_section),
        "suggested_vocab_hits_in_raw_body": "; ".join(suggested_hits_raw),
        "title_skill_hits": "; ".join(title_skill_hits),
        "final_skills": value(row, "final_skills"),
        "rejected_skill_status_counts": json.dumps(dict(rejected_statuses), ensure_ascii=False),
        "body_excerpt": snippet(excerpt_source),
    }


def classify_failure(
    role: str,
    title: str,
    raw_len: int,
    section_len: int,
    policy_hits_section: list[str],
    policy_hits_raw: list[str],
    suggested_hits_section: list[str],
    suggested_hits_raw: list[str],
    final_skills: list[str],
) -> tuple[str, str]:
    if raw_len > 500 and section_len < 200:
        return (
            "missing_or_unmapped_body",
            "Raw description is present, but v4 evidence fields are empty or too short.",
        )
    if raw_len > section_len * 3 and raw_len > 1000 and (policy_hits_raw or suggested_hits_raw):
        return (
            "parsing_or_format_issue",
            "Raw body has relevant technical or product-building language that did not survive section extraction.",
        )
    if suggested_hits_section and not policy_hits_section:
        return (
            "vocabulary_gap",
            "Evidence fields contain role-relevant vocabulary that is not part of the current verified core policy.",
        )
    if suggested_hits_raw and not policy_hits_raw and section_len >= 200:
        return (
            "vocabulary_gap",
            "Raw body contains role-relevant vocabulary, but no current core skill was verified.",
        )
    if role == "AI Backend Developer" and re.search(r"\bresearch\b|\btraining\b|\bscientist\b|\bmodel evaluation\b", title, re.I):
        return (
            "misclassified_role",
            "Accepted AI Backend boundary row appears closer to research/model training than service implementation.",
        )
    if role == "Builder" and re.search(r"\bforward deployed\b|\bfde\b|\bsolution\b", title, re.I) and not policy_hits_section:
        return (
            "genuinely_role_only",
            "Builder role context exists, but direct verified implementation skills are not stated in the checked fields.",
        )
    if final_skills and not policy_hits_section:
        return (
            "genuinely_role_only",
            "Extracted skills were not directly supported by the checked evidence fields.",
        )
    return (
        "genuinely_role_only",
        "Role appears plausible, but no direct core skill evidence was available for scoring.",
    )


def find_policy_hits(policy: dict[str, list[str]], row: dict[str, str]) -> list[str]:
    hits = []
    for skill in policy.get("core", []) + policy.get("secondary", []):
        for field in SECTION_FIELDS:
            if technical_skill_match(skill, value(row, field)):
                hits.append(skill)
                break
    return unique(hits)


def find_text_policy_hits(policy: dict[str, list[str]], text: str) -> list[str]:
    hits = []
    fake_row = {"responsibilities": text, "requirements": "", "preferred_qualifications": ""}
    for skill in policy.get("core", []) + policy.get("secondary", []):
        if technical_skill_match(skill, value(fake_row, "responsibilities")):
            hits.append(skill)
    return unique(hits)


def find_suggested_hits(text: str) -> list[str]:
    hits = []
    for label, pattern in SUGGESTED_VOCABULARY_PATTERNS.items():
        if re.search(pattern, text or "", flags=re.IGNORECASE):
            hits.append(label)
    return hits


def text_has_skill(skill: str, text: str) -> bool:
    if not text:
        return False
    return bool(re.search(rf"(?<![A-Za-z0-9+#.]){re.escape(skill)}(?![A-Za-z0-9+#.-])", text, flags=re.I))


def build_report(
    new_v3: list[dict[str, str]],
    ready_rows: list[dict[str, str]],
    role_only_rows: list[dict[str, str]],
    assessed: list[dict[str, str]],
) -> str:
    lines = [
        "# V4 Role-Only Failure Audit",
        "",
        f"- Batch ID: `{BATCH_ID}`",
        "- Scope: generated CSV audit only. No network, DB write, OpenAI call, embedding, RAG write, or recommendation rebuild.",
        f"- New v3 accepted rows: {len(new_v3)}",
        f"- New v4 skill_evidence_ready rows: {len(ready_rows)}",
        f"- New v4 role_evidence_only rows: {len(role_only_rows)}",
        "",
        "## Funnel By Role",
        "",
        "| Role | v3 Accepted | v4 Ready | v4 Role-Only | Role-Only Rate |",
        "|---|---:|---:|---:|---:|",
    ]
    roles = sorted({role_of(row) for row in new_v3 + ready_rows + role_only_rows})
    for role in roles:
        v3_count = sum(role_of(row) == role for row in new_v3)
        ready_count = sum(role_of(row) == role for row in ready_rows)
        role_only_count = sum(role_of(row) == role for row in role_only_rows)
        rate = role_only_count / v3_count * 100 if v3_count else 0
        lines.append(f"| {role} | {v3_count} | {ready_count} | {role_only_count} | {rate:.1f}% |")

    lines.extend(["", "## Role-Only By Company", "", "| Company | Role | Role-Only Count |", "|---|---|---:|"])
    for (company, role), count in sorted(Counter((row["company"], row["validated_job_role_category"]) for row in assessed).items()):
        lines.append(f"| {md(company)} | {role} | {count} |")

    lines.extend(["", "## Failure Status Distribution", "", "| Status | Count |", "|---|---:|"])
    status_counts = Counter(row["failure_status"] for row in assessed)
    for status, count in status_counts.most_common():
        lines.append(f"| {status} | {count} |")

    add_focus_section(lines, "OpenAI", assessed)
    add_builder_section(lines, assessed)

    lines.extend(
        [
            "",
            "## Field Mapping And Parsing Conclusion",
            "",
            field_mapping_conclusion(assessed),
            "",
            "## Verifier Improvement Recommendations",
            "",
            "### Must Fix Bugs",
            "",
            "- Fix section extraction for Ashby-style descriptions. Many rows have long raw descriptions but near-empty `responsibilities`, `requirements`, and `preferred_qualifications` fields.",
            "- The current section extractor depends heavily on sentence punctuation and a small set of headings; long structured postings without those cues can become empty evidence fields.",
            "- Re-run v3/v4 after improving field mapping before judging OpenAI, Product Engineer, or FDE boards as low-value sources.",
            "",
            "### Vocabulary To Consider Carefully",
            "",
            "- `Agent Infrastructure`, `Model Inference`, `AI Platform`, and `Developer Platform` can be considered for AI Backend, but only when paired with service/API/deployment context.",
            "- `Build Integrations`, `API Integration`, `End-to-End Product`, and `Ship Product` can be used as Builder role-context signals, not as automatic technical skill evidence.",
            "- `Product Engineering` should remain role-context unless concrete technologies such as API, Full Stack, React, TypeScript, Python, Automation, or Integration appear in checked fields.",
            "",
            "### Criteria Not To Loosen",
            "",
            "- Do not mark a row skill-ready only because the title contains AI, FDE, or Product Engineer.",
            "- Do not infer specific technologies from product-building language alone.",
            "- Do not force research/model-training rows into AI Backend skill evidence.",
            "",
            "## Data Collection Strategy",
            "",
            "- OpenAI should not be used as a primary skill-ready source in its current form. Keep it as role-context or retry after verifier policy changes, but expect high review noise.",
            "- Builder role-only rows can be useful for an Agent explaining product-builder role examples, but not for skill scoring until direct technologies are verified.",
            "- Frontend still needs a second dedicated board search because this batch produced only one new Frontend skill-ready row.",
            "- Retry timeout boards in this order: Attio, Clay Labs, Summation. Attio has the strongest Builder signal; Clay Labs has Frontend/Data Analyst/AI signals; Summation has Builder/Backend signals.",
        ]
    )
    return "\n".join(lines) + "\n"


def add_focus_section(lines: list[str], company: str, assessed: list[dict[str, str]]) -> None:
    rows = [row for row in assessed if row["company"] == company]
    lines.extend(
        [
            "",
            f"## {company} Detail",
            "",
            f"- Role-only rows: {len(rows)}",
            "",
            "| Status | Count |",
            "|---|---:|",
        ]
    )
    for status, count in Counter(row["failure_status"] for row in rows).most_common():
        lines.append(f"| {status} | {count} |")
    lines.extend(["", "| Role | Title | Status | Reason | Section Len | Raw Len | Detected Expressions |", "|---|---|---|---|---:|---:|---|"])
    for row in rows:
        detected = row["policy_hits_in_sections"] or row["suggested_vocab_hits_in_sections"] or row["suggested_vocab_hits_in_raw_body"] or "-"
        lines.append(
            f"| {row['validated_job_role_category']} | {md(row['title'])} | {row['failure_status']} | "
            f"{md(row['failure_reason'])} | {row['section_text_len']} | {row['raw_body_len']} | {md(detected)} |"
        )


def add_builder_section(lines: list[str], assessed: list[dict[str, str]]) -> None:
    rows = [row for row in assessed if row["validated_job_role_category"] == "Builder"]
    lines.extend(
        [
            "",
            "## Builder Detail",
            "",
            f"- Builder role-only rows: {len(rows)}",
            "",
            "| Company | Count | Status Mix |",
            "|---|---:|---|",
        ]
    )
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["company"]].append(row)
    for company, company_rows in sorted(grouped.items()):
        mix = ", ".join(f"{status}: {count}" for status, count in Counter(row["failure_status"] for row in company_rows).items())
        lines.append(f"| {md(company)} | {len(company_rows)} | {md(mix)} |")
    lines.extend(["", "Builder role-only rows are useful as role-context examples only when they describe product ownership, customer workflow implementation, or end-to-end shipping. They should not affect skill scores unless direct technologies are present."])


def field_mapping_conclusion(assessed: list[dict[str, str]]) -> str:
    missing = sum(row["failure_status"] == "missing_or_unmapped_body" for row in assessed)
    parsing = sum(row["failure_status"] == "parsing_or_format_issue" for row in assessed)
    vocab = sum(row["failure_status"] == "vocabulary_gap" for row in assessed)
    total = len(assessed)
    if missing == 0 and parsing == 0:
        return (
            "No broad field mapping failure was found. Most role-only rows had usable section/raw text, "
            f"while {vocab} rows looked like possible verifier vocabulary gaps."
        )
    return (
        f"Field/parsing issues are the dominant failure mode: missing_or_unmapped_body={missing}/{total}, "
        f"parsing_or_format_issue={parsing}/{total}, vocabulary_gap={vocab}/{total}. "
        "Raw descriptions are present, but the fields consumed by v4 are often empty or too short."
    )


def sample_fields() -> list[str]:
    return [
        "failure_status",
        "failure_reason",
        "company",
        "title",
        "validated_job_role_category",
        "job_url",
        "source_posting_id",
        "responsibilities_len",
        "requirements_len",
        "preferred_qualifications_len",
        "section_text_len",
        "raw_body_len",
        "raw_body_exists",
        "policy_hits_in_sections",
        "policy_hits_in_raw_body",
        "suggested_vocab_hits_in_sections",
        "suggested_vocab_hits_in_raw_body",
        "title_skill_hits",
        "final_skills",
        "rejected_skill_status_counts",
        "body_excerpt",
    ]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def parse_skills(text: str) -> list[str]:
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def unique(items: list[str]) -> list[str]:
    output = []
    for item in items:
        if item not in output:
            output.append(item)
    return output


def role_of(row: dict[str, str]) -> str:
    return value(row, "validated_job_role_category") or value(row, "original_job_role_category") or value(row, "job_role_category")


def snippet(text: str, limit: int = 500) -> str:
    return " ".join((text or "").split())[:limit]


def md(text: str) -> str:
    return str(text or "").replace("|", "\\|").replace("\n", " ")


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
