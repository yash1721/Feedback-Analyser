import json
from pathlib import Path

from app.domain.evaluation.schemas import EvaluationDatasetFile


DEFAULT_DATASET_PATH = Path(__file__).parent / "fixtures" / "feedback_eval_seed.json"


class EvaluationDatasetLoader:
    def load(self, dataset_path: str | Path | None = None) -> EvaluationDatasetFile:
        path = Path(dataset_path) if dataset_path else DEFAULT_DATASET_PATH
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        return EvaluationDatasetFile.model_validate(payload)
