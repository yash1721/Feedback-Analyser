from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class EnqueuedProcessingJob:
    task_id: str | None


class ProcessingQueue(Protocol):
    def enqueue_feedback_record(self, feedback_id: int) -> EnqueuedProcessingJob:
        """Submit a feedback record for background processing."""


class CeleryProcessingQueue:
    def enqueue_feedback_record(self, feedback_id: int) -> EnqueuedProcessingJob:
        from app.workers.tasks import process_feedback_record

        async_result = process_feedback_record.delay(feedback_id)
        return EnqueuedProcessingJob(task_id=async_result.id)
