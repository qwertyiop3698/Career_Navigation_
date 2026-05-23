import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_optional_current_user
from app.db import get_db
from app.models import User
from app.schemas import (
    ActiveRoadmapResponse,
    RoadmapCreateRequest,
    RoadmapProgressResponse,
    RoadmapResponse,
    ToggleTaskResponse,
)
from app.services.roadmap_service import (
    create_active_roadmap,
    get_active_roadmap,
    get_progress,
    serialize_roadmap,
    toggle_task,
)

router = APIRouter(prefix="/api/v1/roadmaps", tags=["roadmaps"])
logger = logging.getLogger(__name__)


@router.post("", response_model=RoadmapResponse)
def create_roadmap(
    payload: RoadmapCreateRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        roadmap = create_active_roadmap(
            db=db,
            user_id=current_user.id if current_user is not None else None,
            job_target=payload.job_target,
            experience_level=payload.experience_level,
            skills=payload.skills,
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
    current_user: User | None = Depends(get_optional_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id if current_user is not None else None)
    if roadmap is None:
        return {"roadmap": None, "message": "No active roadmap found."}
    return {"roadmap": serialize_roadmap(roadmap), "message": None}


@router.patch("/tasks/{task_id}/toggle", response_model=ToggleTaskResponse)
def toggle_roadmap_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    try:
        task, roadmap, completed_count, total_count = toggle_task(
            db,
            task_id,
            current_user.id if current_user is not None else None,
        )
        db.commit()
        return {
            "roadmap_id": roadmap.id,
            "task_id": task.id,
            "is_completed": task.is_completed,
            "progress_percent": roadmap.progress_percent,
            "completed_count": completed_count,
            "total_count": total_count,
        }
    except Exception:
        db.rollback()
        logger.exception("Failed to toggle roadmap task. task_id=%s", task_id)
        raise


@router.get("/me/progress", response_model=RoadmapProgressResponse)
def get_my_roadmap_progress(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id if current_user is not None else None)
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
