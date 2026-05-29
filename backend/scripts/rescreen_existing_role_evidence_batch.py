from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.services.external_jobs.role_evidence_collection_targets import SKILL_READY_TARGETS  # noqa: E402
from app.services.external_jobs.skill_extractor import extract_skills  # noqa: E402
from collect_role_evidence_batch import candidate_role  # noqa: E402
from export_role_analysis_csv import clean_description, extract_sections  # noqa: E402


DEFAULT_RAW_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings.csv"
DEFAULT_V2_INPUT = (
    ROOT_DIR / "data" / "exports" / "external_job_postings_role_analysis_ml_skills_v2.csv"
)
DEFAULT_V4_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v4.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "exports" / "rescreen_batches"
KNOWN_DB_SNAPSHOT_ROWS = 12468
CURRENT_SKILL_READY = {
    "AI Backend Developer": 50,
    "Backend Developer": 68,
    "Builder": 17,
    "Data Analyst": 31,
    "Data Engineer": 44,
    "Data Scientist": 109,
    "Frontend Developer": 15,
}
PRIORITY_REPORT_ROLES = [
    "AI Backend Developer",
    "Backend Developer",
    "Builder",
    "Data Analyst",
    "Data Engineer",
    "Frontend Developer",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Locally re-screen existing exported job postings using expanded role evidence "
            "title rules. The script performs no network requests, database writes, or "
            "OpenAI calls."
        )
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_RAW_INPUT)
    parser.add_argument("--v2-input", type=Path, default=DEFAULT_V2_INPUT)
    parser.add_argument("--current-v4-input", type=Path, default=DEFAULT_V4_INPUT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--expected-source-rows", type=int, default=KNOWN_DB_SNAPSHOT_ROWS)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Write isolated batch CSV/report files after freshness checks pass.",
    )
    parser.add_argument(
        "--allow-stale-input",
        action="store_true",
        help="Explicitly write a batch from an older export snapshot with a warning.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Input file does not exist: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        return list(csv.DictReader(source))


def text(row: dict[str, str], column: str) -> str:
    return (row.get(column) or "").strip()


def identity_values(rows: list[dict[str, str]]) -> tuple[set[str], set[str]]:
    ids = {text(row, "id") for row in rows if text(row, "id")}
    urls = {text(row, "job_url") for row in rows if text(row, "job_url")}
    return ids, urls


def is_already_present(
    raw_row: dict[str, str], existing_ids: set[str], existing_urls: set[str]
) -> bool:
    posting_id = text(raw_row, "id")
    url = text(raw_row, "job_url")
    return bool((posting_id and posting_id in existing_ids) or (url and url in existing_urls))


def normalized_timestamp_max(rows: list[dict[str, str]]) -> str:
    timestamps = [text(row, "collected_at") for row in rows if text(row, "collected_at")]
    return max(timestamps) if timestamps else ""


def batch_id_or_default(value: str | None) -> str:
    if value:
        return value
    return f"evidence_rescreen_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def row_for_candidate(
    raw_row: dict[str, str],
    batch_id: str,
    role_match: dict[str, Any],
    present_in_v2: bool,
) -> dict[str, str]:
    title = text(raw_row, "title")
    description = clean_description(text(raw_row, "description"))
    sections = extract_sections(description)
    skill_source = " ".join(
        part for part in (title, text(raw_row, "department"), description) if part
    )
    extracted_skills = "; ".join(extract_skills(skill_source))
    include_rule = role_match["include_phrase"]
    exclusion_rule = role_match["exclusion_phrase"]

    if role_match["excluded"]:
        status = "excluded_by_new_rule"
        method = "exclusion_rule"
    elif present_in_v2:
        status = "already_in_v2"
        method = (
            "fallback_classifier"
            if include_rule == "existing_title_classifier"
            else "expanded_title_rule"
        )
    elif include_rule == "existing_title_classifier":
        status = "recovered_by_fallback"
        method = "fallback_classifier"
    else:
        status = "newly_recovered_by_expanded_rule"
        method = "expanded_title_rule"

    return {
        "rescreen_batch_id": batch_id,
        "id": text(raw_row, "id"),
        "company": text(raw_row, "company"),
        "title": title,
        "job_role_category": role_match["role"],
        "location": text(raw_row, "location"),
        "department": text(raw_row, "department"),
        "skills": extracted_skills,
        "responsibilities": sections.get("responsibilities", ""),
        "requirements": sections.get("requirements", ""),
        "preferred_qualifications": sections.get("preferred_qualifications", ""),
        "job_url": text(raw_row, "job_url"),
        "source": text(raw_row, "source"),
        "collected_at": text(raw_row, "collected_at"),
        "predicted_skills": "",
        "predicted_skill_scores": "",
        "final_skills": extracted_skills,
        "skills_method": "keyword",
        "candidate_detection_method": method,
        "matched_include_title_rule": include_rule,
        "matched_exclusion_title_rule": exclusion_rule,
        "already_present_in_v2": str(present_in_v2).lower(),
        "source_posting_id": text(raw_row, "id"),
        "rescreen_status": status,
    }


