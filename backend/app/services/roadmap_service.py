import uuid
from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models import Roadmap, RoadmapTask, RoadmapWeek, User

DEMO_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
DEMO_EMAIL = "demo@career.local"

SUPPORTED_JOB_TARGETS = [
    "Backend Developer",
    "Frontend Developer",
    "AI Backend Developer",
    "Data Analyst",
    "Data Engineer",
    "Data Scientist",
    "Builder",
]

JOB_ALIASES = {
    "백엔드 개발자": "Backend Developer",
    "프론트엔드 개발자": "Frontend Developer",
    "AI 백엔드 개발자": "AI Backend Developer",
    "ai 백엔드 개발자": "AI Backend Developer",
    "데이터 분석가": "Data Analyst",
    "데이터 엔지니어": "Data Engineer",
    "데이터 사이언티스트": "Data Scientist",
    "빌더": "Builder",
    "서비스 빌더": "Builder",
    "AI 빌더": "Builder",
    "ai 빌더": "Builder",
    "노코드 빌더": "Builder",
    "MVP 빌더": "Builder",
    "mvp 빌더": "Builder",
}

JOB_KEYWORDS = [
    ("Builder", ["builder", "no-code", "nocode", "low-code", "lowcode", "mvp", "빌더", "노코드"]),
    ("AI Backend Developer", ["ai", "llm", "rag"]),
    ("Frontend Developer", ["front", "react", "ui", "프론트"]),
    ("Data Engineer", ["engineer", "etl", "pipeline", "엔지니어"]),
    ("Data Scientist", ["scientist", "machine", "ml", "사이언티스트"]),
    ("Data Analyst", ["analyst", "analysis", "분석"]),
    ("Backend Developer", ["backend", "api", "server", "백엔드"]),
]

COMMON_TASKS = [
    ("이력서 작성", "resume"),
    ("포트폴리오 정리", "portfolio"),
    ("GitHub 정리", "portfolio"),
    ("SQLD 자격증 준비", "certificate"),
    ("통계학 기초 학습", "study"),
    ("SQL 문제 풀이", "study"),
    ("직무 프로젝트 1개 완성", "project"),
    ("기술면접 준비", "interview"),
    ("모의면접", "interview"),
    ("채용공고 분석", "job_search"),
    ("지원 기업 리스트 작성", "job_search"),
    ("자기소개서 작성", "resume"),
]

JOB_SKILLS = {
    "Backend Developer": [
        "Java 또는 Python",
        "REST API",
        "SQL",
        "Docker",
        "Database 설계",
        "배포 기초",
        "테스트 코드",
        "포트폴리오 API 서버",
    ],
    "Frontend Developer": [
        "JavaScript",
        "React",
        "API 연동",
        "상태관리",
        "반응형 UI",
        "컴포넌트 설계",
        "포트폴리오 배포",
        "사용자 경험 개선",
    ],
    "AI Backend Developer": [
        "Python",
        "FastAPI",
        "SQL",
        "Docker",
        "PostgreSQL",
        "LLM API",
        "RAG 기초",
        "pgvector",
        "API 프로젝트",
    ],
    "Data Analyst": [
        "SQL",
        "Python",
        "Pandas",
        "통계학",
        "데이터 시각화",
        "SQLD",
        "분석 포트폴리오",
        "대시보드 기초",
    ],
    "Data Engineer": [
        "SQL",
        "Python",
        "ETL",
        "Airflow 기초",
        "데이터 파이프라인",
        "Docker",
        "PostgreSQL",
        "데이터 적재/정제",
    ],
    "Data Scientist": [
        "Python",
        "SQL",
        "통계학",
        "머신러닝",
        "Scikit-learn",
        "Pandas",
        "데이터 시각화",
        "모델 평가",
        "분석 포트폴리오",
        "Kaggle 또는 공공데이터 프로젝트",
    ],
    "Builder": [
        "서비스 기획",
        "문제 정의",
        "사용자 시나리오 작성",
        "Figma 또는 화면 설계",
        "노코드 로우코드 도구",
        "API 기초",
        "JavaScript 기초",
        "AI 도구 활용",
        "자동화 도구",
        "데이터 수집 기초",
        "랜딩페이지 제작",
        "MVP 제작",
        "사용자 테스트",
        "피드백 반영",
        "포트폴리오 정리",
        "이력서 작성",
        "자기소개서 작성",
        "면접 준비",
    ],
}


