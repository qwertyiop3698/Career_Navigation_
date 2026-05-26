from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Roadmap, RoadmapTask
from app.services.roadmap_service import recalculate_progress

OFFICIAL_SCHEDULE_URL = "https://www.dataq.or.kr/www/accept/schedule.do"
TARGET_ROLE = "Data Scientist"
PREP_WEEKS = 4

CERTIFICATION_SCHEDULES = {
    "ADsP": [
        {
            "round": "제50회",
            "name": "ADsP (데이터분석 준전문가)",
            "registration_start": date(2026, 7, 6),
            "registration_end": date(2026, 7, 10),
            "exam_date": date(2026, 8, 8),
            "result_date": date(2026, 8, 28),
            "fit_reason": "통계, 분석 방법론, 데이터 분석 기초를 정리하는 선택형 준비 항목입니다.",
        },
        {
            "round": "제51회",
            "name": "ADsP (데이터분석 준전문가)",
            "registration_start": date(2026, 9, 28),
            "registration_end": date(2026, 10, 2),
            "exam_date": date(2026, 10, 31),
            "result_date": date(2026, 11, 20),
            "fit_reason": "통계, 분석 방법론, 데이터 분석 기초를 정리하는 선택형 준비 항목입니다.",
        },
    ],
    "SQLD": [
        {
            "round": "제62회",
            "name": "SQLD (SQL 개발자)",
            "registration_start": date(2026, 7, 20),
            "registration_end": date(2026, 7, 24),
            "exam_date": date(2026, 8, 22),
            "result_date": date(2026, 9, 11),
            "fit_reason": "데이터 추출과 SQL 활용 역량을 보완하는 선택형 준비 항목입니다.",
        },
        {
            "round": "제63회",
            "name": "SQLD (SQL 개발자)",
            "registration_start": date(2026, 10, 12),
            "registration_end": date(2026, 10, 16),
            "exam_date": date(2026, 11, 14),
            "result_date": date(2026, 12, 4),
            "fit_reason": "데이터 추출과 SQL 활용 역량을 보완하는 선택형 준비 항목입니다.",
        },
    ],
}

PREPARATION_TASKS = {
    "ADsP": [
        "ADsP 범위 확인 및 데이터 분석 개념 정리",
        "ADsP 통계 및 분석 방법론 핵심 학습",
        "ADsP 기출문제 풀이 및 취약 영역 확인",
        "ADsP 모의시험 및 오답 정리",
    ],
    "SQLD": [
        "SQLD 범위 확인 및 데이터 모델링 개념 정리",
        "SQLD SQL 기본 및 활용 문제 학습",
        "SQLD 기출문제 풀이 및 취약 영역 확인",
        "SQLD 모의시험 및 오답 정리",
    ],
}


def get_certification_options(roadmap: Roadmap | None, job_target: str) -> list[dict]:
    if job_target != TARGET_ROLE:
        return []

    today = datetime.now(ZoneInfo("Asia/Seoul")).date()
    selected = set((roadmap.content or {}).get("selected_certifications", [])) if roadmap else set()
    options = []
    for code, schedules in CERTIFICATION_SCHEDULES.items():
        schedule = next(
            (
                candidate
                for candidate in schedules
                if candidate["exam_date"] - timedelta(weeks=PREP_WEEKS) >= today
            ),
            None,
        )
        if schedule is None:
            continue
        options.append(_serialize_option(code, schedule, code in selected))
    return options


def include_certification_plan(db: Session, roadmap: Roadmap, code: str) -> Roadmap:
    if roadmap.job_target != TARGET_ROLE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Certification BETA is available only for Data Scientist roadmaps.",
        )

    normalized_code = code.strip()
    options = {
        option["code"]: option
        for option in get_certification_options(roadmap, roadmap.job_target)
    }
    option = options.get(normalized_code)
    if option is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No available certification schedule was found.",
        )
    if option["is_selected"]:
        return roadmap

    start_date = _roadmap_start_date(roadmap)
    prep_start = date.fromisoformat(option["recommended_start_date"])
    starting_week = max(1, ((prep_start - start_date).days // 7) + 1)
    if starting_week > len(roadmap.weeks):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The recommended preparation period is outside this 12-week roadmap.",
        )

    for index, title in enumerate(PREPARATION_TASKS[normalized_code]):
        week_number = min(starting_week + index, len(roadmap.weeks))
        week = next(week for week in roadmap.weeks if week.week_number == week_number)
        week.tasks.append(
            RoadmapTask(
                task_title=f"[{normalized_code} BETA] {title}",
                task_type="certificate",
            )
        )

    content = dict(roadmap.content or {})
    content["selected_certifications"] = [
        *content.get("selected_certifications", []),
        normalized_code,
    ]
    roadmap.content = content
    recalculate_progress(db, roadmap)
    db.flush()
    return roadmap


def _serialize_option(code: str, schedule: dict, is_selected: bool) -> dict:
    prep_start = schedule["exam_date"] - timedelta(weeks=PREP_WEEKS)
    return {
        "code": code,
        "name": schedule["name"],
        "round": schedule["round"],
        "provider": "한국데이터산업진흥원",
        "registration_start": schedule["registration_start"].isoformat(),
        "registration_end": schedule["registration_end"].isoformat(),
        "exam_date": schedule["exam_date"].isoformat(),
        "result_date": schedule["result_date"].isoformat(),
        "recommended_prep_weeks": PREP_WEEKS,
        "recommended_start_date": prep_start.isoformat(),
        "fit_reason": schedule["fit_reason"],
        "official_url": OFFICIAL_SCHEDULE_URL,
        "is_selected": is_selected,
        "score_policy": "BETA 기간에는 지원 준비 점수에 반영하지 않습니다.",
    }


def _roadmap_start_date(roadmap: Roadmap) -> date:
    if roadmap.created_at is not None:
        return roadmap.created_at.date()
    return datetime.now(ZoneInfo("Asia/Seoul")).date()
