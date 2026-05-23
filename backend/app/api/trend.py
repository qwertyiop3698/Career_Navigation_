from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Skill, SkillTrend
from app.schemas import (
    SkillTrendCreate,
    SkillTrendCreateResponse,
    SkillTrendResponse,
)

router = APIRouter(prefix="/api/v1/trends", tags=["trends"])


@router.post(
    "",
    response_model=SkillTrendCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_skill_trend(
    payload: SkillTrendCreate,
    db: Session = Depends(get_db),
):
    skill_name = payload.skill_name.strip()
    if not skill_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="skill_name is required.",
        )

    try:
        skill = db.query(Skill).filter(Skill.name == skill_name).first()
        if skill is None:
            skill = Skill(name=skill_name)
            db.add(skill)
            db.flush()

        trend = SkillTrend(
            skill_id=skill.id,
            global_score=payload.global_score,
            domestic_score=payload.domestic_score,
            time_lag=payload.time_lag,
            growth_rate=payload.growth_rate,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        db.add(trend)
        db.commit()
        db.refresh(trend)
    except Exception:
        db.rollback()
        raise

    return SkillTrendCreateResponse(
        skill_name=skill.name,
        global_score=trend.global_score,
        domestic_score=trend.domestic_score,
        time_lag=trend.time_lag,
        growth_rate=trend.growth_rate,
        status="created",
    )


@router.get("/keywords", response_model=list[SkillTrendResponse])
def get_trend_keywords(db: Session = Depends(get_db)):
    trends = (
        db.query(SkillTrend)
        .join(Skill)
        .order_by(SkillTrend.updated_at.desc().nullslast(), SkillTrend.id.desc())
        .all()
    )

    return [
        SkillTrendResponse(
            skill_name=trend.skill.name,
            global_score=trend.global_score,
            domestic_score=trend.domestic_score,
            time_lag=trend.time_lag,
            growth_rate=trend.growth_rate,
        )
        for trend in trends
    ]
