from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, selectinload

from app.models import (
    ProjectSubmission,
    Roadmap,
    RoadmapReassessment,
    RoadmapTask,
    RoadmapWeek,
)
from app.services.evidence_roadmap_service import (
    build_evidence_roadmap_context,
    build_evidence_week_template,
)

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
    user_id,
    job_target: str,
    interest_domain: str = "커머스",
    experience_level: str = "Junior",
    skills: list[str] | None = None,
    skill_assessments: list[dict] | None = None,
    goal_period: int = 12,
) -> Roadmap:
    owner_id = user_id
    normalized_job = normalize_job_target(job_target)

    db.query(Roadmap).filter(
        Roadmap.user_id == owner_id,
        Roadmap.is_active.is_(True),
    ).update({Roadmap.is_active: False}, synchronize_session=False)

    normalized_assessments = skill_assessments or [
        {"name": skill, "level": 3} for skill in (skills or [])
    ]
    roadmap_context = build_evidence_roadmap_context(
        db, normalized_job, normalized_assessments, interest_domain
    )
    roadmap = Roadmap(
        user_id=owner_id,
        job_target=normalized_job,
        experience_level=experience_level,
        goal_period=goal_period,
        progress_percent=0,
        is_active=True,
        content=roadmap_context,
    )
    db.add(roadmap)
    db.flush()

    week_templates = build_evidence_week_template(roadmap_context)
    if not week_templates:
        week_templates = build_roadmap_template(normalized_job, skills or [])
    for week_template in week_templates:
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


def get_active_roadmap(db: Session, user_id) -> Roadmap | None:
    owner_id = user_id
    return (
        db.query(Roadmap)
        .options(
            selectinload(Roadmap.weeks).selectinload(RoadmapWeek.tasks),
            selectinload(Roadmap.reassessments),
            selectinload(Roadmap.project_submissions).selectinload(ProjectSubmission.evaluation),
        )
        .filter(Roadmap.user_id == owner_id, Roadmap.is_active.is_(True))
        .first()
    )


def toggle_task(
    db: Session,
    task_id: int,
    user_id,
) -> tuple[RoadmapTask, Roadmap, int, int]:
    query = (
        db.query(RoadmapTask)
        .join(RoadmapWeek)
        .join(Roadmap)
        .filter(RoadmapTask.id == task_id)
    )
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
    context = roadmap.content or {}
    scores = calculate_readiness_scores(roadmap)
    return {
        "id": roadmap.id,
        "user_id": str(roadmap.user_id),
        "job_target": roadmap.job_target,
        "interest_domain": context.get("interest_domain", "커머스"),
        "experience_level": roadmap.experience_level,
        "goal_period": roadmap.goal_period,
        "progress_percent": roadmap.progress_percent,
        "is_active": roadmap.is_active,
        "current_skills": context.get("input_skills", []),
        "skill_assessments": context.get("skill_assessments", []),
        "covered_skills": context.get("covered_skills", []),
        "missing_skills": context.get("missing_skills", []),
        "recommended_skills": context.get("recommended_skills", []),
        **scores,
        "cycles": context.get("cycles", []),
        "project_blueprints": context.get("project_blueprints", []),
        "evidence_summary": context.get("evidence_summary", []),
        "skill_diagnostics": context.get("skill_diagnostics", []),
        "reassessments": [
            {
                "checkpoint_week": reassessment.checkpoint_week,
                "capability_score_before": reassessment.capability_score_before,
                "capability_score_after": reassessment.capability_score_after,
                "skill_assessments": reassessment.updated_assessments,
                "created_at": reassessment.created_at.isoformat()
                if reassessment.created_at
                else None,
            }
            for reassessment in roadmap.reassessments
        ],
        "project_submissions": [
            {
                "id": submission.id,
                "cycle_index": submission.cycle_index,
                "project_title": submission.project_title,
                "github_url": submission.github_url,
                "submitted_at": submission.submitted_at.isoformat()
                if submission.submitted_at
                else None,
                "evaluation": {
                    "id": submission.evaluation.id,
                    "rule_score": submission.evaluation.rule_score,
                    "project_evidence_points": submission.evaluation.project_evidence_points,
                    "status": submission.evaluation.status,
                    "score_breakdown": submission.evaluation.score_breakdown or {},
                    "passed_checks": submission.evaluation.passed_checks or [],
                    "missing_checks": submission.evaluation.missing_checks or [],
                    "critical_issues": submission.evaluation.critical_issues or [],
                    "ai_review": submission.evaluation.ai_review,
                    "ai_model": submission.evaluation.ai_model,
                    "ai_estimated_cost_usd": submission.evaluation.ai_estimated_cost_usd,
                },
            }
            for submission in roadmap.project_submissions
            if submission.evaluation is not None
        ],
        "evidence_note": context.get("evidence_note"),
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


def submit_reassessment(
    db: Session,
    roadmap: Roadmap,
    checkpoint_week: int,
    skill_assessments: list[dict],
) -> Roadmap:
    if checkpoint_week not in {6, 12}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="재진단은 6주차 또는 12주차에 저장할 수 있습니다.",
        )
    if any(item.checkpoint_week == checkpoint_week for item in roadmap.reassessments):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="해당 시점의 재진단이 이미 저장되어 있습니다.",
        )

    previous_context = dict(roadmap.content or {})
    updated_context = build_evidence_roadmap_context(
        db,
        roadmap.job_target,
        skill_assessments,
        previous_context.get("interest_domain", "커머스"),
    )
    if previous_context.get("selected_certifications"):
        updated_context["selected_certifications"] = previous_context["selected_certifications"]

    roadmap.reassessments.append(
        RoadmapReassessment(
            user_id=roadmap.user_id,
            checkpoint_week=checkpoint_week,
            previous_assessments=previous_context.get("skill_assessments", []),
            updated_assessments=skill_assessments,
            previous_diagnostics=previous_context.get("skill_diagnostics", []),
            updated_diagnostics=updated_context.get("skill_diagnostics", []),
            capability_score_before=int(previous_context.get("capability_score", 0)),
            capability_score_after=int(updated_context.get("capability_score", 0)),
        )
    )
    roadmap.content = updated_context

    if checkpoint_week == 6:
        _replace_future_learning_plan(db, roadmap, updated_context, checkpoint_week)

    recalculate_progress(db, roadmap)
    db.flush()
    return get_active_roadmap(db, roadmap.user_id)


