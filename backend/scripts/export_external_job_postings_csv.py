import argparse
import csv
import json
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.db import SessionLocal
from app.models import ExternalJobPosting


FIELDS = [
    "id",
    "company",
    "title",
    "location",
    "department",
    "description",
    "job_url",
    "source",
    "external_id",
    "skills",
    "raw_json",
    "collected_at",
    "created_at",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Export external job postings from DB to CSV.")
    parser.add_argument(
        "--output",
        default="data/exports/external_job_postings.csv",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    db = SessionLocal()
    try:
        postings = (
            db.query(ExternalJobPosting)
            .order_by(ExternalJobPosting.id.asc())
            .yield_per(500)
        )
        count = 0
        with output_path.open("w", encoding="utf-8-sig", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
            writer.writeheader()
            for posting in postings:
                writer.writerow(
                    {
                        "id": posting.id,
                        "company": posting.company,
                        "title": posting.title,
                        "location": posting.location,
                        "department": posting.department,
                        "description": posting.description,
                        "job_url": posting.job_url,
                        "source": posting.source,
                        "external_id": posting.external_id,
                        "skills": json.dumps(posting.skills or [], ensure_ascii=False),
                        "raw_json": json.dumps(posting.raw_json or {}, ensure_ascii=False),
                        "collected_at": posting.collected_at,
                        "created_at": posting.created_at,
                    }
                )
                count += 1
    finally:
        db.close()

    print({"rows": count, "output": str(output_path)})


if __name__ == "__main__":
    main()
