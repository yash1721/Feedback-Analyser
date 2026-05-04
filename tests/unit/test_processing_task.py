from app.workers import tasks


def test_process_feedback_record_task_delegates_to_processor(monkeypatch):
    calls: list[int] = []

    def fake_process(feedback_id: int, *, feedback_service_scope_provider):
        calls.append(feedback_id)
        return {"feedback_id": feedback_id, "processing_status": "COMPLETED"}

    monkeypatch.setattr(tasks, "process_feedback_record_with_scope", fake_process)

    result = tasks.process_feedback_record.run(123)

    assert result == {"feedback_id": 123, "processing_status": "COMPLETED"}
    assert calls == [123]
