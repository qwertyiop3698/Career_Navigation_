from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db import get_db
from app.models import Prediction, User
from app.schemas import ModelPredictRequest, ModelPredictResponse
from app.services.ml_service import RandomForestPredictionService

router = APIRouter(prefix="/api/v1/model", tags=["model"])
prediction_service = RandomForestPredictionService()


@router.post(
    "/predict",
    response_model=ModelPredictResponse,
    status_code=status.HTTP_201_CREATED,
)
def predict_job_impact(
    payload: ModelPredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = prediction_service.predict(
        global_score=payload.global_score,
        domestic_score=payload.domestic_score,
        growth_rate=payload.growth_rate,
        time_lag=payload.time_lag,
    )

    prediction = Prediction(
        user_id=current_user.id,
        job_role=payload.job_role,
        probability=result.probability,
        diffusion_time=result.diffusion_time,
    )
    try:
        db.add(prediction)
        db.commit()
    except Exception:
        db.rollback()
        raise

    return ModelPredictResponse(
        probability=result.probability,
        diffusion_time=result.diffusion_time,
        impact=result.impact,
        model_type=result.model_type,
    )
