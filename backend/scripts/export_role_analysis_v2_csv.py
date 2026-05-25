import argparse
import csv
import random
from collections import Counter, defaultdict
from pathlib import Path

from export_role_analysis_csv import clean_description, extract_sections

ROOT_DIR = Path(__file__).resolve().parents[1]
import sys

sys.path.append(str(ROOT_DIR))

from app.services.external_jobs.skill_extractor import extract_skills
from app.services.external_jobs.role_classifier import (
    ROLE_TITLE_RULES,
    TARGET_ROLES,
    classify_role,
)


OUTPUT_FIELDS = [
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
]

REVIEW_FIELDS = [
    "job_role_category",
    "company",
    "title",
    "department",
    "skills",
    "job_url",
]

def main() -> None:
    parser = argparse.ArgumentParser(description="Export strictly filtered role analysis CSV.")
    parser.add_argument(
        "--input",
        default="backend/data/exports/external_job_postings.csv",
    )
    parser.add_argument(
        "--output",
        default="backend/data/exports/external_job_postings_role_analysis_v2.csv",
    )
    parser.add_argument(
        "--review-output",
        default="backend/data/exports/external_job_postings_role_analysis_v2_review_samples.csv",
    )
    parser.add_argument("--samples-per-role", type=int, default=10)
    parser.add_argument("--target-per-role", type=int, default=400)
    parser.add_argument("--max-per-company-per-role", type=int, default=15)
    args = parser.parse_args()

    raw_rows = read_csv(Path(args.input))
    analysis_rows = []
    for posting in raw_rows:
        role = classify_role(posting.get("title") or "")
        if role == "Other":
            continue

        clean_text = clean_description(posting.get("description") or "")
        sections = extract_sections(clean_text)
        skills = extract_skills(
            " ".join(
                [
                    posting.get("title") or "",
                    posting.get("department") or "",
                    clean_text,
                ]
            )
        )
        analysis_rows.append(
            {
                "id": posting.get("id"),
                "company": posting.get("company"),
                "title": posting.get("title"),
                "job_role_category": role,
                "location": posting.get("location"),
                "department": posting.get("department"),
                "skills": "; ".join(skills),
                "responsibilities": sections["responsibilities"],
                "requirements": sections["requirements"],
                "preferred_qualifications": sections["preferred_qualifications"],
                "job_url": posting.get("job_url"),
                "source": posting.get("source"),
                "collected_at": posting.get("collected_at"),
            }
        )

    selected_rows = select_balanced_rows(
        analysis_rows,
        target_per_role=args.target_per_role,
        max_per_company_per_role=args.max_per_company_per_role,
    )
    write_csv(Path(args.output), OUTPUT_FIELDS, selected_rows)
    review_rows = sample_by_role(selected_rows, args.samples_per_role)
    write_csv(Path(args.review_output), REVIEW_FIELDS, review_rows)
    available_counts = Counter(row["job_role_category"] for row in analysis_rows)
    selected_counts = Counter(row["job_role_category"] for row in selected_rows)
    selected_companies = {
        role: len({row["company"] for row in selected_rows if row["job_role_category"] == role})
        for role in TARGET_ROLES
    }
    print(
        {
            "input_rows": len(raw_rows),
            "eligible_rows": len(analysis_rows),
            "exported_rows": len(selected_rows),
            "excluded_rows": len(raw_rows) - len(analysis_rows),
            "target_per_role": args.target_per_role,
            "max_per_company_per_role": args.max_per_company_per_role,
            "available_role_counts": dict(available_counts),
            "selected_role_counts": dict(selected_counts),
            "selected_company_counts": selected_companies,
            "output": args.output,
            "review_output": args.review_output,
        }
    )


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def write_csv(path: Path, fields: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def sample_by_role(rows: list[dict], sample_count: int) -> list[dict]:
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["job_role_category"]].append(row)

    generator = random.Random(42)
    samples = []
    for role in [role for role, _ in ROLE_TITLE_RULES]:
        candidates = grouped.get(role, [])
        count = min(sample_count, len(candidates))
        samples.extend(generator.sample(candidates, count))
    return samples


def select_balanced_rows(
    rows: list[dict],
    target_per_role: int,
    max_per_company_per_role: int,
) -> list[dict]:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        grouped[row["job_role_category"]][row["company"]].append(row)

    selected = []
    for role in TARGET_ROLES:
        company_rows = grouped.get(role, {})
        for rows_for_company in company_rows.values():
            rows_for_company.sort(key=lambda row: (row.get("title") or "", row.get("id") or ""))

        role_selected = []
        for position in range(max_per_company_per_role):
            for company in sorted(company_rows):
                available = company_rows[company]
                if position < len(available):
                    role_selected.append(available[position])
                if len(role_selected) >= target_per_role:
                    break
            if len(role_selected) >= target_per_role:
                break
        selected.extend(role_selected)
    return selected


if __name__ == "__main__":
    main()
