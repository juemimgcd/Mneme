"""Map explicit answer modes to their allowed private evidence sources.

Plans are deterministic policy: they bound retrieval rather than infer permissions from model output.
"""

from app.mneme.memoria.server.runtime.contracts import RetrievalPlan

MODE_PLANS = {
    "kb_qa": RetrievalPlan(document=True, memory=True, profile=False, relations=False, max_expansions=1),
    "memory_query": RetrievalPlan(document=False, memory=True, profile=False, relations=False, max_expansions=1),
    "profile_query": RetrievalPlan(document=False, memory=True, profile=True, relations=False, max_expansions=0),
    "analysis_query": RetrievalPlan(document=True, memory=True, profile=True, relations=True, max_expansions=1),
    "general_chat": RetrievalPlan(document=False, memory=False, profile=False, relations=False, max_expansions=0),
}
