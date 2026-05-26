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

LEVEL_LABELS = {
    0: "경험 없음",
    1: "기본 사용",
    2: "작은 문제 해결",
    3: "프로젝트 적용",
    4: "품질까지 적용",
    5: "배포/설명 가능",
}

DOMAIN_PROFILES = {
    "금융": {
        "entity": "대출 신청자",
        "classification_problem": "연체 위험 예측",
        "regression_problem": "신용 위험 비용 예측",
        "data": "신청자 소득, 부채, 상환 이력, 상품 조건 데이터",
        "decision": "심사 기준과 리스크 관리 우선순위",
    },
    "커머스": {
        "entity": "고객",
        "classification_problem": "재구매 이탈 위험 예측",
        "regression_problem": "향후 구매 금액 예측",
        "data": "주문, 방문, 장바구니, 프로모션 반응 데이터",
        "decision": "리텐션 캠페인 대상과 운영 전략",
    },
    "헬스케어": {
        "entity": "환자",
        "classification_problem": "재입원 위험 예측",
        "regression_problem": "예상 재원 일수 예측",
        "data": "진료 이력, 검사 결과, 처방, 입퇴원 기록 데이터",
        "decision": "고위험군 사전 관리와 자원 배분",
    },
    "교육": {
        "entity": "학습자",
        "classification_problem": "중도 이탈 위험 예측",
        "regression_problem": "최종 성취도 예측",
        "data": "학습 진도, 퀴즈 결과, 접속 패턴, 과제 제출 데이터",
        "decision": "개입 대상 선정과 맞춤 학습 지원",
    },
    "콘텐츠": {
        "entity": "사용자",
        "classification_problem": "구독 해지 위험 예측",
        "regression_problem": "콘텐츠 시청 시간 예측",
        "data": "재생, 검색, 좋아요, 구독 전환 데이터",
        "decision": "추천 편성 및 이탈 방지 전략",
    },
    "스포츠": {
        "entity": "선수",
        "classification_problem": "부상 위험 구간 예측",
        "regression_problem": "다음 경기 성과 지표 예측",
        "data": "경기 기록, 출전 시간, 훈련 부하, 상대팀 기록 데이터",
        "decision": "출전 운영과 훈련 계획 조정",
    },
    "채용/HR": {
        "entity": "지원자",
        "classification_problem": "채용 전형 통과 가능성 분석",
        "regression_problem": "포지션별 요구 역량 점수 예측",
        "data": "공고 기술, 지원 이력, 직무 분류, 전형 결과 데이터",
        "decision": "직무 매칭과 역량 보완 우선순위",
    },
}


def build_evidence_roadmap_context(
    db: Session,
    job_role: str,
    skill_assessments: list[dict],
    interest_domain: str = "커머스",
) -> dict:
    normalized_domain = interest_domain.strip() or "커머스"
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
    skill_diagnostics = _build_skill_diagnostics(
        blueprint_skills,
        cycles,
        evidence_by_skill,
        assessed_levels,
    )
    project_blueprints = _build_project_blueprints(
        job_role,
        normalized_domain,
        cycles,
        skill_diagnostics,
    )
    for cycle, blueprint in zip(cycles, project_blueprints):
        cycle["project"] = blueprint["title"]
        cycle["blueprint"] = blueprint
    for diagnostic in skill_diagnostics:
        project = next(
            (
                blueprint["title"]
                for blueprint in project_blueprints
                if diagnostic["skill"] in blueprint["core_skills"]
            ),
            None,
        )
        if project is not None:
            diagnostic["project_application"] = project
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
        "interest_domain": normalized_domain,
        "covered_skills": covered_skills,
        "missing_skills": selected_skills,
        "recommended_skills": selected_skills,
        "capability_score": capability_score,
        "readiness_score": capability_score,
        "cycles": cycles,
        "project_blueprints": project_blueprints,
        "evidence_summary": evidence_summary,
        "skill_diagnostics": skill_diagnostics,
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
        skill_text = ", ".join(cycle["skills"]) or "보유 역량의 품질과 설명 근거"
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


