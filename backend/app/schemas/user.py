from pydantic import BaseModel, Field


class UserProfileCreate(BaseModel):
    job_target: str = Field(..., examples=["Backend Developer"])
    experience_level: str = Field(..., examples=["Junior"])
    skills: list[str] = Field(..., examples=[["Python", "FastAPI", "SQLAlchemy"]])
    goal_period: int = Field(..., examples=[6])


class UserProfileResponse(BaseModel):
    user_id: str
    job_target: str
    experience_level: str
    skills: list[str]
    goal_period: int
    status: str
