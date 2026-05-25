import argparse
import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT_DIR))

from app.db import Base, SessionLocal, engine
from app.models import JobRoleSkillEvidence


KEYWORD_WEIGHT = 1.0
HIGH_CONFIDENCE_WEIGHT = 0.7
MEDIUM_CONFIDENCE_WEIGHT = 0.4


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild current role/skill market evidence.")
    parser.add_argument(
        "--input",
        default="data/exports/external_job_postings_role_analysis_ml_skills_v2.csv",
    )
    args = parser.parse_args()

    rows = read_csv(Path(args.input))
    evidence_rows = build_evidence_rows(rows)

    Base.metadata.create_all(bind=engine, tables=[JobRoleSkillEvidence.__table__])
    db = SessionLocal()
    try:
        db.query(JobRoleSkillEvidence).delete()
        db.add_all(JobRoleSkillEvidence(**row) for row in evidence_rows)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

    top_skills = defaultdict(list)
    for row in evidence_rows:
        if len(top_skills[row["job_role_category"]]) < 5:
            top_skills[row["job_role_category"]].append(
                (row["skill"], row["market_score"], row["evidence_level"])
            )
    print(
        {
            "input_rows": len(rows),
            "evidence_rows": len(evidence_rows),
            "top_skills": dict(top_skills),
        }
    )


def build_evidence_rows(rows: list[dict]) -> list[dict]:
    role_rows = defaultdict(list)
    for row in rows:
        role_rows[row["job_role_category"]].append(row)

    results = []
    calculated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    for role, postings in role_rows.items():
        role_company_count = len({row["company"] for row in postings})
        per_skill = defaultdict(new_skill_stats)

        for posting in postings:
            method = posting.get("skills_method") or ""
            company = posting.get("company") or ""
            scores = parse_prediction_scores(posting.get("predicted_skill_scores"))
            for skill in parse_skills(posting.get("final_skills")):
                stats = per_skill[skill]
                if method == "keyword":
                    stats["keyword_posting_count"] += 1
                    stats["weighted_posting_score"] += KEYWORD_WEIGHT
                    stats["evidence_companies"].add(company)
                elif method == "model":
                    stats["model_posting_count"] += 1
                    weight = model_weight(scores.get(skill, 0))
                    if weight == 0:
                        stats["low_confidence_model_count"] += 1
                    else:
                        stats["weighted_posting_score"] += weight
                        stats["evidence_companies"].add(company)

        for skill, stats in per_skill.items():
            weighted_count = stats["weighted_posting_score"]
            company_count = len(stats["evidence_companies"])
            demand_share = weighted_count / len(postings) if postings else 0
            company_coverage = company_count / role_company_count if role_company_count else 0
            market_score = 100 * (0.7 * demand_share + 0.3 * company_coverage)
            results.append(
                {
                    "job_role_category": role,
                    "skill": skill,
                    "role_posting_count": len(postings),
                    "role_company_count": role_company_count,
                    "keyword_posting_count": stats["keyword_posting_count"],
                    "model_posting_count": stats["model_posting_count"],
                    "low_confidence_model_count": stats["low_confidence_model_count"],
                    "evidence_company_count": company_count,
                    "weighted_posting_score": round(weighted_count, 2),
                    "demand_share": round(demand_share, 4),
                    "company_coverage": round(company_coverage, 4),
                    "market_score": round(market_score, 2),
                    "evidence_level": evidence_level(
                        role_posting_count=len(postings),
                        keyword_count=stats["keyword_posting_count"],
                        company_count=company_count,
                        market_score=market_score,
                    ),
                    "evidence_basis": (
                        "Current balanced postings: keyword=1.0, "
                        "model>=0.65=0.7, model>=0.55=0.4, model<0.55=excluded"
                    ),
                    "calculated_at": calculated_at,
                }
            )

    return sorted(
        results,
        key=lambda row: (
            row["job_role_category"],
            -row["market_score"],
            -row["evidence_company_count"],
            row["skill"],
        ),
    )


def new_skill_stats() -> dict:
    return {
        "keyword_posting_count": 0,
        "model_posting_count": 0,
        "low_confidence_model_count": 0,
        "weighted_posting_score": 0.0,
        "evidence_companies": set(),
    }


def evidence_level(
    role_posting_count: int,
    keyword_count: int,
    company_count: int,
    market_score: float,
) -> str:
    if role_posting_count >= 100 and keyword_count >= 5 and company_count >= 5 and market_score >= 5:
        return "strong"
    if keyword_count >= 2 and company_count >= 3 and market_score >= 2:
        return "moderate"
    return "limited"


def model_weight(score: float) -> float:
    if score >= 0.65:
        return HIGH_CONFIDENCE_WEIGHT
    if score >= 0.55:
        return MEDIUM_CONFIDENCE_WEIGHT
    return 0.0


def parse_skills(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(";") if part.strip()]


def parse_prediction_scores(value: str | None) -> dict[str, float]:
    if not value:
        return {}
    scores = {}
    for skill, score in re.findall(r"([^;:]+):([0-9.]+)", value):
        scores[skill.strip()] = float(score)
    return scores


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as csv_file:
        return list(csv.DictReader(csv_file))


if __name__ == "__main__":
    main()
