from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import JobPosting, JobSkill, Skill
from app.schemas import JobCreate, JobResponse

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])


@router.post(
    "",
    response_model=JobResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
):
    skill_names = _normalize_skill_names(payload.skills)
    if not skill_names:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid skill is required.",
        )

    job = JobPosting(
        company=payload.company,
        title=payload.title,
        description=payload.description,
        source=payload.source,
        created_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )

    try:
        db.add(job)
        db.flush()

        existing_skills = (
            db.query(Skill)
            .filter(Skill.name.in_(skill_names))
            .all()
        )
        skills_by_name = {skill.name: skill for skill in existing_skills}

        for skill_name in skill_names:
            skill = skills_by_name.get(skill_name)
            if skill is None:
                skill = Skill(name=skill_name)
                db.add(skill)
                db.flush()
                skills_by_name[skill_name] = skill

            db.add(JobSkill(job_id=job.id, skill_id=skill.id))

        db.commit()
        db.refresh(job)
    except Exception:
        db.rollback()
        raise

    return JobResponse(
        job_id=job.id,
        company=job.company,
        title=job.title,
        source=job.source,
        skills=skill_names,
        status="created",
    )


def _normalize_skill_names(skills: list[str]) -> list[str]:
    normalized = []
    seen = set()

    for skill in skills:
        skill_name = skill.strip()
        if not skill_name or skill_name in seen:
            continue
        normalized.append(skill_name)
        seen.add(skill_name)

    return normalized
