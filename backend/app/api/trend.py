from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import JobRoleMarketHistory, JobRoleSkillEvidence, Skill, SkillTrend
from app.schemas import (
    JobRoleMarketHistoryResponse,
    JobRoleSkillEvidenceResponse,
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


@router.get("/role-skills", response_model=list[JobRoleSkillEvidenceResponse])
def get_job_role_skill_evidence(
    job_role_category: str = Query(...),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    evidence_rows = (
        db.query(JobRoleSkillEvidence)
        .filter(JobRoleSkillEvidence.job_role_category == job_role_category)
        .order_by(
            JobRoleSkillEvidence.market_score.desc(),
            JobRoleSkillEvidence.evidence_company_count.desc(),
            JobRoleSkillEvidence.skill.asc(),
        )
        .limit(limit)
        .all()
    )
    return [
        JobRoleSkillEvidenceResponse(
            job_role_category=row.job_role_category,
            skill=row.skill,
            role_posting_count=row.role_posting_count,
            role_company_count=row.role_company_count,
            keyword_posting_count=row.keyword_posting_count,
            model_posting_count=row.model_posting_count,
            low_confidence_model_count=row.low_confidence_model_count,
            evidence_company_count=row.evidence_company_count,
            weighted_posting_score=row.weighted_posting_score,
            demand_share=row.demand_share,
            company_coverage=row.company_coverage,
            market_score=row.market_score,
            evidence_level=row.evidence_level,
            evidence_basis=row.evidence_basis,
        )
        for row in evidence_rows
    ]


@router.get("/role-history", response_model=list[JobRoleMarketHistoryResponse])
def get_job_role_market_history(
    job_role_category: str = Query(...),
    metric: str = Query(default="average_salary"),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(JobRoleMarketHistory)
        .filter(
            JobRoleMarketHistory.job_role_category == job_role_category,
            JobRoleMarketHistory.metric == metric,
        )
        .order_by(JobRoleMarketHistory.period_month.asc())
        .all()
    )
    return [
        JobRoleMarketHistoryResponse(
            source=row.source,
            country=row.country,
            job_role_category=row.job_role_category,
            query_term=row.query_term,
            metric=row.metric,
            period_month=row.period_month.isoformat(),
            value=row.value,
            granularity=row.granularity,
            limitation_note=row.limitation_note,
        )
        for row in rows
    ]
