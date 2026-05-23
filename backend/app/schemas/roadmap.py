from pydantic import BaseModel, Field


class RoadmapCreateRequest(BaseModel):
    job_target: str = Field(..., examples=["AI Backend Developer"])
    experience_level: str = Field("Junior", examples=["Junior"])
    skills: list[str] = Field(default_factory=list, examples=[["Python", "SQL", "FastAPI"]])
    goal_period: int = Field(12, examples=[12])


class RoadmapTaskResponse(BaseModel):
    id: int
    task_title: str
    task_type: str
    is_completed: bool
    completed_at: str | None = None


class RoadmapWeekResponse(BaseModel):
    id: int
    week_number: int
    title: str
    goal: str | None = None
    tasks: list[RoadmapTaskResponse]


class RoadmapResponse(BaseModel):
    id: int
    user_id: str
    job_target: str
    experience_level: str | None = None
    goal_period: int | None = None
    progress_percent: int
    is_active: bool
    weeks: list[RoadmapWeekResponse]


class ActiveRoadmapResponse(BaseModel):
    roadmap: RoadmapResponse | None = None
    message: str | None = None


class ToggleTaskResponse(BaseModel):
    roadmap_id: int
    task_id: int
    is_completed: bool
    progress_percent: int
    completed_count: int
    total_count: int


class RoadmapProgressResponse(BaseModel):
    roadmap_id: int | None = None
    progress_percent: int
    completed_count: int
    total_count: int
    message: str | None = None
