import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db import get_db
from app.models import User
from app.schemas import ProjectSubmissionCreate, ProjectSubmissionResult
from app.services.project_evaluation_service import (
    create_strict_ai_review,
    serialize_submission,
    submit_project_for_evaluation,
)
from app.services.roadmap_service import get_active_roadmap, serialize_roadmap

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])
logger = logging.getLogger(__name__)


@router.post("/submissions", response_model=ProjectSubmissionResult)
def submit_project(
    payload: ProjectSubmissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id)
    if roadmap is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="활성 로드맵을 먼저 생성해주세요.",
        )
    try:
        submission = submit_project_for_evaluation(db, roadmap, payload)
        db.commit()
        updated_roadmap = get_active_roadmap(db, roadmap.user_id)
        return {
            "submission": serialize_submission(submission),
            "roadmap": serialize_roadmap(updated_roadmap),
        }
    except Exception:
        db.rollback()
        logger.exception("Failed to evaluate project submission. cycle=%s", payload.cycle_index)
        raise


@router.post("/submissions/{submission_id}/ai-review", response_model=ProjectSubmissionResult)
def review_project_with_ai(
    submission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    roadmap = get_active_roadmap(db, current_user.id)
    if roadmap is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="활성 로드맵이 없습니다.")
    submission = next(
        (item for item in roadmap.project_submissions if item.id == submission_id),
        None,
    )
    if submission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="제출물을 찾을 수 없습니다.")
    try:
        reviewed_submission = create_strict_ai_review(db, submission)
        db.commit()
        updated_roadmap = get_active_roadmap(db, roadmap.user_id)
        return {
            "submission": serialize_submission(reviewed_submission),
            "roadmap": serialize_roadmap(updated_roadmap),
        }
    except Exception:
        db.rollback()
        logger.exception("Failed to run strict AI review. submission_id=%s", submission_id)
        raise
