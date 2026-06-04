from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.security import require_admin_or_internal_api_key
from app.db import get_db
from app.models import ExternalJobPosting, User
from app.services.external_jobs.persistence import collect_external_jobs_to_db
from app.services.external_jobs.skill_extractor import TECH_KEYWORDS

router = APIRouter(prefix="/api/v1/external-jobs", tags=["External Jobs"])
admin_router = APIRouter(prefix="/api/v1/admin/external-jobs", tags=["Admin External Jobs"])


@admin_router.post("/collect")
@router.post("/collect")
def collect_external_jobs(
    db: Session = Depends(get_db),
    _: User | None = Depends(require_admin_or_internal_api_key),
):
    return collect_external_jobs_to_db(db)


@router.get("")
def list_external_jobs(
    company: str | None = Query(default=None),
    source: str | None = Query(default=None),
    skill: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(ExternalJobPosting)

    if company:
        query = query.filter(ExternalJobPosting.company.ilike(f"%{company}%"))
    if source:
        query = query.filter(func.lower(ExternalJobPosting.source) == source.lower())
    if skill:
        query = query.filter(ExternalJobPosting.skills.contains([_canonical_skill(skill)]))

    postings = (
        query.order_by(ExternalJobPosting.collected_at.desc())
        .limit(limit)
        .all()
    )

    return [_to_public_response(posting) for posting in postings]


@router.get("/skills/summary")
def get_external_job_skill_summary(db: Session = Depends(get_db)):
    postings = db.query(ExternalJobPosting.skills).all()
    counter = Counter()

    for (skills,) in postings:
        if isinstance(skills, list):
            counter.update(skill for skill in skills if skill)

    return [
        {"skill": skill, "count": count}
        for skill, count in counter.most_common()
    ]


def _to_public_response(posting: ExternalJobPosting) -> dict:
    return {
        "id": posting.id,
        "company": posting.company,
        "title": posting.title,
        "location": posting.location,
        "department": posting.department,
        "job_url": posting.job_url,
        "source": posting.source,
        "skills": posting.skills or [],
        "summary": _summarize(posting.description),
        "collected_at": posting.collected_at,
    }


def _summarize(description: str | None, max_length: int = 280) -> str:
    if not description:
        return ""
    text = " ".join(description.split())
    if len(text) <= max_length:
        return text
    return f"{text[:max_length].rstrip()}..."


def _canonical_skill(skill: str) -> str:
    normalized = skill.strip().lower()
    for keyword in TECH_KEYWORDS:
        if keyword.lower() == normalized:
            return keyword
    return skill.strip()
