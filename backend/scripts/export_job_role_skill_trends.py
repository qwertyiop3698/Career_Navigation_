import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Export skill frequency trends by job role.")
    parser.add_argument(
        "--input",
        default="backend/data/exports/external_job_postings_role_analysis_ml_skills_v2.csv",
    )
    parser.add_argument(
        "--output",
        default="backend/data/exports/job_role_skill_trends_v2.csv",
    )
    args = parser.parse_args()

    rows = read_csv(Path(args.input))
    role_totals = Counter(row["job_role_category"] for row in rows)
    role_skill_counts = defaultdict(Counter)
    role_skill_keyword_counts = defaultdict(Counter)
    role_skill_model_counts = defaultdict(Counter)

    for row in rows:
        role = row["job_role_category"]
        method = row.get("skills_method") or ""
        for skill in parse_skills(row.get("final_skills")):
            role_skill_counts[role][skill] += 1
            if method == "keyword":
                role_skill_keyword_counts[role][skill] += 1
            elif method == "model":
                role_skill_model_counts[role][skill] += 1

    output_rows = []
    for role in sorted(role_skill_counts):
        total_posts = role_totals[role]
        for rank, (skill, postings_with_skill) in enumerate(
            role_skill_counts[role].most_common(),
            start=1,
        ):
            output_rows.append(
                {
                    "job_role_category": role,
                    "rank": rank,
                    "skill": skill,
                    "postings_with_skill": postings_with_skill,
                    "role_total_postings": total_posts,
                    "skill_share_percent": round(postings_with_skill * 100 / total_posts, 2),
                    "keyword_count": role_skill_keyword_counts[role][skill],
                    "model_count": role_skill_model_counts[role][skill],
                }
            )

    write_csv(Path(args.output), output_rows)
    print(
        {
            "input_rows": len(rows),
            "roles": len(role_totals),
            "trend_rows": len(output_rows),
            "top_skills": {
                role: role_skill_counts[role].most_common(5)
                for role in sorted(role_skill_counts)
            },
            "output": args.output,
        }
    )


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def parse_skills(value: str | None) -> list[str]:
    if not value:
        return []
    return [skill.strip() for skill in value.split(";") if skill.strip()]


def write_csv(path: Path, rows: list[dict]) -> None:
    fields = [
        "job_role_category",
        "rank",
        "skill",
        "postings_with_skill",
        "role_total_postings",
        "skill_share_percent",
        "keyword_count",
        "model_count",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
