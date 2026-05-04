from dataclasses import dataclass

from app.domain.retrieval.vector_store import SearchResult


ALLOWED_TEAMS = [
    "Payment Team",
    "Frontend Team",
    "Backend Team",
    "Customer Support Team",
    "Logistics Team",
    "Design Team",
    "Marketing Team",
    "Sales Team",
    "Human Resources Team",
    "Product Team",
]


@dataclass(frozen=True)
class AnalysisPrompt:
    version: str
    feedback_text: str
    evidence_context: str
    prompt_text: str


def build_feedback_analysis_prompt(
    *,
    feedback_text: str,
    evidence: list[SearchResult],
    prompt_version: str,
) -> AnalysisPrompt:
    evidence_lines = []
    for index, item in enumerate(evidence, start=1):
        chunk_id = item.chunk_id if item.chunk_id is not None else "unknown"
        evidence_lines.append(f"[{index}] chunk_id={chunk_id} score={item.score:.4f}: {item.text}")
    evidence_context = "\n".join(evidence_lines) if evidence_lines else "No retrieval evidence was found."
    prompt_text = f"""You are FeedbackIQ's feedback analysis component.

Analyze the feedback using the retrieved evidence when relevant.
If evidence is weak or absent, lower confidence and say that in reasoning_summary.
Return only strict JSON. Do not include chain-of-thought.

Allowed sentiment_label values: POSITIVE, NEGATIVE, NEUTRAL, MIXED.
Allowed category values: PAYMENT, UI, BACKEND, SUPPORT, PERFORMANCE, SECURITY, PRODUCT, DELIVERY, OTHER.
Allowed severity values: P0, P1, P2, P3.
Allowed routed_team values: {", ".join(ALLOWED_TEAMS)}.

JSON fields:
sentiment_label, sentiment_score, category, severity, routed_team, summary,
recommended_action, confidence_score, reasoning_summary, evidence_chunk_ids.

Feedback:
{feedback_text}

Evidence:
{evidence_context}
"""
    return AnalysisPrompt(
        version=prompt_version,
        feedback_text=feedback_text,
        evidence_context=evidence_context,
        prompt_text=prompt_text,
    )