def _build_skill_diagnostics(
    blueprint_skills: list[str],
    cycles: list[dict],
    evidence_by_skill: dict,
    assessed_levels: dict[str, int],
) -> list[dict]:
    project_by_skill = {
        normalize_skill(skill): cycle["project"]
        for cycle in cycles
        for skill in cycle["skills"]
    }
    diagnostics = []
    for skill in blueprint_skills:
        key = normalize_skill(skill)
        row = evidence_by_skill[key]
        level = assessed_levels.get(key, 0)
        gap_priority = round(row.market_score * (5 - level) / 5, 2)
        diagnostics.append(
            {
                "skill": skill,
                "current_level": level,
                "level_label": LEVEL_LABELS[level],
                "status": _skill_status(level),
                "gap_priority": gap_priority,
                "market_score": row.market_score,
                "evidence_level": row.evidence_level,
                "keyword_posting_count": row.keyword_posting_count,
                "evidence_company_count": row.evidence_company_count,
                "evidence_reason": (
                    f"{row.evidence_company_count}개 회사의 공고에서 "
                    f"{row.keyword_posting_count}건 직접 확인된 기술입니다."
                ),
                "recommended_action": _recommended_action(skill, level),
                "project_application": project_by_skill.get(key),
            }
        )
    return sorted(
        diagnostics,
        key=lambda item: (-item["gap_priority"], -item["market_score"], item["skill"]),
    )


def _skill_status(level: int) -> str:
    if level >= 5:
        return "강점 유지"
    if level >= 3:
        return "증명 강화"
    return "우선 보완"


def _recommended_action(skill: str, level: int) -> str:
    if level == 0:
        return f"{skill} 기본 개념과 작은 실습부터 시작해 프로젝트에 연결합니다."
    if level <= 2:
        return f"{skill}을(를) 단독 실습에서 끝내지 않고 프로젝트 기능 하나에 적용합니다."
    if level <= 4:
        return f"{skill} 적용 결과에 검증, 실패 처리, 선택 이유 기록을 추가합니다."
    return f"{skill} 활용 결과와 설계 판단을 이력서와 면접 답변으로 정리합니다."


def _build_project_blueprints(
    job_role: str,
    interest_domain: str,
    cycles: list[dict],
    diagnostics: list[dict],
) -> list[dict]:
    profile = DOMAIN_PROFILES.get(interest_domain) or {
        "entity": "대상 사용자 또는 객체",
        "classification_problem": f"{interest_domain} 위험 또는 행동 유형 예측",
        "regression_problem": f"{interest_domain} 핵심 성과 지표 예측",
        "data": f"{interest_domain} 공개 데이터 또는 직접 수집한 행동·성과 데이터",
        "decision": f"{interest_domain} 분야의 실행 의사결정",
    }
    ranked_skills = [item["skill"] for item in diagnostics]
    return [
        _project_blueprint(job_role, interest_domain, profile, cycle, index, ranked_skills)
        for index, cycle in enumerate(cycles)
    ]


def _project_blueprint(
    job_role: str,
    domain: str,
    profile: dict,
    cycle: dict,
    index: int,
    ranked_skills: list[str],
) -> dict:
    skills = cycle["skills"] or ranked_skills[:3]
    if job_role == "Data Scientist":
        return _data_scientist_blueprint(domain, profile, index, skills)
    if job_role == "Data Analyst":
        title = (
            "SQL 기반 핵심 지표 분석과 의사결정 대시보드"
            if index == 0
            else "반복 분석 자동화와 실행 제안 리포트"
        )
        techniques = ["SQL 데이터 마트 구성", "Python 탐색 분석", "코호트/KPI 비교 분석"]
        evaluation = ["지표 정의의 타당성", "반복 실행 가능한 SQL", "의사결정 제안의 근거"]
    elif job_role == "Data Engineer":
        title = (
            "스케줄링 기반 배치 데이터 파이프라인 구축"
            if index == 0
            else "대용량 처리와 데이터 품질 모니터링 파이프라인"
        )
        techniques = ["Airflow 배치 오케스트레이션", "Spark 변환 처리", "데이터 품질 테스트 및 실패 알림"]
        evaluation = ["재처리 가능성", "품질 오류 탐지", "처리량 및 실패 복구 기록"]
    elif job_role == "AI Backend Developer":
        title = (
            "출처 기반 RAG 질의응답 API 구현"
            if index == 0
            else "AI 응답 평가와 운영 안정성 강화"
        )
        techniques = ["RAG 검색 흐름", "Embedding 기반 근거 검색", "FastAPI 또는 서비스 API 연동"]
        evaluation = ["출처 정확성", "답변 근거성", "실패 질문 처리와 평가 세트"]
    elif job_role == "Backend Developer":
        title = (
            "인증과 데이터 모델을 갖춘 REST API 구현"
            if index == 0
            else "컨테이너 배포와 운영 점검 가능한 API 확장"
        )
        techniques = ["인증 포함 API", "SQL 데이터 모델", "Docker/AWS 배포 흐름"]
        evaluation = ["API 테스트", "데이터 일관성", "배포 및 장애 대응 기록"]
    elif job_role == "Frontend Developer":
        title = (
            "API 연동 데이터 대시보드와 상태 처리 구현"
            if index == 0
            else "화면 품질 검증과 배포 가능한 사용자 경험 개선"
        )
        techniques = ["React 컴포넌트 설계", "TypeScript 데이터 타입", "API 연동 및 상태 처리"]
        evaluation = ["로딩/오류 상태", "반응형 사용성", "사용자 행동 기반 개선 기록"]
    else:
        title = (
            "핵심 문제를 검증하는 동작형 MVP 구현"
            if index == 0
            else "배포와 사용자 피드백 기반 제품 개선"
        )
        techniques = ["핵심 문제 흐름 구현", "사용자 테스트", "피드백 기반 반복 개선"]
        evaluation = ["작동하는 MVP", "테스트 사용자 피드백", "개선 전후 비교"]
    return _package_blueprint(
        title=title,
        problem=f"{job_role} 직무에서 요구되는 {', '.join(skills)} 역량을 하나의 결과물로 증명합니다.",
        domain_example=f"{domain} 소재를 선택하면 {profile['data']}를 활용해 {profile['decision']} 맥락으로 구현할 수 있습니다.",
        data=f"공개 또는 직접 구성한 {domain} 예시 데이터: {profile['data']}",
        techniques=techniques,
        evaluation=evaluation,
        deliverables=["실행 가능한 결과물", "README 설계 기록", "검증 결과 리포트"],
        skills=skills,
        domain=domain,
    )


