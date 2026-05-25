from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import JobRoleSkillEvidence


ROLE_CYCLES = {
    "Backend Developer": [
        {
            "title": "서비스 API 기반 구축",
            "project": "인증과 데이터 저장이 포함된 REST API 구축",
            "skills": ["Java", "Python", "SQL", "Spring", "PostgreSQL"],
            "signal": "비즈니스 기능과 안정적인 데이터 처리를 함께 구현할 수 있습니다.",
        },
        {
            "title": "배포와 운영 확장",
            "project": "컨테이너 기반 API 배포와 운영 점검 추가",
            "skills": ["Docker", "AWS", "Kubernetes", "Redis", "Go"],
            "signal": "로컬 구현에서 끝나지 않고 서버를 전달하고 운영하는 흐름을 보여줍니다.",
        },
    ],
    "Frontend Developer": [
        {
            "title": "제품형 인터페이스 기반 구축",
            "project": "API 연동 반응형 데이터 대시보드 구축",
            "skills": ["React", "TypeScript", "JavaScript"],
            "signal": "사용자 흐름을 고려한 유지보수 가능한 화면 구현을 보여줍니다.",
        },
        {
            "title": "품질과 전달 가능성 확장",
            "project": "대시보드 품질 검증과 배포 흐름 확장",
            "skills": ["Node.js", "AWS", "Docker"],
            "signal": "화면 기능을 실제 전달 가능한 결과물로 완성하고 품질 판단을 설명합니다.",
        },
    ],
    "AI Backend Developer": [
        {
            "title": "AI 기능 API 기반 구축",
            "project": "출처를 표시하는 문서 질의응답 API 구축",
            "skills": ["Python", "LLM", "RAG", "FastAPI", "Embedding"],
            "signal": "AI 기능을 사용 가능한 서비스 API로 연결한 경험을 보여줍니다.",
        },
        {
            "title": "평가와 운영 확장",
            "project": "품질 평가, 사용 제한, 실행 환경을 갖춘 AI 기능 확장",
            "skills": ["Machine Learning", "Docker", "AWS", "PyTorch", "Vector DB"],
            "signal": "AI 제품에서 요구되는 품질과 운영 조건을 고려할 수 있음을 보여줍니다.",
        },
    ],
    "Data Analyst": [
        {
            "title": "의사결정형 분석 기반 구축",
            "project": "정제된 비즈니스 데이터 기반 분석 보고서 작성",
            "skills": ["SQL", "Python", "PostgreSQL"],
            "signal": "원천 데이터를 설명 가능한 비즈니스 결론으로 바꿀 수 있습니다.",
        },
        {
            "title": "분석 결과 전달 확장",
            "project": "반복 실행 가능한 KPI 대시보드와 제안서 작성",
            "skills": ["Machine Learning", "AWS"],
            "signal": "분석을 실행 가능한 제안으로 전달하는 역량을 보여줍니다.",
        },
    ],
    "Data Engineer": [
        {
            "title": "데이터 파이프라인 기반 구축",
            "project": "수집과 변환이 스케줄링된 데이터 파이프라인 구축",
            "skills": ["SQL", "Python", "Airflow"],
            "signal": "재현 가능한 데이터 흐름과 스케줄링 경험을 보여줍니다.",
        },
        {
            "title": "확장성과 신뢰성 강화",
            "project": "확장 처리와 데이터 품질 점검이 포함된 파이프라인 개선",
            "skills": ["Spark", "Kafka", "AWS", "Docker"],
            "signal": "운영 환경의 데이터 처리와 신뢰성을 고민한 경험을 보여줍니다.",
        },
    ],
    "Data Scientist": [
        {
            "title": "모델링 기반 구축",
            "project": "재현 가능한 예측 분석 프로젝트 구축",
            "skills": ["Python", "SQL", "Machine Learning"],
            "signal": "데이터 준비, 모델링, 평가를 연결할 수 있습니다.",
        },
        {
            "title": "고급 모델링과 전달 확장",
            "project": "모델을 개선하고 설명 가능한 결과물로 정리",
            "skills": ["PyTorch", "Deep Learning", "Spark", "AWS"],
            "signal": "개선 판단과 실제 활용 가능성을 함께 설명할 수 있습니다.",
        },
    ],
    "Builder": [
        {
            "title": "제품 구현 기반 구축",
            "project": "동작하는 제품 흐름 구현과 사용자 검증",
            "skills": ["Python", "JavaScript", "SQL", "React"],
            "signal": "문제를 실제 사용할 수 있는 제품 흐름으로 바꿀 수 있습니다.",
        },
        {
            "title": "출시와 피드백 확장",
            "project": "제품을 배포하고 사용자 피드백으로 개선",
            "skills": ["AWS", "Docker", "TypeScript"],
            "signal": "전달, 피드백 반영, 반복 개선 역량을 보여줍니다.",
        },
    ],
}

