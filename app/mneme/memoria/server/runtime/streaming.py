"""Convert completed runtime phases and validated answers into stream-safe events.

Answer text is chunked only after validation, so clients never receive content that may be rolled back.
"""

def phase_event_name(phase: str, status: str) -> str | None:
    """Map an internal phase transition to its stable public event name.

    Returns ``None`` for internal transitions that are intentionally not
    exposed to clients.
    """
    return {
        ("retrieve", "started"): "retrieval.started",
        ("generate", "started"): "answer.started",
        ("grounding", "completed"): "grounding.decided",
        ("citations", "completed"): "citation.resolved",
    }.get((phase, status))


def answer_chunks(answer: str, *, size: int = 160) -> list[str]:
    """Split a fully validated answer into deterministic transport chunks.

    This function is called after answer and citation validation; chunking
    must not be confused with provider-native token streaming.
    """
    return [answer[index : index + size] for index in range(0, len(answer), size)]
