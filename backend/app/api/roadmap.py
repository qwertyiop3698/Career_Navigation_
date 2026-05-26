import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import (
    ActiveRoadmapResponse,
    CertificationBetaOptionResponse,
    RoadmapCreateRequest,
    RoadmapProgressResponse,
    RoadmapReassessmentRequest,
    RoadmapResponse,
    ToggleTaskResponse,
)
from app.services.certification_beta_service import (
    get_certification_options,
    include_certification_plan,
)
from app.services.roadmap_service import (
    create_active_roadmap,
    get_active_roadmap,
    get_progress,
    serialize_roadmap,
    submit_reassessment,
    toggle_task,
)

router = APIRouter(prefix="/api/v1/roadmaps", tags=["roadmaps"])
logger = logging.getLogger(__name__)


@router.post("", response_model=RoadmapResponse)
def create_roadmap(
    payload: RoadmapCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        roadmap = create_active_roadmap(
            db=db,
            user_id=current_user.id,
            job_target=payload.job_target,
            interest_domain=payload.interest_domain,
            experience_level=payload.experience_level,
            skills=payload.skills,
            skill_assessments=[
                {"name": assessment.name, "level": assessment.level}
                for assessment in payload.skill_assessments
            ],
            goal_period=payload.goal_period,
        )
        db.commit()
        return serialize_roadmap(roadmap)
    except Exception:
        db.rollback()
        logger.exception("Failed to create roadmap. payload=%s", _payload_to_dict(payload))
        raise


@router.get("/me", response_model=ActiveRoadmapResponse)
def get_my_roadmap(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id)
    if roadmap is None:
        return {"roadmap": None, "message": "No active roadmap found."}
    return {"roadmap": serialize_roadmap(roadmap), "message": None}


@router.get("/certifications/beta", response_model=list[CertificationBetaOptionResponse])
def get_certification_beta_options(
    job_target: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id)
    return get_certification_options(roadmap, job_target)


@router.post("/me/certifications/{code}/include", response_model=RoadmapResponse)
def include_certification_in_roadmap(
    code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id)
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active roadmap found.",
        )
    try:
        updated_roadmap = include_certification_plan(db, roadmap, code)
        db.commit()
        return serialize_roadmap(updated_roadmap)
    except Exception:
        db.rollback()
        logger.exception("Failed to include certification plan. code=%s", code)
        raise


@router.post("/me/reassessments", response_model=RoadmapResponse)
def create_roadmap_reassessment(
    payload: RoadmapReassessmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id)
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active roadmap found.",
        )
    try:
        updated_roadmap = submit_reassessment(
            db=db,
            roadmap=roadmap,
            checkpoint_week=payload.checkpoint_week,
            skill_assessments=[
                {"name": assessment.name, "level": assessment.level}
                for assessment in payload.skill_assessments
            ],
        )
        db.commit()
        return serialize_roadmap(updated_roadmap)
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to create roadmap reassessment. checkpoint_week=%s",
            payload.checkpoint_week,
        )
        raise


@router.patch("/tasks/{task_id}/toggle", response_model=ToggleTaskResponse)
def toggle_roadmap_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        task, roadmap, completed_count, total_count = toggle_task(
            db,
            task_id,
            current_user.id,
        )
        db.commit()
        scores = serialize_roadmap(roadmap)
        return {
            "roadmap_id": roadmap.id,
            "task_id": task.id,
            "is_completed": task.is_completed,
            "progress_percent": roadmap.progress_percent,
            "completed_count": completed_count,
            "total_count": total_count,
            "readiness_score": scores["readiness_score"],
            "capability_score": scores["capability_score"],
            "project_evidence_score": scores["project_evidence_score"],
            "application_readiness_score": scores["application_readiness_score"],
        }
    except Exception:
        db.rollback()
        logger.exception("Failed to toggle roadmap task. task_id=%s", task_id)
        raise


@router.get("/me/progress", response_model=RoadmapProgressResponse)
def get_my_roadmap_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id)
    progress_percent, completed_count, total_count = get_progress(db, roadmap)
    if roadmap is None:
        return {
            "roadmap_id": None,
            "progress_percent": 0,
            "completed_count": 0,
            "total_count": 0,
            "message": "No active roadmap found.",
        }
    return {
        "roadmap_id": roadmap.id,
        "progress_percent": progress_percent,
        "completed_count": completed_count,
        "total_count": total_count,
        "message": None,
    }


def _payload_to_dict(payload: RoadmapCreateRequest) -> dict:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    return payload.dict()
