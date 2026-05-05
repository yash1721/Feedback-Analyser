from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.domain.evaluation.models import EvaluationDataset, EvaluationExample, EvaluationRun, EvaluationRunItem


class EvaluationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_dataset_by_name_version(self, *, name: str, version: str) -> EvaluationDataset | None:
        return self.session.scalar(
            select(EvaluationDataset)
            .options(selectinload(EvaluationDataset.examples))
            .where(EvaluationDataset.name == name, EvaluationDataset.version == version)
            .limit(1)
        )

    def create_dataset(
        self,
        *,
        name: str,
        version: str,
        description: str | None,
        source_path: str | None,
        metadata_json: dict | None,
    ) -> EvaluationDataset:
        dataset = EvaluationDataset(
            name=name,
            version=version,
            description=description,
            source_path=source_path,
            metadata_json=metadata_json,
        )
        self.session.add(dataset)
        self.session.flush()
        self.session.refresh(dataset)
        return dataset

    def replace_examples(self, dataset: EvaluationDataset, examples: list[dict]) -> list[EvaluationExample]:
        existing_by_external_id = {
            example.external_id: example
            for example in self.session.scalars(
                select(EvaluationExample).where(EvaluationExample.dataset_id == dataset.id)
            )
        }
        created: list[EvaluationExample] = []
        for example in examples:
            row = existing_by_external_id.get(example["external_id"])
            if row is None:
                row = EvaluationExample(dataset_id=dataset.id, **example)
                self.session.add(row)
            else:
                row.feedback_text = example["feedback_text"]
                row.expected_json = example["expected_json"]
                row.notes = example["notes"]
            created.append(row)
        self.session.flush()
        for row in created:
            self.session.refresh(row)
        return created

    def create_run(self, **fields) -> EvaluationRun:
        run = EvaluationRun(**fields)
        self.session.add(run)
        self.session.flush()
        self.session.refresh(run)
        return run

    def update_run(self, run: EvaluationRun, **fields) -> EvaluationRun:
        for key, value in fields.items():
            setattr(run, key, value)
        self.session.flush()
        self.session.refresh(run)
        return run

    def create_run_item(self, **fields) -> EvaluationRunItem:
        item = EvaluationRunItem(**fields)
        self.session.add(item)
        self.session.flush()
        self.session.refresh(item)
        return item

    def get_run(self, run_id: int) -> EvaluationRun | None:
        return self.session.scalar(
            select(EvaluationRun)
            .options(selectinload(EvaluationRun.items))
            .where(EvaluationRun.id == run_id)
        )

    def list_runs(self, *, limit: int, offset: int) -> tuple[list[EvaluationRun], int]:
        statement = select(EvaluationRun)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        runs = list(
            self.session.scalars(
                statement.order_by(EvaluationRun.created_at.desc(), EvaluationRun.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return runs, total
