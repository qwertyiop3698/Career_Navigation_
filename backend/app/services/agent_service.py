from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.ml_service import PredictionResult, RandomForestPredictionService
from app.services.rag_service import RagService


@dataclass
class CareerPathResult:
    future_job: str
    demand_probability: float
    impact: str
    recommended_skills: list[str]
    roadmap: list[dict]
    evidence_documents: list[dict]


class AgentCareerService:
    def __init__(
        self,
        rag_service: RagService | None = None,
        prediction_service: RandomForestPredictionService | None = None,
    ):
        self.rag_service = rag_service or RagService()
        self.prediction_service = prediction_service or RandomForestPredictionService()

    def create_career_path(
        self,
        db: Session,
        job_role: str,
        target_skill: str,
        user_id: UUID | None = None,
    ) -> CareerPathResult:
        evidence_documents = self.rag_service.search_documents(
            db=db,
            query=f"{job_role} {target_skill} career roadmap skills",
            top_k=5,
        )
        prediction = self._predict_demand(target_skill, evidence_documents)
        recommended_skills = self._recommended_skills(target_skill)
        roadmap = self._build_roadmap(target_skill, recommended_skills)

        result = CareerPathResult(
            future_job=job_role,
            demand_probability=prediction.probability,
            impact=prediction.impact,
            recommended_skills=recommended_skills,
            roadmap=roadmap,
            evidence_documents=evidence_documents,
        )

        return result

    def _predict_demand(
        self,
        target_skill: str,
        evidence_documents: list[dict],
    ) -> PredictionResult:
        average_similarity = self._average_similarity(evidence_documents)
        skill_bonus = min(len(target_skill.strip()) * 1.5, 15.0)

        global_score = min(95.0, 60.0 + average_similarity * 30 + skill_bonus)
        domestic_score = min(90.0, 55.0 + average_similarity * 25 + skill_bonus)
        growth_rate = min(20.0, 6.0 + average_similarity * 12)
        time_lag = max(1, int(8 - average_similarity * 5))

        return self.prediction_service.predict(
            global_score=global_score,
            domestic_score=domestic_score,
            growth_rate=growth_rate,
            time_lag=time_lag,
        )

    def _average_similarity(self, evidence_documents: list[dict]) -> float:
        if not evidence_documents:
            return 0.35

        total_similarity = sum(
            max(0.0, float(document["similarity_score"]))
            for document in evidence_documents
        )
        return min(1.0, total_similarity / len(evidence_documents))

    def _recommended_skills(self, target_skill: str) -> list[str]:
        base_skills = [
            target_skill,
            "Python",
            "SQL",
            "RAG",
            "LLM Evaluation",
            "Agent Workflow",
            "MLOps",
        ]

        recommended = []
        seen = set()
        for skill in base_skills:
            normalized = skill.strip()
            key = normalized.lower()
            if normalized and key not in seen:
                recommended.append(normalized)
                seen.add(key)

        return recommended

    def _build_roadmap(
        self,
        target_skill: str,
        recommended_skills: list[str],
    ) -> list[dict]:
        return [
            {
                "step": 1,
                "title": "핵심 기술 기초 다지기",
                "items": recommended_skills[:3],
            },
            {
                "step": 2,
                "title": "AI 기술 적용하기",
                "items": self._unique_items([target_skill, "RAG", "LLM Evaluation"]),
            },
            {
                "step": 3,
                "title": "에이전트 워크플로우 실습하기",
                "items": ["Agent Workflow", "MLOps"],
            },
        ]

    def _unique_items(self, items: list[str]) -> list[str]:
        unique = []
        seen = set()
        for item in items:
            key = item.lower()
            if key not in seen:
                unique.append(item)
                seen.add(key)
        return unique
