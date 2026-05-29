import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.services.external_jobs.companies import COMPANIES
from app.services.external_jobs.role_evidence_collection_targets import (
    ROLE_COLLECTION_RULES,
    SKILL_READY_TARGETS,
)


DEFAULT_INPUT = ROOT_DIR / "data" / "exports" / "external_job_postings_role_evidence_v4.csv"
DEFAULT_OUTPUT = ROOT_DIR / "data" / "exports" / "additional_collection_plan_report.md"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the additional evidence collection plan report.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--batch-manifest", type=Path, default=None)
    parser.add_argument("--v3-accepted", type=Path, default=None)
    parser.add_argument("--baseline-input", type=Path, default=None)
    args = parser.parse_args()

    rows = read_csv(args.input.resolve())
    baseline_rows = read_csv(args.baseline_input.resolve()) if args.baseline_input else None
    batch_metrics = load_batch_metrics(rows, args.batch_manifest, args.v3_accepted)
    report = build_report(rows, args.input.resolve(), batch_metrics, baseline_rows)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"Additional collection plan report written: {output}")
    for role in SKILL_READY_TARGETS:
        ready = ready_rows(rows, role)
        target = SKILL_READY_TARGETS[role]
        print(f"{role}: current={len(ready)}, target={target}, shortage={max(0, target - len(ready))}")


