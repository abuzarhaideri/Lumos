"""
TutorState — shared LangGraph state that flows through all 5 agent nodes.

Every field is Optional except session_id and raw_document so that the graph
can be entered with a minimal initial state and populated incrementally.
"""

from typing import Any, Dict, List, Optional, TypedDict


class TutorState(TypedDict):
    # ── Session identity ────────────────────────────────────────────────────
    session_id: str
    raw_document: str

    # ── Agent 1a output ─────────────────────────────────────────────────────
    chunks: Optional[List[Dict[str, Any]]]         # list of {id, text, topic_hint}
    document_title: Optional[str]

    # ── Agent 1b output ─────────────────────────────────────────────────────
    learner_profile: Optional[Dict[str, Any]]      # full profiler JSON

    # ── Agent 2 output ──────────────────────────────────────────────────────
    lesson_plan: Optional[Dict[str, Any]]          # {curriculum_title, lessons:[...]}

    # ── Per-lesson loop state ────────────────────────────────────────────────
    current_lesson_index: int
    current_lesson_content: Optional[Dict[str, Any]]   # agent_3 output
    confusion_log: Optional[Dict[str, Any]]             # agent_4 output (on failure)
    validation_result: Optional[Dict[str, Any]]         # agent_5 output
    iteration_count: int
    max_iterations: int
    passed: bool                                        # agent_4 passed flag

    # ── Assembled output ─────────────────────────────────────────────────────
    final_curriculum: Optional[List[Dict[str, Any]]]   # approved lesson contents

    # ── Observability ────────────────────────────────────────────────────────
    agent_log: List[str]