def get_demo_user(db: Session) -> User:
    user = db.query(User).filter(User.id == DEMO_USER_ID).first()
    if user:
        return user

    user = User(
        id=DEMO_USER_ID,
        email=DEMO_EMAIL,
        nickname="데모 사용자",
    )
    db.add(user)
    db.flush()
    return user


def get_current_user_id(db: Session) -> uuid.UUID:
    return get_demo_user(db).id


def normalize_job_target(job_target: str) -> str:
    value = (job_target or "").strip()
    if value in SUPPORTED_JOB_TARGETS:
        return value
    if value in JOB_ALIASES:
        return JOB_ALIASES[value]

    lowered = value.lower()
    for mapped, keywords in JOB_KEYWORDS:
        if any(keyword.lower() in lowered for keyword in keywords):
            return mapped

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"지원하는 IT 직무는 다음과 같습니다: {', '.join(SUPPORTED_JOB_TARGETS)}",
    )


def create_active_roadmap(
    db: Session,
    job_target: str,
    experience_level: str = "Junior",
    skills: list[str] | None = None,
    goal_period: int = 12,
    user_id: uuid.UUID | None = None,
) -> Roadmap:
    owner_id = user_id or get_current_user_id(db)
    normalized_job = normalize_job_target(job_target)

    db.query(Roadmap).filter(
        Roadmap.user_id == owner_id,
        Roadmap.is_active.is_(True),
    ).update({Roadmap.is_active: False}, synchronize_session=False)

    roadmap = Roadmap(
        user_id=owner_id,
        job_target=normalized_job,
        experience_level=experience_level,
        goal_period=goal_period,
        progress_percent=0,
        is_active=True,
        content={"input_skills": skills or []},
    )
    db.add(roadmap)
    db.flush()

    for week_template in build_roadmap_template(normalized_job, skills or []):
        week = RoadmapWeek(
            roadmap_id=roadmap.id,
            week_number=week_template["week_number"],
            title=week_template["title"],
            goal=week_template["goal"],
        )
        db.add(week)
        db.flush()
        for task in week_template["tasks"]:
            db.add(
                RoadmapTask(
                    week_id=week.id,
                    task_title=task["task_title"],
                    task_type=task["task_type"],
                )
            )

    recalculate_progress(db, roadmap)
    return get_active_roadmap(db, owner_id)


def get_active_roadmap(db: Session, user_id: uuid.UUID | None = None) -> Roadmap | None:
    owner_id = user_id or get_current_user_id(db)
    return (
        db.query(Roadmap)
        .options(selectinload(Roadmap.weeks).selectinload(RoadmapWeek.tasks))
        .filter(Roadmap.user_id == owner_id, Roadmap.is_active.is_(True))
        .first()
    )


def toggle_task(
    db: Session,
    task_id: int,
    user_id: uuid.UUID | None = None,
) -> tuple[RoadmapTask, Roadmap, int, int]:
    query = (
        db.query(RoadmapTask)
        .join(RoadmapWeek)
        .join(Roadmap)
        .filter(RoadmapTask.id == task_id)
    )
    if user_id is not None:
        query = query.filter(Roadmap.user_id == user_id)
    task = query.first()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="할 일을 찾을 수 없습니다.")

    task.is_completed = not task.is_completed
    task.completed_at = datetime.utcnow() if task.is_completed else None
    roadmap = task.week.roadmap
    completed_count, total_count = recalculate_progress(db, roadmap)
    db.flush()
    return task, roadmap, completed_count, total_count


