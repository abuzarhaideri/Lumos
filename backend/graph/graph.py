"""
LangGraph execution graph for the 5-agent Algorithmic Instructional Designer.

Full pipeline:

  chunker → profiler → architect → (per-lesson loop):
    content → student → [if pass] → validator → [if approved] → advance → content (next lesson)
                      ↑                        ↘ [if rejected] ↗
                      └── [if fail, iter<max] ──┘
  After all lessons: → finalize → END
"""

from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from backend.graph.nodes import (
    advance_lesson_node,
    architect_node,
    chunker_node,
    content_node,
    finalize_node,
    profiler_node,
    student_node,
    validator_node,
)
from backend.graph.state import TutorState


# ── Conditional edge: should we retry content or move to validation? ─────────

def _should_retry_or_validate(state: TutorState) -> str:
    """After the student node: retry content, or advance to the validator."""
    if state["passed"]:
        return "validate"
    if state["iteration_count"] >= state["max_iterations"]:
        # Force advance — log note already written in student_node
        return "validate"
    return "retry_content"


# ── Conditional edge: after validator, approve or force rewrite ──────────────

def _validator_decision(state: TutorState) -> str:
    """After the validator node: advance lesson or trigger a rewrite."""
    result = state.get("validation_result") or {}
    verdict = result.get("overall_verdict", "approved")
    if verdict == "rejected":
        # Check we haven't exhausted retries already
        if state["iteration_count"] < state["max_iterations"]:
            return "rejected_rewrite"
        # Exhausted — force advance anyway
    return "approved"


# ── Conditional edge: after advancing, are there more lessons? ───────────────

def _advance_or_finish(state: TutorState) -> str:
    """After advancing the lesson index, check if there are more to process."""
    lessons = [
        l
        for l in state["lesson_plan"]["lessons"]
        if l.get("status") != "skip"
    ]
    if state["current_lesson_index"] < len(lessons):
        return "next_lesson"
    return "finish"


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph(services: dict[str, Any]):
    graph = StateGraph(TutorState)

    # ── Register nodes ────────────────────────────────────────────────────────
    graph.add_node("chunker",       partial(chunker_node,   services=services))
    graph.add_node("profiler",      partial(profiler_node,  services=services))
    graph.add_node("architect",     partial(architect_node, services=services))
    graph.add_node("content",       partial(content_node,   services=services))
    graph.add_node("student",       partial(student_node,   services=services))
    graph.add_node("validator",     partial(validator_node, services=services))
    graph.add_node("advance_lesson", advance_lesson_node)
    graph.add_node("finalize",      partial(finalize_node,  services=services))

    # ── Static edges ──────────────────────────────────────────────────────────
    graph.set_entry_point("chunker")
    graph.add_edge("chunker",   "profiler")
    graph.add_edge("profiler",  "architect")
    graph.add_edge("architect", "content")
    graph.add_edge("content",   "student")

    # ── Student → retry or validate ───────────────────────────────────────────
    graph.add_conditional_edges(
        "student",
        _should_retry_or_validate,
        {
            "retry_content": "content",
            "validate":      "validator",
        },
    )

    # ── Validator → approved (advance) or rejected (rewrite) ─────────────────
    graph.add_conditional_edges(
        "validator",
        _validator_decision,
        {
            "approved":        "advance_lesson",
            "rejected_rewrite": "content",
        },
    )

    # ── Advance → next lesson or finalize ─────────────────────────────────────
    graph.add_conditional_edges(
        "advance_lesson",
        _advance_or_finish,
        {
            "next_lesson": "content",
            "finish":      "finalize",
        },
    )

    graph.add_edge("finalize", END)

    return graph.compile()