def baseline_v2_row(row: dict[str, str], batch_id: str) -> dict[str, str]:
    return {
        "rescreen_batch_id": batch_id,
        "id": text(row, "id"),
        "company": text(row, "company"),
        "title": text(row, "title"),
        "job_role_category": text(row, "job_role_category"),
        "location": text(row, "location"),
        "department": text(row, "department"),
        "skills": text(row, "skills"),
        "responsibilities": text(row, "responsibilities"),
        "requirements": text(row, "requirements"),
        "preferred_qualifications": text(row, "preferred_qualifications"),
        "job_url": text(row, "job_url"),
        "source": text(row, "source"),
        "collected_at": text(row, "collected_at"),
        "predicted_skills": text(row, "predicted_skills"),
        "predicted_skill_scores": text(row, "predicted_skill_scores"),
        "final_skills": text(row, "final_skills"),
        "skills_method": text(row, "skills_method"),
        "candidate_detection_method": "existing_v2_baseline",
        "matched_include_title_rule": "",
        "matched_exclusion_title_rule": "",
        "already_present_in_v2": "true",
        "source_posting_id": text(row, "id"),
        "rescreen_status": "already_in_v2",
    }


def write_csv(path: Path, rows: list[dict[str, str]], columns: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def percent(value: int, total: int) -> str:
    return f"{(value / total * 100):.1f}%" if total else "0.0%"


def company_concentration(rows: list[dict[str, str]], role: str) -> tuple[int, str, str]:
    counts = Counter(
        text(row, "company")
        for row in rows
        if text(row, "job_role_category") == role and text(row, "company")
    )
    total = sum(counts.values())
    if not total:
        return 0, "0.0%", "0.0%"
    values = [count for _, count in counts.most_common()]
    return len(counts), percent(values[0], total), percent(sum(values[:3]), total)


def current_skill_ready(rows: list[dict[str, str]]) -> dict[str, int]:
    if not rows:
        return CURRENT_SKILL_READY
    output = Counter()
    for row in rows:
        if text(row, "evidence_quality") == "skill_evidence_ready":
            output[text(row, "validated_job_role_category") or text(row, "job_role_category")] += 1
    return {role: output.get(role, 0) for role in SKILL_READY_TARGETS}


def report_markdown(
    manifest: dict[str, Any],
    new_rows: list[dict[str, str]],
    v4_rows: list[dict[str, str]],
) -> str:
    ready_counts = current_skill_ready(v4_rows)
    new_counts = Counter(text(row, "job_role_category") for row in new_rows)
    cannot_reach_target = [
        role
        for role in PRIORITY_REPORT_ROLES
        if ready_counts.get(role, 0) + new_counts.get(role, 0) < SKILL_READY_TARGETS[role]
    ]
    might_reach_after_validation = [
        role
        for role in PRIORITY_REPORT_ROLES
        if role not in cannot_reach_target
        and ready_counts.get(role, 0) < SKILL_READY_TARGETS[role]
    ]
    batch_id = manifest["batch_id"]
    lines = [
        "# Existing Job Posting Re-screen Plan Report",
        "",
        "## Safety And Input",
        "",
        f"- Batch ID: `{manifest['batch_id']}`",
        f"- Raw input: `{manifest['input']}`",
        f"- Raw rows: {manifest['input_raw_rows']:,}",
        f"- Known DB snapshot rows: {manifest['expected_source_rows']:,}",
        f"- Missing versus known DB snapshot: {manifest['missing_rows_vs_snapshot']:,}",
        f"- Raw export latest `collected_at`: `{manifest['latest_collected_at']}`",
        f"- Input stale: `{str(manifest['input_stale']).lower()}`",
        "- Network requests: `false`",
        "- Database changes: `false`",
        "- OpenAI calls: `false`",
        "",
        "## Candidate Recovery",
        "",
        f"- Existing v2 postings: {manifest['existing_v2_rows']:,}",
        f"- Newly recovered by expanded rule: {manifest['newly_recovered_by_expanded_rule']:,}",
        f"- Recovered by fallback classifier: {manifest['recovered_by_fallback']:,}",
        f"- Excluded by new rule: {manifest['excluded_by_new_rule']:,}",
        "",
        "| Role | Current skill-ready | Target | New candidates before v3/v4 | v3 accepted | v4 skill-ready | Remaining shortage after validation | New companies | Top 1 company share | Top 3 company share |",
        "| --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for role in PRIORITY_REPORT_ROLES:
        role_rows = [row for row in new_rows if text(row, "job_role_category") == role]
        companies, top1, top3 = company_concentration(new_rows, role)
        lines.append(
            f"| {role} | {ready_counts.get(role, 0)} | {SKILL_READY_TARGETS[role]} | "
            f"{len(role_rows)} | pending v3 | pending v4 | pending v4 | "
            f"{companies} | {top1} | {top3} |"
        )

    lines.extend(
        [
            "",
            "The new candidate column is a pre-validation recovery count. A role is not "
            "considered sufficiently reinforced until the recovered rows pass the same v3 "
            "role validation and v4 direct-skill verification gates.",
            "",
            "## Conclusions Before Validation",
            "",
            "- This local re-screen can be run before opening additional ATS boards because it "
            "uses already collected postings only.",
            "- No role should be declared sufficient from recovered candidate counts alone; "
            "v4 `skill_evidence_ready` counts decide that after validation.",
            f"- Even if every recovered candidate passed validation, these roles cannot reach "
            f"their target from this snapshot alone: {', '.join(cannot_reach_target) or 'None'}.",
            f"- These roles have enough pre-validation candidate volume to be decided after "
            f"v3/v4, but are not yet sufficient: {', '.join(might_reach_after_validation) or 'None'}.",
            "- New ATS company-board review should prioritize Frontend Developer and Builder, "
            "then Data Analyst and Data Engineer; AI Backend Developer and Backend Developer "
            "should be revisited if their recovered candidates fail the validation gates.",
            "",
            "## Follow-up Commands",
            "",
            "Run the existing v3 and v4 gates against the isolated combined candidate file, "
            "then regenerate the collection plan comparison report. These commands do not run "
            "as part of re-screen generation.",
            "",
            "```powershell",
            f"$batch = '{batch_id}'",
            "python backend/scripts/build_role_job_evidence_v3.py --input "
            "\"backend/data/exports/rescreen_batches/external_job_postings_role_candidates_combined_$batch.csv\" "
            "--accepted-output \"backend/data/exports/rescreen_batches/external_job_postings_role_evidence_v3_$batch.csv\" "
            "--review-output \"backend/data/exports/rescreen_batches/external_job_postings_role_evidence_review_v3_$batch.csv\" "
            "--report-output \"backend/data/exports/rescreen_batches/role_job_evidence_v3_validation_report_$batch.md\"",
            "python backend/scripts/build_role_job_evidence_v4.py --input "
            "\"backend/data/exports/rescreen_batches/external_job_postings_role_evidence_v3_$batch.csv\" "
            "--output \"backend/data/exports/rescreen_batches/external_job_postings_role_evidence_v4_$batch.csv\" "
            "--removed-output \"backend/data/exports/rescreen_batches/external_job_postings_role_evidence_v4_removed_or_unverified_$batch.csv\" "
            "--report-output \"backend/data/exports/rescreen_batches/role_job_evidence_v4_validation_report_$batch.md\"",
            "python backend/scripts/generate_additional_collection_plan_report.py --input "
            "\"backend/data/exports/rescreen_batches/external_job_postings_role_evidence_v4_$batch.csv\" "
            "--baseline-input backend/data/exports/external_job_postings_role_evidence_v4.csv "
            "--batch-manifest \"backend/data/exports/rescreen_batches/external_job_postings_rescreen_manifest_$batch.json\" "
            "--v3-accepted \"backend/data/exports/rescreen_batches/external_job_postings_role_evidence_v3_$batch.csv\" "
            "--output \"backend/data/exports/rescreen_batches/existing_rescreen_after_validation_report_$batch.md\"",
            "```",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    batch_id = batch_id_or_default(args.batch_id)
    raw_rows = read_csv(args.input)
    v2_rows = read_csv(args.v2_input)
    v4_rows = read_csv(args.current_v4_input) if args.current_v4_input.exists() else []
    existing_ids, existing_urls = identity_values(v2_rows)

    candidates: list[dict[str, str]] = []
    for raw_row in raw_rows:
        match = candidate_role(text(raw_row, "title"))
        if not match:
            continue
        candidates.append(
            row_for_candidate(
                raw_row,
                batch_id,
                match,
                is_already_present(raw_row, existing_ids, existing_urls),
            )
        )

    newly_recovered = [
        row
        for row in candidates
        if row["rescreen_status"]
        in {"newly_recovered_by_expanded_rule", "recovered_by_fallback"}
    ]
    expanded_recovered = [
        row
        for row in candidates
        if row["rescreen_status"] == "newly_recovered_by_expanded_rule"
    ]
    fallback_recovered = [
        row for row in candidates if row["rescreen_status"] == "recovered_by_fallback"
    ]
    excluded = [row for row in candidates if row["rescreen_status"] == "excluded_by_new_rule"]
    combined = [baseline_v2_row(row, batch_id) for row in v2_rows] + newly_recovered

    missing_rows = max(args.expected_source_rows - len(raw_rows), 0)
    stale = bool(args.expected_source_rows and len(raw_rows) < args.expected_source_rows)
    expanded_by_role = Counter(row["job_role_category"] for row in expanded_recovered)
    recovered_by_role = Counter(row["job_role_category"] for row in newly_recovered)
    ready_counts = current_skill_ready(v4_rows)
    recovery_preview = {}
    for role in PRIORITY_REPORT_ROLES:
        role_new_rows = [row for row in newly_recovered if row["job_role_category"] == role]
        companies, top1, top3 = company_concentration(role_new_rows, role)
        recovery_preview[role] = {
            "current_skill_ready": ready_counts.get(role, 0),
            "target_skill_ready": SKILL_READY_TARGETS[role],
            "current_shortage": max(0, SKILL_READY_TARGETS[role] - ready_counts.get(role, 0)),
            "new_candidate_rows_before_v3_v4": len(role_new_rows),
            "new_candidates_by_expanded_rule": expanded_by_role.get(role, 0),
            "new_candidates_by_fallback": len(role_new_rows) - expanded_by_role.get(role, 0),
            "new_unique_companies": companies,
            "new_candidate_top1_company_share": top1,
            "new_candidate_top3_company_share": top3,
            "v3_accepted": "pending_validation",
            "v4_skill_evidence_ready": "pending_validation",
            "remaining_shortage_after_validation": "pending_validation",
        }
    readonly_export_command = (
        "docker compose exec -T backend python scripts/export_external_job_postings_csv.py "
        "--output data/exports/external_job_postings_snapshot_20260527.csv"
    )
    manifest: dict[str, Any] = {
        "batch_id": batch_id,
        "batch_kind": "local_rescreen",
        "mode": "execute" if args.execute else "dry-run",
        "input": str(args.input),
        "v2_input": str(args.v2_input),
        "input_raw_rows": len(raw_rows),
        "expected_source_rows": args.expected_source_rows,
        "missing_rows_vs_snapshot": missing_rows,
        "latest_collected_at": normalized_timestamp_max(raw_rows),
        "input_stale": stale,
        "existing_v2_rows": len(v2_rows),
        "candidate_rows": len(candidates),
        "already_in_v2_candidates": sum(
            row["rescreen_status"] == "already_in_v2" for row in candidates
        ),
        "newly_recovered_by_expanded_rule": len(expanded_recovered),
        "newly_recovered_by_expanded_rule_by_role": dict(sorted(expanded_by_role.items())),
        "recovered_by_fallback": len(fallback_recovered),
        "newly_recovered_total": len(newly_recovered),
        "newly_recovered_total_by_role": dict(sorted(recovered_by_role.items())),
        "role_recovery_preview": recovery_preview,
        "excluded_by_new_rule": len(excluded),
        "combined_candidate_rows": len(combined),
        "network_requests": False,
        "database_changes": False,
        "openai_calls": False,
        "output_files_written": False,
        "readonly_fresh_export_command": readonly_export_command,
    }

    if not args.execute:
        print(json.dumps(manifest, ensure_ascii=False, indent=2))
        return 0

    if stale and not args.allow_stale_input:
        raise SystemExit(
            "Refusing to write an isolated re-screen batch from a stale export. "
            f"The input has {len(raw_rows):,} rows versus the known snapshot "
            f"{args.expected_source_rows:,}. After approval, create a read-only snapshot with: "
            f"{readonly_export_command}"
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    suffix = batch_id
    paths = {
        "rescreen": args.output_dir
        / f"external_job_postings_role_candidates_rescreen_{suffix}.csv",
        "newly_recovered": args.output_dir
        / f"external_job_postings_role_candidates_newly_recovered_{suffix}.csv",
        "combined": args.output_dir
        / f"external_job_postings_role_candidates_combined_{suffix}.csv",
        "manifest": args.output_dir / f"external_job_postings_rescreen_manifest_{suffix}.json",
        "report": args.output_dir / f"existing_rescreen_plan_report_{suffix}.md",
    }
    columns = list(combined[0].keys()) if combined else list(candidates[0].keys())
    write_csv(paths["rescreen"], candidates, columns)
    write_csv(paths["newly_recovered"], newly_recovered, columns)
    write_csv(paths["combined"], combined, columns)
    manifest["output_files_written"] = True
    manifest["outputs"] = {name: str(path) for name, path in paths.items()}
    paths["manifest"].write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    paths["report"].write_text(report_markdown(manifest, newly_recovered, v4_rows), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