def recalculate_progress(db: Session, roadmap: Roadmap) -> tuple[int, int]:
    tasks = (
        db.query(RoadmapTask)
        .join(RoadmapWeek)
        .filter(RoadmapWeek.roadmap_id == roadmap.id)
        .all()
    )
    total_count = len(tasks)
    completed_count = sum(1 for task in tasks if task.is_completed)
    roadmap.progress_percent = (
        round(completed_count / total_count * 100) if total_count else 0
    )
    return completed_count, total_count


def get_progress(db: Session, roadmap: Roadmap | None) -> tuple[int, int, int]:
    if roadmap is None:
        return 0, 0, 0
    completed_count, total_count = recalculate_progress(db, roadmap)
    return roadmap.progress_percent, completed_count, total_count


def serialize_roadmap(roadmap: Roadmap) -> dict:
    return {
        "id": roadmap.id,
        "user_id": str(roadmap.user_id),
        "job_target": roadmap.job_target,
        "experience_level": roadmap.experience_level,
        "goal_period": roadmap.goal_period,
        "progress_percent": roadmap.progress_percent,
        "is_active": roadmap.is_active,
        "weeks": [
            {
                "id": week.id,
                "week_number": week.week_number,
                "title": week.title,
                "goal": week.goal,
                "tasks": [
                    {
                        "id": task.id,
                        "task_title": task.task_title,
                        "task_type": task.task_type,
                        "is_completed": task.is_completed,
                        "completed_at": task.completed_at.isoformat()
                        if task.completed_at
                        else None,
                    }
                    for task in week.tasks
                ],
            }
            for week in roadmap.weeks
        ],
    }


def build_roadmap_template(job_target: str, input_skills: list[str]) -> list[dict]:
    if job_target == "Builder":
        return build_builder_roadmap_template()

    job_skills = JOB_SKILLS[job_target]
    skill_tasks = [(f"{skill} 학습 및 실습", "study") for skill in job_skills]
    all_tasks = skill_tasks + COMMON_TASKS

    weeks = []
    for index in range(12):
        week_number = index + 1
        selected = [
            all_tasks[(index * 2) % len(all_tasks)],
            all_tasks[(index * 2 + 1) % len(all_tasks)],
        ]
        if index in (3, 7, 10):
            selected.append(("직무 프로젝트 1개 완성", "project"))
        if index >= 8:
            selected.append(("기술면접 준비", "interview"))

        weeks.append(
            {
                "week_number": week_number,
                "title": _week_title(week_number, job_target),
                "goal": _week_goal(week_number, job_target, input_skills),
                "tasks": [
                    {"task_title": title, "task_type": task_type}
                    for title, task_type in _unique_tasks(selected)
                ],
            }
        )
    return weeks


