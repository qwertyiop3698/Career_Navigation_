import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

ROOT_DIR = Path(__file__).resolve().parents[1]
import sys

sys.path.append(str(ROOT_DIR))

from app.db import SessionLocal
from app.models import Document, ExternalJobPosting, Skill, SkillTrend
from app.services.rag_service import RagService


def main() -> None:
    parser = argparse.ArgumentParser(description="Index existing DB records into RAG documents.")
    parser.add_argument("--jobs-limit", type=int, default=500)
    parser.add_argument("--trends", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = {
            "jobs": index_external_jobs(db, limit=args.jobs_limit),
            "trends": index_skill_trends(db) if args.trends else {"inserted": 0, "skipped": 0},
        }
        db.commit()
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def index_external_jobs(db: Session, limit: int) -> dict:
    rag_service = RagService()
    postings = (
        db.query(ExternalJobPosting)
        .order_by(ExternalJobPosting.collected_at.desc(), ExternalJobPosting.id.desc())
        .limit(limit)
        .all()
    )

    inserted = 0
    skipped = 0
    for posting in postings:
        stable_hash = _stable_hash(
            "external_job_posting",
            posting.id,
            posting.company,
            posting.title,
            posting.job_url,
        )
        if _document_exists(db, stable_hash):
            skipped += 1
            continue

        rag_service.create_document(
            db=db,
            content=_external_job_content(posting),
            source="external_job_posting",
            metadata={
                "stable_hash": stable_hash,
                "source_table": "external_job_postings",
                "external_job_posting_id": posting.id,
                "company": posting.company,
                "title": posting.title,
                "location": posting.location,
                "department": posting.department,
                "job_url": posting.job_url,
                "skills": posting.skills or [],
                "indexed_at": _utcnow_iso(),
            },
        )
        inserted += 1

    return {"inserted": inserted, "skipped": skipped, "seen": len(postings)}


def index_skill_trends(db: Session) -> dict:
    rag_service = RagService()
    trends = (
        db.query(SkillTrend, Skill)
        .join(Skill, Skill.id == SkillTrend.skill_id)
        .order_by(SkillTrend.global_score.desc().nullslast())
        .all()
    )

    inserted = 0
    skipped = 0
    for trend, skill in trends:
        stable_hash = _stable_hash(
            "skill_trend",
            skill.name,
            trend.global_score,
            trend.domestic_score,
            trend.growth_rate,
            trend.time_lag,
        )
        if _document_exists(db, stable_hash):
            skipped += 1
            continue

        rag_service.create_document(
            db=db,
            content=_skill_trend_content(skill, trend),
            source="skill_trend",
            metadata={
                "stable_hash": stable_hash,
                "source_table": "skill_trends",
                "skill": skill.name,
                "global_score": trend.global_score,
                "domestic_score": trend.domestic_score,
                "growth_rate": trend.growth_rate,
                "time_lag": trend.time_lag,
                "indexed_at": _utcnow_iso(),
            },
        )
        inserted += 1

    return {"inserted": inserted, "skipped": skipped, "seen": len(trends)}


def _external_job_content(posting: ExternalJobPosting) -> str:
    description = " ".join((posting.description or "").split())
    if len(description) > 1200:
        description = f"{description[:1200].rstrip()}..."

    fields = [
        ("Company", posting.company),
        ("Title", posting.title),
        ("Location", posting.location),
        ("Department", posting.department),
        ("Source", posting.source),
        ("Skills", ", ".join(posting.skills or [])),
        ("Job URL", posting.job_url),
        ("Description", description),
    ]
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


def _skill_trend_content(skill: Skill, trend: SkillTrend) -> str:
    return "\n".join(
        [
            f"Skill: {skill.name}",
            f"Global demand score: {trend.global_score}",
            f"Domestic demand score: {trend.domestic_score}",
            f"Estimated domestic time lag: {trend.time_lag} months",
            f"Growth rate: {trend.growth_rate}",
        ]
    )


def _document_exists(db: Session, stable_hash: str) -> bool:
    return (
        db.query(Document.id)
        .filter(Document.metadata_.contains({"stable_hash": stable_hash}))
        .first()
        is not None
    )


def _stable_hash(*parts) -> str:
    value = "|".join("" if part is None else str(part) for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
