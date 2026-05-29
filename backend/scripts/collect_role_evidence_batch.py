import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.services.external_jobs.ats_collectors import fetch_company_jobs
from app.services.external_jobs.companies import COMPANIES
from app.services.external_jobs.role_evidence_collection_targets import (
    ROLE_COLLECTION_RULES,
    SKILL_READY_TARGETS,
)
from app.services.external_jobs.role_classifier import classify_role
from app.services.external_jobs.skill_extractor import extract_skills
from export_role_analysis_csv import clean_description, extract_sections


DEFAULT_BASELINE = ROOT_DIR / "data" / "exports" / "external_job_postings_role_analysis_ml_skills_v2.csv"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "data" / "exports" / "additional_batches"

RAW_FIELDS = [
    "batch_id",
    "company",
    "title",
    "location",
    "department",
    "description",
    "job_url",
    "source",
    "external_id",
    "candidate_role",
    "candidate_match_phrase",
    "candidate_exclusion_phrase",
    "collected_at",
]

CANDIDATE_FIELDS = [
    "batch_id",
    "id",
    "company",
    "title",
    "job_role_category",
    "location",
    "department",
    "skills",
    "responsibilities",
    "requirements",
    "preferred_qualifications",
    "job_url",
    "source",
    "collected_at",
    "predicted_skills",
    "predicted_skill_scores",
    "final_skills",
    "skills_method",
    "candidate_match_phrase",
    "candidate_exclusion_phrase",
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Collect an isolated additional role-evidence batch from public ATS boards."
    )
    parser.add_argument("--execute", action="store_true", help="Perform ATS network requests and write batch files.")
    parser.add_argument("--batch-id", default=None)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--baseline-input", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument(
        "--additional-companies-json",
        type=Path,
        default=None,
        help="Optional reviewed JSON array of additional {company, ats, slug} public board entries.",
    )
    args = parser.parse_args()

    companies = load_companies(args.additional_companies_json)
    if not args.execute:
        print(json.dumps(dry_run_summary(companies), ensure_ascii=False, indent=2))
        return

    batch_id = args.batch_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / f"external_job_postings_additional_raw_{batch_id}.csv"
    candidate_path = output_dir / f"external_job_postings_role_candidates_{batch_id}.csv"
    combined_path = output_dir / f"external_job_postings_role_candidates_combined_{batch_id}.csv"
    manifest_path = output_dir / f"external_job_postings_additional_manifest_{batch_id}.json"

    raw_rows, candidate_rows, source_results = collect_batch(companies, batch_id)
    combined_rows = merge_with_baseline(args.baseline_input.resolve(), candidate_rows)
    write_csv(raw_path, RAW_FIELDS, raw_rows)
    write_csv(candidate_path, CANDIDATE_FIELDS, candidate_rows)
    write_csv(combined_path, combined_fields(combined_rows), combined_rows)
    manifest = {
        "batch_id": batch_id,
        "created_at": utcnow_iso(),
        "network_collection_executed": True,
        "database_writes": False,
        "raw_rows": len(raw_rows),
        "candidate_rows": len(candidate_rows),
        "candidate_role_counts": role_counts(candidate_rows),
        "combined_rows": len(combined_rows),
        "paths": {
            "raw": str(raw_path),
            "candidates": str(candidate_path),
            "combined_candidates": str(combined_path),
        },
        "source_results": source_results,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({**manifest, "paths": {**manifest["paths"], "manifest": str(manifest_path)}}, ensure_ascii=False, indent=2))


def dry_run_summary(companies: list[dict]) -> dict:
    by_source = {}
    for company in companies:
        ats = company["ats"]
        by_source[ats] = by_source.get(ats, 0) + 1
    return {
        "mode": "dry-run",
        "network_collection_executed": False,
        "database_writes": False,
        "embedding_requests": False,
        "configured_public_boards": len(companies),
        "boards_by_ats": by_source,
        "active_roles": [rule["role"] for rule in ROLE_COLLECTION_RULES],
        "skill_ready_targets": SKILL_READY_TARGETS,
        "role_keyword_rules": ROLE_COLLECTION_RULES,
        "execution_note": "Use --execute with a batch ID only after review. Outputs remain isolated from DB and baseline CSVs.",
    }


def load_companies(additional_path: Path | None) -> list[dict]:
    if not additional_path:
        return list(COMPANIES)
    additional = json.loads(additional_path.resolve().read_text(encoding="utf-8"))
    if not isinstance(additional, list):
        raise ValueError("--additional-companies-json must contain a JSON list.")
    companies = []
    configured = {(item["ats"], item["slug"]) for item in COMPANIES}
    known = set()
    for item in additional:
        if not all(item.get(key) for key in ["company", "ats", "slug"]):
            raise ValueError("Each additional company must provide company, ats, and slug.")
        if item["ats"] not in {"greenhouse", "lever", "ashby"}:
            raise ValueError(f"Unsupported ATS in additional company config: {item['ats']}")
        identity = (item["ats"], item["slug"])
        if identity in configured:
            raise ValueError(f"Additional company is already configured in base boards: {identity}")
        if identity not in known:
            companies.append(item)
            known.add(identity)
    return companies


