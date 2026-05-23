from dataclasses import dataclass

from sklearn.ensemble import RandomForestClassifier


@dataclass
class PredictionResult:
    probability: float
    diffusion_time: float
    impact: str
    model_type: str = "random_forest"


class RandomForestPredictionService:
    def predict(
        self,
        global_score: float,
        domestic_score: float,
        growth_rate: float,
        time_lag: int,
    ) -> PredictionResult:
        model = RandomForestClassifier(n_estimators=50, random_state=42)
        model.fit(self._training_features(), self._training_labels())

        features = [[global_score, domestic_score, growth_rate, time_lag]]
        probability = float(model.predict_proba(features)[0][1])
        diffusion_time = self._estimate_diffusion_time(
            probability=probability,
            growth_rate=growth_rate,
            time_lag=time_lag,
        )

        return PredictionResult(
            probability=round(probability, 4),
            diffusion_time=diffusion_time,
            impact=self._impact_from_probability(probability),
        )

    def _training_features(self) -> list[list[float]]:
        return [
            [95.0, 90.0, 18.0, 1],
            [88.0, 82.0, 14.0, 2],
            [80.0, 78.0, 10.0, 3],
            [72.0, 65.0, 7.5, 4],
            [65.0, 58.0, 4.0, 6],
            [55.0, 50.0, 2.5, 8],
            [45.0, 40.0, 1.0, 10],
            [35.0, 32.0, -1.0, 12],
            [25.0, 20.0, -3.5, 14],
            [15.0, 12.0, -6.0, 18],
        ]

    def _training_labels(self) -> list[int]:
        return [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]

    def _estimate_diffusion_time(
        self,
        probability: float,
        growth_rate: float,
        time_lag: int,
    ) -> float:
        growth_adjustment = max(growth_rate, 0.0) / 10
        estimated_time = time_lag + (1 - probability) * 12 - growth_adjustment
        return round(max(1.0, estimated_time), 2)

    def _impact_from_probability(self, probability: float) -> str:
        if probability >= 0.7:
            return "높음"
        if probability >= 0.4:
            return "보통"
        return "낮음"
