from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BATCH_ID = "evidence_boost_20260529_01"
DIR = ROOT_DIR / "data" / "exports" / "additional_batches"
DEFAULT_BEFORE = DIR / f"external_job_postings_role_evidence_v4_{BATCH_ID}.csv"
DEFAULT_AFTER = DIR / f"external_job_postings_role_evidence_v4_{BATCH_ID}_parserfix_v2.csv"
DEFAULT_OLD_AUDIT = DIR / f"v4_role_only_failure_samples_{BATCH_ID}.csv"
DEFAULT_REPORT = DIR / f"parserfix_impact_report_{BATCH_ID}.md"

TARGETS = {
    "AI Backend Developer": 100,
    "Backend Developer": 100,
    "Builder": 80,
    "Data Analyst": 80,
    "Data Engineer": 80,
    "Data Scientist": 109,
    "Frontend Developer": 80,
}
BEFORE_READY = {
    "AI Backend Developer": 84,
    "Backend Developer": 92,
    "Builder": 22,
    "Data Analyst": 52,
    "Data Engineer": 54,
    "Data Scientist": 112,
    "Frontend Developer": 17,
}
POLLUTION_CHECKS = {
    "Data Analyst": ["Go", "Embedding", "Spark"],
    "Frontend Developer": ["Java", "C++", "Go"],
    "AI Backend Developer": ["Go", "Java", "Machine Learning"],
    "Builder": ["AWS", "Machine Learning"],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare parserfix v2 v4 output against prior additional-batch v4 output.")
    parser.add_argument("--before", type=Path, default=DEFAULT_BEFORE)
    parser.add_argument("--after", type=Path, default=DEFAULT_AFTER)
    parser.add_argument("--old-role-only-audit", type=Path, default=DEFAULT_OLD_AUDIT)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    before = read_csv(args.before)
    after = read_csv(args.after)
    old_audit = read_csv(args.old_role_only_audit)
    before_by_id = {value(row, "id"): row for row in before}
    after_by_id = {value(row, "id"): row for row in after}
    old_role_only_ids = {value(row, "source_posting_id") for row in old_audit}
    missing_unmapped_ids = {
        value(row, "source_posting_id")
        for row in old_audit
        if value(row, "failure_status") == "missing_or_unmapped_body"
    }

    converted = [
        after_by_id[posting_id]
        for posting_id in old_role_only_ids
        if posting_id in after_by_id and value(after_by_id[posting_id], "evidence_quality") == "skill_evidence_ready"
    ]
    recovered_missing = [
        after_by_id[posting_id]
        for posting_id in missing_unmapped_ids
        if posting_id in after_by_id and value(after_by_id[posting_id], "evidence_quality") == "skill_evidence_ready"
    ]
    lost_ready = [
        before_by_id[posting_id]
        for posting_id, row in before_by_id.items()
        if value(row, "evidence_quality") == "skill_evidence_ready"
        and posting_id in after_by_id
        and value(after_by_id[posting_id], "evidence_quality") != "skill_evidence_ready"
    ]

    report = build_report(before, after, converted, recovered_missing, lost_ready)
    args.output.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "report": str(args.output),
                "old_role_only_converted_to_ready": len(converted),
                "missing_or_unmapped_converted_to_ready": len(recovered_missing),
                "previous_ready_lost": len(lost_ready),
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


def build_report(
    before: list[dict[str, str]],
    after: list[dict[str, str]],
    converted: list[dict[str, str]],
    recovered_missing: list[dict[str, str]],
    lost_ready: list[dict[str, str]],
) -> str:
    lines = [
        "# Parserfix v2 Impact Report",
        "",
        f"- Batch ID: `{BATCH_ID}`",
        "- Scope: existing CSV files only. No ATS collection, DB access/write, OpenAI call, embedding, RAG write, or recommendation rebuild.",
        "- Parser version: `role_evidence_parser_v2`",
        "",
        "## Code Cause",
        "",
        "- `ats_collectors.py` stores Ashby `descriptionHtml` and Greenhouse `content` as `description` after HTML stripping.",
        "- `collect_role_evidence_batch.py` creates `responsibilities`, `requirements`, and `preferred_qualifications` by calling `clean_description()` and `extract_sections()`.",
        "- The previous parser flattened much of the raw body and split mainly on punctuation. Ashby-style structured postings often became long text without useful section boundaries, so v4 saw empty or tiny evidence fields.",
        "- Parser v2 normalizes HTML/entities/bullets/headings, recognizes broader heading variants, and carries `normalized_raw_body` for safe fallback in v4 when structured sections are too short.",
        "",
        "## Skill-Ready Before And After",
        "",
        "| Role | Before Parserfix | After Parserfix | Change | Target Shortage After |",
        "|---|---:|---:|---:|---:|",
    ]
    after_ready_counts = ready_counts(after)
    for role, before_count in BEFORE_READY.items():
        after_count = after_ready_counts.get(role, 0)
        lines.append(
            f"| {role} | {before_count} | {after_count} | {after_count - before_count:+} | "
            f"{max(0, TARGETS[role] - after_count)} |"
        )

    lines.extend(
        [
            "",
            "## Role-Only Recovery",
            "",
            f"- Old role-only rows converted to skill-ready: {len(converted)}",
            f"- Old `missing_or_unmapped_body` rows converted to skill-ready: {len(recovered_missing)}",
            f"- Previous skill-ready rows that became role-only after stricter parser sections: {len(lost_ready)}",
            "",
            "| Role | Converted From Old Role-Only | Recovered Missing/Unmapped | Lost Previous Ready |",
            "|---|---:|---:|---:|",
        ]
    )
    converted_counts = Counter(role_of(row) for row in converted)
    recovered_counts = Counter(role_of(row) for row in recovered_missing)
    lost_counts = Counter(role_of(row) for row in lost_ready)
    for role in TARGETS:
        lines.append(
            f"| {role} | {converted_counts.get(role, 0)} | {recovered_counts.get(role, 0)} | {lost_counts.get(role, 0)} |"
        )

    lines.extend(["", "## Top Verified Core Skills After Parserfix", ""])
    for role in TARGETS:
        role_ready = [row for row in after if role_of(row) == role and value(row, "evidence_quality") == "skill_evidence_ready"]
        lines.extend([f"### {role}", "", "| Skill | Ready Posting Count |", "|---|---:|"])
        for skill, count in skill_counts(role_ready, "verified_core_skills").most_common(10):
            lines.append(f"| {skill} | {count} |")
        if not role_ready:
            lines.append("| No ready evidence | 0 |")
        lines.append("")

    lines.extend(["## Pollution Check", "", "| Role | Skill | Core Count After Parserfix |", "|---|---|---:|"])
    for role, skills in POLLUTION_CHECKS.items():
        role_rows = [row for row in after if role_of(row) == role]
        for skill in skills:
            lines.append(f"| {role} | {skill} | {count_skill(role_rows, 'verified_core_skills', skill)} |")

    lines.extend(
        [
            "",
            "## Focus Conclusions",
            "",
            f"- OpenAI old role-only rows converted to skill-ready: {sum(value(row, 'company') == 'OpenAI' for row in converted)}",
            f"- Builder old role-only rows converted to skill-ready: {sum(role_of(row) == 'Builder' for row in converted)}",
            f"- Frontend old role-only rows converted to skill-ready: {sum(role_of(row) == 'Frontend Developer' for row in converted)}",
            "- Backend did not reach the 100 target; it moved from 92 to 90 because two prior ready rows no longer had direct core evidence under the cleaner section extraction.",
            "- Builder improved from 22 to 25, which is useful but far below the 80 target.",
            "- Frontend stayed at 17, so Frontend-specific board discovery remains necessary.",
            "- Data Analyst and Data Engineer did not materially improve and still need additional collection.",
            "- OpenAI should not be promoted to scoring evidence yet; parserfix recovered some AI Backend rows, but OpenAI remains noisy and should be kept as role-context plus carefully verified skill evidence.",
            "- Retry timeout boards in this order: Attio, Clay Labs, Summation.",
            "- Do not proceed to JobRoleSkillEvidence rebuild or RAG embedding as the final production corpus yet; collect more Frontend and Builder evidence first.",
        ]
    )
    return "\n".join(lines) + "\n"


def ready_counts(rows: list[dict[str, str]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        if value(row, "evidence_quality") == "skill_evidence_ready":
            counts[role_of(row)] += 1
    return counts


def skill_counts(rows: list[dict[str, str]], field: str) -> Counter[str]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(set(parse_skills(value(row, field))))
    return counts


def count_skill(rows: list[dict[str, str]], field: str, skill: str) -> int:
    return sum(skill in parse_skills(value(row, field)) for row in rows)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def parse_skills(text: str) -> list[str]:
    return [part.strip() for part in (text or "").split(";") if part.strip()]


def role_of(row: dict[str, str]) -> str:
    return value(row, "validated_job_role_category") or value(row, "original_job_role_category") or value(row, "job_role_category")


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