def _data_scientist_blueprint(domain: str, profile: dict, index: int, skills: list[str]) -> dict:
    if index == 0:
        title = "분류 모델 비교와 주요 예측 요인 분석 프로젝트"
        problem = "분류 목표를 정의하고 베이스라인과 트리 기반 모델을 비교해 모델링 및 설명 역량을 증명합니다."
        domain_example = (
            f"{domain} 소재를 선택하면 {profile['entity']}의 {profile['classification_problem']}을 "
            f"분석하여 {profile['decision']} 맥락으로 해석할 수 있습니다."
        )
        techniques = [
            "SQL 기반 학습 데이터 정제",
            "Logistic Regression 베이스라인",
            "RandomForest Classifier 비교 모델",
            "Feature Importance 또는 SHAP 기반 요인 분석",
        ]
        evaluation = ["Precision/Recall 또는 F1", "불균형 데이터 처리 근거", "오분류 비용 설명"]
    else:
        title = "회귀 모델 비교와 예측 오차 개선 프로젝트"
        problem = "연속형 목표를 예측하고 모델별 오차와 설명력을 비교해 개선 판단 역량을 증명합니다."
        domain_example = (
            f"{domain} 소재를 선택하면 {profile['regression_problem']}을 분석하여 "
            f"{profile['decision']} 맥락으로 결과를 설명할 수 있습니다."
        )
        techniques = [
            "다중선형 회귀 베이스라인 구현",
            "RandomForest Regressor 비교 모델",
            "교차검증 및 변수 중요도 분석",
            "오차 원인 분석과 개선 실험",
        ]
        evaluation = ["MAE/RMSE", "베이스라인 대비 개선폭", "변수 해석 가능성"]
    return _package_blueprint(
        title=title,
        problem=problem,
        domain_example=domain_example,
        data=profile["data"],
        techniques=techniques,
        evaluation=evaluation,
        deliverables=["분석 노트북 또는 코드", "모델 비교 리포트", "의사결정 요약 README"],
        skills=skills,
        domain=domain,
    )


def _package_blueprint(
    title: str,
    problem: str,
    domain_example: str,
    data: str,
    techniques: list[str],
    evaluation: list[str],
    deliverables: list[str],
    skills: list[str],
    domain: str,
) -> dict:
    return {
        "title": title,
        "domain": domain,
        "problem": problem,
        "domain_example": domain_example,
        "data_plan": data,
        "core_skills": skills,
        "recommendation_basis": (
            f"현재 {', '.join(skills)} 역량을 공고 근거와 현재 수행 단계에 따라 집중 기술로 선정했습니다."
        ),
        "method_basis": (
            "구현 방식과 모델 비교 구성은 선정된 역량을 결과물로 증명하기 위한 프로젝트 설계입니다. "
            "특정 알고리즘의 채용 수요 순위를 의미하지 않습니다."
        ),
        "techniques": techniques,
        "evaluation": evaluation,
        "deliverables": deliverables,
        "validation_rubric": [
            "문제와 목표 변수가 명확하게 정의되어 있는가",
            "기술 또는 모델 선택 이유를 설명할 수 있는가",
            "평가 지표와 결과 비교가 재현 가능한가",
            "실패 사례와 개선 판단이 문서화되어 있는가",
        ],
    }