def _replace_future_learning_plan(
    db: Session,
    roadmap: Roadmap,
    updated_context: dict,
    checkpoint_week: int,
) -> None:
    future_weeks = [week for week in roadmap.weeks if week.week_number > checkpoint_week]
    regular_tasks = [
        task
        for week in future_weeks
        for task in week.tasks
        if task.task_type != "certificate"
    ]
    if any(task.is_completed for task in regular_tasks):
        return

    templates = {
        template["week_number"]: template
        for template in build_evidence_week_template(updated_context)
        if template["week_number"] > checkpoint_week
    }
    for week in future_weeks:
        template = templates.get(week.week_number)
        if template is None:
            continue
        week.title = template["title"]
        week.goal = template["goal"]
        for task in list(week.tasks):
            if task.task_type == "certificate":
                continue
            week.tasks.remove(task)
            db.delete(task)
        for task in template["tasks"]:
            week.tasks.append(
                RoadmapTask(
                    task_title=task["task_title"],
                    task_type=task["task_type"],
                )
            )


def calculate_readiness_scores(roadmap: Roadmap) -> dict:
    context = roadmap.content or {}
    capability_score = min(60, max(0, int(context.get("capability_score", 0))))
    tasks = [task for week in roadmap.weeks for task in week.tasks]
    application_tasks = [
        task for task in tasks
        if task.task_type in {"resume", "interview", "job_search"}
    ]
    project_evidence_score = min(
        25,
        sum(
            submission.evaluation.project_evidence_points
            for submission in roadmap.project_submissions
            if submission.evaluation is not None
        ),
    )
    application_readiness_score = _completion_score(application_tasks, 15)
    return {
        "readiness_score": (
            capability_score + project_evidence_score + application_readiness_score
        ),
        "capability_score": capability_score,
        "project_evidence_score": project_evidence_score,
        "application_readiness_score": application_readiness_score,
    }


def _completion_score(tasks: list[RoadmapTask], maximum: int) -> int:
    if not tasks:
        return 0
    completed = sum(1 for task in tasks if task.is_completed)
    return round(completed / len(tasks) * maximum)


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
