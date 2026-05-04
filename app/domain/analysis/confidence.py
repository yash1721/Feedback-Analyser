from app.domain.analysis.schemas import StructuredAnalysisOutput
from app.domain.retrieval.vector_store import SearchResult


def apply_confidence_policy(
    output: StructuredAnalysisOutput,
    *,
    evidence: list[SearchResult],
    threshold: float,
) -> StructuredAnalysisOutput:
    confidence = output.confidence_score
    if not evidence:
        confidence = min(confidence, 0.35)
    elif output.evidence_chunk_ids:
        confidence = max(confidence, min(threshold, 0.75))
    return output.model_copy(update={"confidence_score": confidence})
