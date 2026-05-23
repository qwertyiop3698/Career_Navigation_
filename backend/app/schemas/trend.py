from pydantic import BaseModel, Field


class SkillTrendCreate(BaseModel):
    skill_name: str = Field(..., examples=["Python"])
    global_score: float = Field(..., examples=[92.5])
    domestic_score: float = Field(..., examples=[88.0])
    time_lag: int = Field(..., examples=[2])
    growth_rate: float = Field(..., examples=[13.4])


class SkillTrendResponse(BaseModel):
    skill_name: str
    global_score: float
    domestic_score: float
    time_lag: int
    growth_rate: float


class SkillTrendCreateResponse(SkillTrendResponse):
    status: str