def build_builder_roadmap_template() -> list[dict]:
    return [
        _builder_week(1, "문제 정의와 서비스 아이디어 구체화", "해결할 문제와 MVP로 검증할 가설을 명확히 정리합니다.", [
            ("문제 정의 작성", "study"),
            ("서비스 기획 초안 작성", "project"),
            ("채용공고 분석", "job_search"),
        ]),
        _builder_week(2, "사용자 시나리오와 화면 설계", "핵심 사용자의 흐름과 필요한 화면을 정리합니다.", [
            ("사용자 시나리오 작성", "project"),
            ("핵심 화면 목록 작성", "project"),
            ("포트폴리오 정리 기준 세우기", "portfolio"),
        ]),
        _builder_week(3, "Figma 또는 간단한 UI 프로토타입 제작", "아이디어를 눈으로 확인할 수 있는 화면으로 만듭니다.", [
            ("Figma 또는 화면 설계", "project"),
            ("랜딩페이지 와이어프레임 제작", "project"),
            ("GitHub 정리", "portfolio"),
        ]),
        _builder_week(4, "노코드 로우코드 도구 익히기", "빠르게 MVP를 만들 수 있는 제작 도구를 선택하고 익힙니다.", [
            ("노코드 로우코드 도구 실습", "study"),
            ("간단한 CRUD 화면 만들기", "project"),
            ("SQLD 자격증 준비", "certificate"),
        ]),
        _builder_week(5, "API 기초와 외부 데이터 연동 이해", "서비스가 외부 데이터와 연결되는 방식을 이해합니다.", [
            ("API 기초 학습", "study"),
            ("외부 데이터 연동 실습", "project"),
            ("JavaScript 기초 학습", "study"),
        ]),
        _builder_week(6, "AI 도구를 활용한 기능 설계", "AI 도구를 활용해 MVP의 핵심 기능을 설계합니다.", [
            ("AI 도구 활용 범위 정리", "study"),
            ("AI 기능 요구사항 작성", "project"),
            ("통계학 기초 학습", "study"),
        ]),
        _builder_week(7, "자동화 도구로 업무 흐름 만들기", "반복 작업을 자동화하고 서비스 운영 흐름을 만듭니다.", [
            ("자동화 도구 실습", "study"),
            ("데이터 수집 기초 실습", "project"),
            ("SQL 문제 풀이", "study"),
        ]),
        _builder_week(8, "MVP 핵심 기능 구현", "작게 동작하는 MVP 핵심 기능을 완성합니다.", [
            ("MVP 제작", "project"),
            ("핵심 기능 테스트", "project"),
            ("직무 프로젝트 1개 완성", "project"),
        ]),
        _builder_week(9, "랜딩페이지 또는 소개 페이지 제작", "사용자가 서비스를 이해할 수 있는 소개 화면을 만듭니다.", [
            ("랜딩페이지 제작", "project"),
            ("서비스 소개 문구 작성", "portfolio"),
            ("포트폴리오 정리", "portfolio"),
        ]),
        _builder_week(10, "사용자 테스트와 피드백 반영", "실제 피드백으로 MVP를 개선합니다.", [
            ("사용자 테스트 진행", "project"),
            ("피드백 반영", "project"),
            ("모의면접", "interview"),
        ]),
        _builder_week(11, "포트폴리오와 GitHub 문서 정리", "Builder 역량을 보여줄 산출물과 문서를 정리합니다.", [
            ("포트폴리오 정리", "portfolio"),
            ("GitHub 정리", "portfolio"),
            ("MVP 제작 과정 문서화", "portfolio"),
        ]),
        _builder_week(12, "이력서, 자기소개서, 면접 준비", "지원 문서와 면접 답변을 Builder 직무에 맞게 완성합니다.", [
            ("이력서 작성", "resume"),
            ("자기소개서 작성", "resume"),
            ("면접 준비", "interview"),
        ]),
    ]


def _builder_week(week_number: int, title: str, goal: str, tasks: list[tuple[str, str]]) -> dict:
    return {
        "week_number": week_number,
        "title": title,
        "goal": goal,
        "tasks": [
            {"task_title": task_title, "task_type": task_type}
            for task_title, task_type in tasks
        ],
    }


def _week_title(week_number: int, job_target: str) -> str:
    if week_number <= 3:
        return f"{job_target} 기초 역량 만들기"
    if week_number <= 6:
        return "직무 기술 실습과 포트폴리오 초안"
    if week_number <= 9:
        return "프로젝트 완성도 높이기"
    return "지원 준비와 면접 대비"


def _week_goal(week_number: int, job_target: str, input_skills: list[str]) -> str:
    skills_text = ", ".join(input_skills[:3]) if input_skills else job_target
    if week_number <= 3:
        return f"{skills_text} 기반의 핵심 개념을 정리합니다."
    if week_number <= 6:
        return "작게 동작하는 결과물을 만들고 기록합니다."
    if week_number <= 9:
        return "대표 프로젝트 1개를 완성하고 GitHub를 정리합니다."
    return "채용공고, 이력서, 자기소개서, 면접 답변을 연결합니다."


def _unique_tasks(tasks: list[tuple[str, str]]) -> list[tuple[str, str]]:
    unique = []
    seen = set()
    for title, task_type in tasks:
        if title not in seen:
            unique.append((title, task_type))
            seen.add(title)
    return unique