def build_report(
    rows: list[dict[str, str]],
    input_path: Path,
    batch_metrics: dict | None,
    baseline_rows: list[dict[str, str]] | None,
) -> str:
    sources = Counter(company["ats"] for company in COMPANIES)
    lines = [
        "# Additional Role Evidence Collection Plan",
        "",
        f"- Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"- Current evidence dataset: `{input_path.as_posix()}`",
        "- Safety scope: planning and isolated batch export only. No DB write, recommendation rebuild, RAG write, or embedding execution is included.",
        "",
        "## Current Collection Pipeline",
        "",
        "1. `app/services/external_jobs/ats_collectors.py` fetches every public posting from configured ATS boards.",
        "2. `app/services/external_jobs/persistence.py` normally saves postings to `external_job_postings`, extracting broad keyword skills from descriptions.",
        "3. `app/services/external_jobs/scheduler.py` invokes the DB collector once per configured interval, currently intended as daily collection.",
        "4. `scripts/export_external_job_postings_csv.py` exports DB rows.",
        "5. `scripts/export_role_analysis_v2_csv.py` applies title-based seven-role mapping and company balancing.",
        "6. The evidence v3/v4 scripts apply role validation, duplicate handling, and direct-text skill verification.",
        "",
        "### Configured Public ATS Boards",
        "",
        f"- Total configured company boards: {len(COMPANIES)}",
        f"- Greenhouse: {sources['greenhouse']}",
        f"- Ashby: {sources['ashby']}",
        f"- Lever: {sources['lever']}",
        "",
        "Configured board companies:",
        "",
        f"- Greenhouse: {', '.join(company['company'] for company in COMPANIES if company['ats'] == 'greenhouse')}",
        f"- Ashby: {', '.join(company['company'] for company in COMPANIES if company['ats'] == 'ashby')}",
        f"- Lever: {', '.join(company['company'] for company in COMPANIES if company['ats'] == 'lever')}",
        "",
        "The current ATS endpoints return complete public boards; they do not accept the role keyword list as a search query. Expanded keywords therefore improve local candidate screening, while immediate new volume additionally depends on newly posted jobs or reviewed extra company boards.",
        "",
        "## Why the Evidence Sample Is Uneven",
        "",
        "- Title classification previously favored titles explicitly containing `AI/ML`, `backend`, `data engineer`, or `data scientist`; phrases such as `Product Analyst`, `React Engineer`, and AI product-builder variants were undercovered.",
        "- `Builder` initially included many `Solutions Engineer` postings, which were removed because they did not represent the product-building role definition.",
        "- Keyword extraction and modeled `final_skills` inflated some skill counts; direct-text v4 verification reduced many otherwise accepted postings to role-only evidence.",
        "- Existing boards contain abundant Data Scientist postings but substantially fewer verified Builder and Frontend technology requirements.",
        "- Company concentration is moderate in several low-volume roles, so simply taking more records from the same boards may preserve bias.",
        "",
        "## Skill-Ready Goal and Current Shortage",
        "",
        "| Role | Current Skill-Ready | Target | Shortage | Unique Companies | Top 1 Company Share | Top 3 Company Share |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for role, target in SKILL_READY_TARGETS.items():
        role_rows = ready_rows(rows, role)
        company_counts = Counter(value(row, "company") for row in role_rows)
        lines.append(
        f"| {role} | {len(role_rows):,} | {target:,} | {max(0, target - len(role_rows)):,} | "
            f"{len(company_counts):,} | {company_share(company_counts, 1):.1f}% | "
            f"{company_share(company_counts, 3):.1f}% |"
        )

    if baseline_rows is not None:
        lines.extend(
            [
                "",
                "## Baseline Comparison",
                "",
                "| Role | Baseline Skill-Ready | Current Skill-Ready | Increase | Remaining Shortage | Baseline Unique Companies | Current Unique Companies | Top 1 Share Change | Top 3 Share Change |",
                "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
            ]
        )
        for role, target in SKILL_READY_TARGETS.items():
            baseline_role_rows = ready_rows(baseline_rows, role)
            current_role_rows = ready_rows(rows, role)
            baseline_companies = Counter(value(row, "company") for row in baseline_role_rows)
            current_companies = Counter(value(row, "company") for row in current_role_rows)
            lines.append(
                f"| {role} | {len(baseline_role_rows):,} | {len(current_role_rows):,} | "
                f"{len(current_role_rows) - len(baseline_role_rows):+,} | "
                f"{max(0, target - len(current_role_rows)):,} | {len(baseline_companies):,} | "
                f"{len(current_companies):,} | {company_share(baseline_companies, 1):.1f}% -> "
                f"{company_share(current_companies, 1):.1f}% | {company_share(baseline_companies, 3):.1f}% -> "
                f"{company_share(current_companies, 3):.1f}% |"
            )

    lines.extend(["", "## Additional Batch Funnel", ""])
    if batch_metrics is None:
        lines.append("- No additional collection batch has been executed or supplied. Run this report again with `--batch-manifest` and `--v3-accepted` after an approved batch.")
    else:
        lines.extend(
            [
                f"- Batch ID: `{batch_metrics['batch_id']}`",
                f"- Batch kind: `{batch_metrics['batch_kind']}`",
                f"- Source raw postings evaluated: {batch_metrics['raw_rows']:,}",
                f"- Keyword/title candidate postings: {batch_metrics['candidate_rows']:,}",
                f"- New v3 accepted postings: {batch_metrics['v3_accepted_new']:,}",
                f"- New v4 skill-ready postings: {batch_metrics['v4_skill_ready_new']:,}",
                f"- Candidate to v3 accepted pass rate: {batch_metrics['v3_pass_rate']:.1f}%",
                f"- Candidate to v4 skill-ready pass rate: {batch_metrics['v4_ready_pass_rate']:.1f}%",
                "",
                "| Role | New Raw Candidates | New v3 Accepted | New v4 Skill-Ready | Skill-Ready Pass Rate |",
                "|---|---:|---:|---:|---:|",
            ]
        )
        for role in SKILL_READY_TARGETS:
            candidate = batch_metrics["candidate_by_role"].get(role, 0)
            v3 = batch_metrics["v3_by_role"].get(role, 0)
            v4 = batch_metrics["v4_ready_by_role"].get(role, 0)
            rate = v4 / candidate * 100 if candidate else 0.0
            lines.append(f"| {role} | {candidate:,} | {v3:,} | {v4:,} | {rate:.1f}% |")

    lines.extend(["", "## Current Concentration and Technology Company Coverage", ""])
    for role in SKILL_READY_TARGETS:
        role_rows = ready_rows(rows, role)
        distinct_groups = {
            value(row, "duplicate_group_id")
            for row in role_rows
            if value(row, "duplicate_status") == "distinct_opening" and value(row, "duplicate_group_id")
        }
        lines.extend(
            [
                f"### {role}",
                "",
                f"- Skill-ready postings: {len(role_rows):,}",
                f"- Unique companies: {len({value(row, 'company') for row in role_rows}):,}",
                f"- Same-company/similar-title distinct-opening groups: {len(distinct_groups):,}",
                "",
                "| Verified Skill | Posting Count | Unique Company Count |",
                "|---|---:|---:|",
            ]
        )
        for skill, count, company_count in technology_company_coverage(role_rows)[:15]:
            lines.append(f"| {skill} | {count:,} | {company_count:,} |")
        if not role_rows:
            lines.append("| No ready evidence | - | - |")
        lines.append("")

    lines.extend(["## Expanded Candidate Keywords", ""])
    for rule in sorted(ROLE_COLLECTION_RULES, key=lambda item: item["priority"]):
        lines.extend(
            [
                f"### {rule['role']}",
                "",
                f"- Include title phrases: {', '.join(rule['include_phrases'])}",
                f"- Exclude or hold back at candidate screening: {', '.join(rule['exclude_phrases']) or 'None'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Minimal Pipeline Extension",
            "",
            "- `app/services/external_jobs/role_evidence_collection_targets.py`: isolated target counts and expanded title candidate rules.",
            "- `scripts/collect_role_evidence_batch.py`: fetches public ATS boards only with explicit `--execute`, writes a separated batch, and never writes the DB. Expanded phrases are checked first, then the existing seven-role title classifier is retained as a fallback so new valid postings are not lost.",
            "- `scripts/generate_additional_collection_plan_report.py`: recalculates shortage and company/technology concentration from any v4 output.",
            "- Existing v3 and v4 scripts remain the quality gates for accepted roles and verified skills.",
            "",
            "Extra public company boards should only be added through a reviewed JSON list passed to the batch script. Board slugs should be verified before any collection run; they are not added speculatively in this plan.",
            "",
            "## Safe Batch Execution Flow",
            "",
            "The following commands are prepared but must not be executed until collection is approved:",
            "",
            "```powershell",
            "$batch = 'evidence_boost_20260527_01'",
            "python backend/scripts/collect_role_evidence_batch.py --execute --batch-id $batch",
            "python backend/scripts/build_role_job_evidence_v3.py --input \"backend/data/exports/additional_batches/external_job_postings_role_candidates_combined_$batch.csv\" --accepted-output \"backend/data/exports/additional_batches/external_job_postings_role_evidence_v3_$batch.csv\" --review-output \"backend/data/exports/additional_batches/external_job_postings_role_evidence_review_v3_$batch.csv\" --report-output \"backend/data/exports/additional_batches/role_job_evidence_v3_validation_report_$batch.md\"",
            "python backend/scripts/build_role_job_evidence_v4.py --input \"backend/data/exports/additional_batches/external_job_postings_role_evidence_v3_$batch.csv\" --output \"backend/data/exports/additional_batches/external_job_postings_role_evidence_v4_$batch.csv\" --removed-output \"backend/data/exports/additional_batches/external_job_postings_role_evidence_v4_removed_or_unverified_$batch.csv\" --report-output \"backend/data/exports/additional_batches/role_job_evidence_v4_validation_report_$batch.md\"",
            "python backend/scripts/generate_additional_collection_plan_report.py --input \"backend/data/exports/additional_batches/external_job_postings_role_evidence_v4_$batch.csv\" --batch-manifest \"backend/data/exports/additional_batches/external_job_postings_additional_manifest_$batch.json\" --v3-accepted \"backend/data/exports/additional_batches/external_job_postings_role_evidence_v3_$batch.csv\" --output \"backend/data/exports/additional_batches/additional_collection_result_report_$batch.md\"",
            "```",
            "",
            "For reviewed extra ATS boards:",
            "",
            "```powershell",
            "python backend/scripts/collect_role_evidence_batch.py --execute --batch-id $batch --additional-companies-json backend/data/collection/additional_public_boards_reviewed.json",
            "```",
            "",
            "## Post-Collection Report Requirements",
            "",
            "- For each role: current skill-ready count, goal, shortage, newly fetched raw postings, v3 accepted count, v4 skill-ready count, and pass rate.",
            "- For each role: postings, unique companies, top-one and top-three company shares, repeated similar-title groups, and verified-skill company coverage.",
            "- RAG retrieval policy: display at most one result per `company + duplicate_group_id` in a response.",
            "- Future market scoring policy: store both direct posting count and direct unique-company count for each verified skill.",
            "",
            "## Recommendation Before Collection",
            "",
            "- Prioritize Builder, Frontend Developer, AI Backend Developer, Data Analyst, Data Engineer, and Backend Developer in that order of shortage and reliability risk.",
            "- Keep Data Scientist available for monitoring, but no deliberate expansion is required for the current minimum target.",
            "- Do not rebuild JobRoleSkillEvidence or create RAG embeddings until the additional batch has passed v3/v4 verification and company concentration review.",
            "",
        ]
    )
    return "\n".join(lines)


def load_batch_metrics(
    v4_rows: list[dict[str, str]],
    manifest_path: Path | None,
    v3_path: Path | None,
) -> dict | None:
    if manifest_path is None or v3_path is None:
        return None
    manifest = json.loads(manifest_path.resolve().read_text(encoding="utf-8"))
    batch_id = manifest["batch_id"]
    v3_rows = read_csv(v3_path.resolve())
    is_rescreen = manifest.get("batch_kind") == "local_rescreen"

    def is_new_batch_row(row: dict[str, str]) -> bool:
        if is_rescreen:
            return (
                value(row, "rescreen_batch_id") == batch_id
                and value(row, "rescreen_status")
                in {"newly_recovered_by_expanded_rule", "recovered_by_fallback"}
            )
        return value(row, "batch_id") == batch_id

    new_v3 = [row for row in v3_rows if is_new_batch_row(row)]
    new_v4_ready = [
        row
        for row in v4_rows
        if is_new_batch_row(row) and value(row, "evidence_quality") == "skill_evidence_ready"
    ]
    candidate_count = int(
        manifest.get(
            "newly_recovered_total" if is_rescreen else "candidate_rows",
            0,
        )
    )
    return {
        "batch_id": batch_id,
        "batch_kind": manifest.get("batch_kind", "ats_collection"),
        "raw_rows": int(manifest.get("input_raw_rows", manifest.get("raw_rows", 0))),
        "candidate_rows": candidate_count,
        "v3_accepted_new": len(new_v3),
        "v4_skill_ready_new": len(new_v4_ready),
        "v3_pass_rate": len(new_v3) / candidate_count * 100 if candidate_count else 0.0,
        "v4_ready_pass_rate": len(new_v4_ready) / candidate_count * 100 if candidate_count else 0.0,
        "candidate_by_role": manifest.get(
            "newly_recovered_total_by_role" if is_rescreen else "candidate_role_counts",
            {},
        ),
        "v3_by_role": Counter(role_of(row) for row in new_v3),
        "v4_ready_by_role": Counter(role_of(row) for row in new_v4_ready),
    }


def ready_rows(rows: list[dict[str, str]], role: str) -> list[dict[str, str]]:
    return [
        row
        for row in rows
        if role_of(row) == role and value(row, "evidence_quality") == "skill_evidence_ready"
    ]


def company_share(counts: Counter[str], limit: int) -> float:
    total = sum(counts.values())
    return sum(count for _, count in counts.most_common(limit)) / total * 100 if total else 0.0


def technology_company_coverage(rows: list[dict[str, str]]) -> list[tuple[str, int, int]]:
    posting_counts: Counter[str] = Counter()
    companies: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        for skill in parse_skills(value(row, "verified_skills")):
            posting_counts[skill] += 1
            companies[skill].add(value(row, "company"))
    return sorted(
        [(skill, count, len(companies[skill])) for skill, count in posting_counts.items()],
        key=lambda item: (-item[1], -item[2], item[0]),
    )


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def parse_skills(text: str) -> list[str]:
    return [part.strip() for part in text.split(";") if part.strip()]


def role_of(row: dict[str, str]) -> str:
    return value(row, "validated_job_role_category") or value(row, "original_job_role_category")


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


if __name__ == "__main__":
    main()
