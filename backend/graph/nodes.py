import json
import re
from typing import Any

from backend.graph.state import TutorState
from backend.prompts.templates import (
    ARCHITECT_SYSTEM,
    ARCHITECT_USER,
    CONTENT_CONFUSION_ADDENDUM,
    CONTENT_SYSTEM,
    CONTENT_USER,
    STUDENT_SYSTEM,
    STUDENT_USER,
)
from backend.services.gemini import gemini_generate_text

GEMINI_MODEL = "gemini-2.5-flash"


def _extract_json(text: str) -> dict[str, Any]:
    clean = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()
    return json.loads(clean)


async def emit(state: TutorState, message: str, services: dict[str, Any]) -> None:
    state["agent_log"].append(message)
    await services["sse"].publish(state["session_id"], message)


async def architect_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    await emit(
        state,
        "Architect Agent: Analyzing document and designing curriculum...",
        services,
    )
    text = gemini_generate_text(
        model=GEMINI_MODEL,
        system_text=ARCHITECT_SYSTEM,
        user_text=ARCHITECT_USER.format(raw_document=state["raw_document"][:12000]),
        max_output_tokens=4096,
        temperature=0.2,
    )
    lesson_plan = _extract_json(text)
    lesson_count = len(lesson_plan.get("lessons", []))
    await emit(
        state,
        f"Architect Agent: Created {lesson_count}-lesson curriculum.",
        services,
    )
    return {**state, "lesson_plan": lesson_plan, "current_lesson_index": 0}


async def content_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    lessons = state["lesson_plan"]["lessons"]
    idx = state["current_lesson_index"]
    lesson = lessons[idx]
    iteration = state["iteration_count"]

    if iteration == 0:
        await emit(state, f"Content Agent: Writing lesson {idx + 1}.", services)
        confusion_section = ""
    else:
        await emit(
            state,
            f"Content Agent: Rewriting after confusion (attempt {iteration + 1}).",
            services,
        )
        confusion_section = CONTENT_CONFUSION_ADDENDUM.format(
            confusion_log=json.dumps(state["confusion_log"], indent=2)
        )

    text = gemini_generate_text(
        model=GEMINI_MODEL,
        system_text=CONTENT_SYSTEM,
        user_text=CONTENT_USER.format(
            lesson_blueprint=json.dumps(lesson, indent=2),
            confusion_section=confusion_section,
        ),
        max_output_tokens=4096,
        temperature=0.4,
    )
    content = _extract_json(text)
    q_count = len(content.get("quiz", {}).get("questions", []))
    await emit(state, f"Content Agent: Lesson written with {q_count} questions.", services)
    return {**state, "current_lesson_content": content}


async def student_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    attempt_num = state["iteration_count"] + 1
    await emit(state, f"Student Agent: Taking quiz (attempt {attempt_num}).", services)

    content = state["current_lesson_content"]
    sections_text = "\n\n".join(
        [
            f"[{s['type'].upper()}] {s.get('title', '')}\n{s.get('body', s.get('snippet', ''))}"
            for s in content["sections"]
        ]
    )

    text = gemini_generate_text(
        model=GEMINI_MODEL,
        system_text=STUDENT_SYSTEM,
        user_text=STUDENT_USER.format(
            lesson_content=sections_text,
            attempt_number=attempt_num,
            quiz=json.dumps(content["quiz"], indent=2),
        ),
        max_output_tokens=2048,
        temperature=0.2,
    )
    result = _extract_json(text)
    score = float(result["score"])
    score_pct = int(score * 100)
    passed = score >= content["quiz"]["pass_threshold"]
    result["passed"] = passed

    if passed:
        await emit(state, f"Student Agent: PASSED with {score_pct}%.", services)
    else:
        await emit(state, f"Student Agent: Failed with {score_pct}%.", services)
        await emit(state, f"Confusion: {result.get('summary_feedback', '')}", services)

    return {
        **state,
        "confusion_log": result,
        "passed": passed,
        "iteration_count": state["iteration_count"] + 1,
    }
