from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from backend.graph.nodes import architect_node, content_node, student_node
from backend.graph.state import TutorState


def should_retry(state: TutorState) -> str:
    if state["passed"]:
        return "advance_or_finish"
    if state["iteration_count"] >= state["max_iterations"]:
        return "advance_or_finish"
    return "retry_content"


def advance_or_finish(state: TutorState) -> str:
    lessons = state["lesson_plan"]["lessons"]
    next_idx = state["current_lesson_index"] + 1
    if next_idx < len(lessons):
        return "next_lesson"
    return "finish"


def build_graph(services: dict[str, Any]):
    graph = StateGraph(TutorState)

    graph.add_node("architect", partial(architect_node, services=services))
    graph.add_node("content", partial(content_node, services=services))
    graph.add_node("student", partial(student_node, services=services))

    def _advance(state: TutorState) -> TutorState:
        return {
            **state,
            "current_lesson_index": state["current_lesson_index"] + 1,
            "iteration_count": 0,
            "passed": False,
            "confusion_log": None,
            "current_lesson_content": None,
        }

    graph.add_node("advance_lesson", _advance)
    graph.add_node("check_done", lambda s: s)

    graph.set_entry_point("architect")
    graph.add_edge("architect", "content")
    graph.add_edge("content", "student")

    graph.add_conditional_edges(
        "student",
        should_retry,
        {"retry_content": "content", "advance_or_finish": "check_done"},
    )

    graph.add_conditional_edges(
        "check_done",
        advance_or_finish,
        {"next_lesson": "advance_lesson", "finish": END},
    )
    graph.add_edge("advance_lesson", "content")

    return graph.compile()
