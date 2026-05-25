import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_optional_current_user
from app.db import get_db
from app.models import Skill, User, UserSkill
from app.schemas import SkillAssessment, UserProfileCreate, UserProfileResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])
logger = logging.getLogger(__name__)


@router.post(
    "/profile",
    response_model=UserProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_profile(
    payload: UserProfileCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    assessments = _normalize_skill_assessments(payload)
    if not assessments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one valid skill assessment is required.",
        )
    skill_names = [assessment.name for assessment in assessments]

    user = current_user or User()
    user.job_target = payload.job_target
    user.experience_level = payload.experience_level
    user.goal_period = payload.goal_period

    try:
        if current_user is None:
            db.add(user)
        db.flush()
        db.query(UserSkill).filter(UserSkill.user_id == user.id).delete()

        existing_skills = (
            db.query(Skill)
            .filter(Skill.name.in_(skill_names))
            .all()
        )
        skills_by_name = {skill.name: skill for skill in existing_skills}

        for assessment in assessments:
            skill_name = assessment.name
            skill = skills_by_name.get(skill_name)
            if skill is None:
                skill = Skill(name=skill_name)
                db.add(skill)
                db.flush()
                skills_by_name[skill_name] = skill

            db.add(
                UserSkill(
                    user_id=user.id,
                    skill_id=skill.id,
                    proficiency_level=assessment.level,
                )
            )

        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to create user profile. payload=%s normalized_skills=%s",
            _payload_to_dict(payload),
            skill_names,
        )
        raise

    return UserProfileResponse(
        user_id=str(user.id),
        job_target=user.job_target,
        experience_level=user.experience_level,
        skills=[assessment.name for assessment in assessments if assessment.level > 0],
        skill_assessments=assessments,
        goal_period=user.goal_period,
        status="created",
    )


def _normalize_skill_assessments(payload: UserProfileCreate) -> list[SkillAssessment]:
    submitted = payload.skill_assessments or [
        SkillAssessment(name=skill, level=3) for skill in payload.skills
    ]
    normalized: list[SkillAssessment] = []
    seen = set()

    for assessment in submitted:
        skill_name = assessment.name.strip()
        key = skill_name.lower()
        if not skill_name or key in seen:
            continue
        normalized.append(SkillAssessment(name=skill_name, level=assessment.level))
        seen.add(key)

    return normalized


def _payload_to_dict(payload: UserProfileCreate) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()
