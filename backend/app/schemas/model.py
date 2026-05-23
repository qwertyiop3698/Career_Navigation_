from uuid import UUID

from pydantic import BaseModel, Field


class ModelPredictRequest(BaseModel):
    user_id: UUID | None = Field(None, examples=["6f4f312e-6d74-4e03-aecd-29e8ee4d6832"])
    job_role: str = Field(..., examples=["Backend Developer"])
    global_score: float = Field(..., examples=[86.0])
    domestic_score: float = Field(..., examples=[79.5])
    growth_rate: float = Field(..., examples=[11.2])
    time_lag: int = Field(..., examples=[3])


class ModelPredictResponse(BaseModel):
    probability: float
    diffusion_time: float
    impact: str
    model_type: str