LEVEL_WEIGHTS = {
    0: 0.00,
    1: 0.10,
    2: 0.20,
    3: 0.35,
    4: 0.50,
    5: 0.60,
}


def build_evidence_roadmap_context(
    db: Session,
    job_role: str,
    skill_assessments: list[dict],
) -> dict:
    assessed_levels = {
        normalize_skill(assessment["name"]): max(0, min(5, int(assessment.get("level", 0))))
        for assessment in skill_assessments
        if assessment.get("name", "").strip()
    }
    evidence = (
        db.query(JobRoleSkillEvidence)
        .filter(JobRoleSkillEvidence.job_role_category == job_role)
        .order_by(
            JobRoleSkillEvidence.market_score.desc(),
            JobRoleSkillEvidence.evidence_company_count.desc(),
        )
        .all()
    )
    evidence_by_skill = {
        normalize_skill(row.skill): row
        for row in evidence
        if row.evidence_level in {"strong", "moderate"}
    }
    selected = set()
    cycles = []
    blueprint_skills = []

    for cycle_definition in ROLE_CYCLES.get(job_role, []):
        cycle_skills = [
            skill
            for skill in cycle_definition["skills"]
            if normalize_skill(skill) in evidence_by_skill
        ][:3]
        for skill in cycle_skills:
            if skill not in blueprint_skills:
                blueprint_skills.append(skill)
        focus_skills = []
        for skill in cycle_skills:
            key = normalize_skill(skill)
            if assessed_levels.get(key, 0) >= 5 or key in selected:
                continue
            if key not in evidence_by_skill:
                continue
            focus_skills.append(skill)
            selected.add(key)

        cycles.append(
            {
                "title": cycle_definition["title"],
                "project": cycle_definition["project"],
                "skills": focus_skills,
                "signal": cycle_definition["signal"],
            }
        )

    selected_skills = [skill for cycle in cycles for skill in cycle["skills"]]
    covered_skills = [
        skill for skill in blueprint_skills if assessed_levels.get(normalize_skill(skill), 0) > 0
    ]
    supported_market_total = sum(
        evidence_by_skill[normalize_skill(skill)].market_score for skill in blueprint_skills
    )
    capability_market_total = sum(
        evidence_by_skill[normalize_skill(skill)].market_score
        * LEVEL_WEIGHTS[assessed_levels.get(normalize_skill(skill), 0)]
        for skill in blueprint_skills
    )
    capability_score = (
        round(capability_market_total * 100 / supported_market_total)
        if supported_market_total
        else 0
    )
    evidence_summary = []
    for skill in selected_skills:
        row = evidence_by_skill.get(normalize_skill(skill))
        if row is None:
            continue
        evidence_summary.append(
            {
                "skill": row.skill,
                "market_score": row.market_score,
                "evidence_level": row.evidence_level,
                "keyword_posting_count": row.keyword_posting_count,
                "evidence_company_count": row.evidence_company_count,
                "role_posting_count": row.role_posting_count,
                "role_company_count": row.role_company_count,
                "current_level": assessed_levels.get(normalize_skill(skill), 0),
            }
        )

    return {
        "input_skills": [
            assessment["name"]
            for assessment in skill_assessments
            if int(assessment.get("level", 0)) > 0
        ],
        "skill_assessments": skill_assessments,
        "covered_skills": covered_skills,
        "missing_skills": selected_skills,
        "recommended_skills": selected_skills,
        "capability_score": capability_score,
        "readiness_score": capability_score,
        "cycles": cycles,
        "evidence_summary": evidence_summary,
        "evidence_note": (
            "현재 균형 표본 공고를 근거로 추천합니다. 본문에서 직접 추출한 스킬은 "
            "전부 반영하고, 모델 예측은 점수 0.55 이상만 근거 점수에 반영합니다."
            " 준비도는 근거가 확인된 직무 핵심 스킬 중 현재 보유한 스킬의 가중 비율입니다."
        ),
    }