def collect_batch(companies: list[dict], batch_id: str) -> tuple[list[dict], list[dict], list[dict]]:
    raw_rows = []
    candidate_rows = []
    source_results = []
    for company_info in companies:
        try:
            jobs = fetch_company_jobs(company_info)
            status = "success"
            reason = ""
        except Exception as exc:
            jobs = []
            status = "failed"
            reason = str(exc)
        source_results.append(
            {
                "company": company_info["company"],
                "ats": company_info["ats"],
                "status": status,
                "fetched": len(jobs),
                "reason": reason,
            }
        )
        for job in jobs:
            candidate = candidate_role(job.get("title") or "")
            raw_rows.append(raw_record(batch_id, job, candidate))
            if candidate and not candidate["excluded"]:
                candidate_rows.append(candidate_record(batch_id, job, candidate))
    return raw_rows, candidate_rows, source_results


def candidate_role(title: str) -> dict | None:
    normalized = " ".join(title.lower().split())
    for rule in sorted(ROLE_COLLECTION_RULES, key=lambda item: item["priority"]):
        include = first_phrase_match(normalized, rule["include_phrases"])
        if not include:
            continue
        exclusion = first_phrase_match(normalized, rule["exclude_phrases"])
        return {
            "role": rule["role"],
            "include_phrase": include,
            "exclusion_phrase": exclusion,
            "excluded": bool(exclusion),
        }
    for rule in sorted(ROLE_COLLECTION_RULES, key=lambda item: item["priority"]):
        exclusion = first_phrase_match(normalized, rule["exclude_phrases"])
        if exclusion:
            return {
                "role": rule["role"],
                "include_phrase": "excluded_title_phrase",
                "exclusion_phrase": exclusion,
                "excluded": True,
            }
    existing_role = classify_role(title)
    if existing_role != "Other":
        return {
            "role": existing_role,
            "include_phrase": "existing_title_classifier",
            "exclusion_phrase": "",
            "excluded": False,
        }
    return None


def first_phrase_match(normalized_title: str, phrases: list[str]) -> str:
    for phrase in phrases:
        normalized_phrase = " ".join(phrase.lower().split())
        if re.search(rf"(?<![a-z0-9]){re.escape(normalized_phrase)}(?![a-z0-9])", normalized_title):
            return phrase
    return ""


def raw_record(batch_id: str, job: dict, candidate: dict | None) -> dict:
    return {
        "batch_id": batch_id,
        "company": job.get("company") or "",
        "title": job.get("title") or "",
        "location": job.get("location") or "",
        "department": job.get("department") or "",
        "description": job.get("description") or "",
        "job_url": job.get("job_url") or "",
        "source": job.get("source") or "",
        "external_id": job.get("external_id") or "",
        "candidate_role": candidate["role"] if candidate else "",
        "candidate_match_phrase": candidate["include_phrase"] if candidate else "",
        "candidate_exclusion_phrase": candidate["exclusion_phrase"] if candidate else "",
        "collected_at": utcnow_iso(),
    }


def candidate_record(batch_id: str, job: dict, candidate: dict) -> dict:
    clean_text = clean_description(job.get("description") or "")
    sections = extract_sections(clean_text)
    skills = extract_skills(
        " ".join([job.get("title") or "", job.get("department") or "", clean_text])
    )
    skill_text = "; ".join(skills)
    return {
        "batch_id": batch_id,
        "id": f"{job.get('source') or ''}:{job.get('external_id') or job.get('job_url') or ''}",
        "company": job.get("company") or "",
        "title": job.get("title") or "",
        "job_role_category": candidate["role"],
        "location": job.get("location") or "",
        "department": job.get("department") or "",
        "skills": skill_text,
        "responsibilities": sections.get("responsibilities") or "",
        "requirements": sections.get("requirements") or "",
        "preferred_qualifications": sections.get("preferred_qualifications") or "",
        "job_url": job.get("job_url") or "",
        "source": job.get("source") or "",
        "collected_at": utcnow_iso(),
        "predicted_skills": "",
        "predicted_skill_scores": "",
        "final_skills": skill_text,
        "skills_method": "keyword",
        "candidate_match_phrase": candidate["include_phrase"],
        "candidate_exclusion_phrase": "",
    }


def merge_with_baseline(baseline_path: Path, candidate_rows: list[dict]) -> list[dict]:
    baseline_rows = read_csv(baseline_path)
    combined = list(baseline_rows)
    identities = {
        (value(row, "job_url"), value(row, "company").lower(), value(row, "title").lower())
        for row in baseline_rows
    }
    for row in candidate_rows:
        identity = (value(row, "job_url"), value(row, "company").lower(), value(row, "title").lower())
        if identity in identities:
            continue
        combined.append(row)
        identities.add(identity)
    return combined


def combined_fields(rows: list[dict]) -> list[str]:
    fields = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    return fields


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def role_counts(rows: list[dict]) -> dict[str, int]:
    counts = {}
    for row in rows:
        role = row["job_role_category"]
        counts[role] = counts.get(role, 0) + 1
    return counts


def value(row: dict, field: str) -> str:
    return (row.get(field) or "").strip()


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
