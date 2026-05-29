from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from app.services.external_jobs.skill_extractor import extract_skills  # noqa: E402
from export_role_analysis_csv import clean_description, extract_sections  # noqa: E402


BATCH_ID = "evidence_boost_20260529_01"
DEFAULT_DIR = ROOT_DIR / "data" / "exports" / "additional_batches"
DEFAULT_RAW = DEFAULT_DIR / f"external_job_postings_additional_raw_{BATCH_ID}.csv"
DEFAULT_COMBINED = DEFAULT_DIR / f"external_job_postings_role_candidates_combined_{BATCH_ID}.csv"
DEFAULT_OUTPUT = DEFAULT_DIR / f"external_job_postings_role_candidates_combined_{BATCH_ID}_parserfix_v2.csv"
PARSER_VERSION = "role_evidence_parser_v2"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rebuild additional batch candidate sections from existing raw CSV only."
    )
    parser.add_argument("--batch-id", default=BATCH_ID)
    parser.add_argument("--raw-input", type=Path, default=DEFAULT_RAW)
    parser.add_argument("--combined-input", type=Path, default=DEFAULT_COMBINED)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    raw_rows, _ = read_csv(args.raw_input)
    combined_rows, fields = read_csv(args.combined_input)
    raw_by_id = {
        f"{value(row, 'source')}:{value(row, 'external_id')}": row
        for row in raw_rows
        if value(row, "source") and value(row, "external_id")
    }

    rebuilt = []
    updated = 0
    fallback_ready = 0
    for row in combined_rows:
        output = dict(row)
        raw = raw_by_id.get(value(row, "id"))
        if raw and value(row, "batch_id") == args.batch_id:
            normalized = clean_description(value(raw, "description"))
            sections = extract_sections(normalized)
            output["responsibilities"] = sections["responsibilities"]
            output["requirements"] = sections["requirements"]
            output["preferred_qualifications"] = sections["preferred_qualifications"]
            output["normalized_raw_body"] = normalized
            output["normalized_raw_body_length"] = str(len(normalized))
            section_length = sum(len(value(output, field)) for field in ["responsibilities", "requirements", "preferred_qualifications"])
            output["section_extraction_status"] = "fallback_used" if section_length < 200 and len(normalized) >= 500 else "success"
            output["parser_version"] = PARSER_VERSION
            skills = extract_skills(" ".join([value(raw, "title"), value(raw, "department"), normalized]))
            output["skills"] = "; ".join(skills)
            output["final_skills"] = "; ".join(skills)
            output["skills_method"] = "keyword"
            updated += 1
            if output["section_extraction_status"] == "fallback_used":
                fallback_ready += 1
        else:
            output.setdefault("normalized_raw_body", "")
            output.setdefault("normalized_raw_body_length", "")
            output.setdefault("section_extraction_status", value(output, "section_extraction_status") or "")
            output.setdefault("parser_version", value(output, "parser_version") or "")
        rebuilt.append(output)

    output_fields = extend_fields(
        fields,
        [
            "normalized_raw_body",
            "normalized_raw_body_length",
            "section_extraction_status",
            "parser_version",
        ],
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_csv(args.output, output_fields, rebuilt)
    print(
        json.dumps(
            {
                "batch_id": args.batch_id,
                "input_rows": len(combined_rows),
                "raw_rows": len(raw_rows),
                "updated_batch_candidate_rows": updated,
                "fallback_flagged_rows": fallback_ready,
                "output": str(args.output),
                "network_requests": False,
                "database_writes": False,
                "openai_calls": False,
                "embedding_requests": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def read_csv(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        return list(reader), list(reader.fieldnames or [])


def write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def extend_fields(fields: list[str], additions: list[str]) -> list[str]:
    output = list(fields)
    for field in additions:
        if field not in output:
            output.append(field)
    return output


def value(row: dict[str, str], field: str) -> str:
    return (row.get(field) or "").strip()


if __name__ == "__main__":
    raise SystemExit(main())