def build_evidence_week_template(context: dict) -> list[dict]:
    cycles = context.get("cycles") or []
    weeks = []
    for cycle_index, cycle in enumerate(cycles):
        start_week = cycle_index * 6 + 1
        skill_text = ", ".join(cycle["skills"]) or "목표 직무 역량"
        previous_reuse = (
            ""
            if cycle_index == 0
            else " 첫 프로젝트의 역량도 다시 사용하며 결과물을 확장합니다."
        )
        plans = [
            (
                f"{cycle['title']}: 기획과 기초",
                f"{cycle['project']}의 범위를 정하고 {skill_text}을(를) 적용합니다.{previous_reuse}",
                [(f"프로젝트 범위 정의: {cycle['project']}", "project"), (f"필요 역량 실습: {skill_text}", "study")],
            ),
            (
                f"{cycle['title']}: 핵심 구현",
                "가장 작은 동작 흐름을 구현하고 기술 선택의 이유를 기록합니다.",
                [(f"핵심 흐름 구현: {skill_text}", "project"), ("README에 기술 선택 이유 기록", "portfolio")],
            ),
            (
                f"{cycle['title']}: 기능 연결",
                "각 기술을 따로 연습하는 대신 하나의 동작하는 결과물 안에서 연결합니다.",
                [(f"프로젝트에 역량 통합: {skill_text}", "project"), ("재현 가능한 실행 가이드 작성", "portfolio")],
            ),
            (
                f"{cycle['title']}: 품질 점검",
                "오류를 처리하고 결과물이 안정적으로 동작하는지 검증합니다.",
                [("검증, 실패 처리, 테스트 추가", "project"), ("테스트 결과와 한계 문서화", "portfolio")],
            ),
            (
                f"{cycle['title']}: 전달 준비",
                "다른 사람이 실행하고 평가할 수 있는 결과물로 정리합니다.",
                [("실행 가능한 빌드 패키징 또는 배포", "project"), ("실행 증거와 개선 내용 기록", "portfolio")],
            ),
            (
                f"{cycle['title']}: 채용 근거 정리",
                f"프로젝트가 다음 실무 신호를 어떻게 보여주는지 설명합니다: {cycle['signal']}",
                [("이력서용 프로젝트 근거 문장 작성", "resume"), ("프로젝트 설명 면접 답변 연습", "interview")],
            ),
        ]
        for offset, (title, goal, tasks) in enumerate(plans):
            weeks.append(
                {
                    "week_number": start_week + offset,
                    "title": title,
                    "goal": goal,
                    "tasks": [
                        {"task_title": task_title, "task_type": task_type}
                        for task_title, task_type in tasks
                    ],
                }
            )
    return weeks


def normalize_skill(skill: str) -> str:
    return skill.strip().lower()
