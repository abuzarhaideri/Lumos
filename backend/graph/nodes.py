"""
LangGraph nodes for the 5-agent Algorithmic Instructional Designer pipeline.

Agent → Model mapping
─────────────────────────────────────────────────────────────────────────────
  Agent 1a  RAG Chunker      nvidia/nemotron-3-nano-30b-a3b:free
  Agent 1b  Learner Profiler nvidia/nemotron-3-nano-30b-a3b:free
  Agent 2   Architect        nvidia/nemotron-3-super-120b-a12b:free
  Agent 3   Content Writer   openai/gpt-oss-120b:free
                  fallback → arcee-ai/trinity-large-preview:free
  Agent 4   Blind Student    z-ai/glm-4.5-air:free  (temperature=0.9)
  Agent 5   Validator        nvidia/nemotron-3-super-120b-a12b:free
"""

import json
import re
from typing import Any

from backend.graph.state import TutorState
from backend.prompts.templates import (
    ARCHITECT_SYSTEM,
    ARCHITECT_USER,
    CHUNKER_SYSTEM,
    CHUNKER_USER,
    CONTENT_CONFUSION_ADDENDUM,
    CONTENT_SYSTEM,
    CONTENT_USER,
    PROFILER_SYSTEM,
    PROFILER_USER,
    STUDENT_SYSTEM,
    STUDENT_USER,
    VALIDATOR_SYSTEM,
    VALIDATOR_USER,
)
from backend.services.openrouter import (
    MODEL_ARCHITECT,
    MODEL_CHUNKER,
    MODEL_CONTENT,
    MODEL_CONTENT_FALLBACK,
    MODEL_PROFILER,
    MODEL_STUDENT,
    MODEL_VALIDATOR,
    generate_text,
)

# ── Default learner diagnostic shown when no profile was supplied ────────────
_DEFAULT_DIAGNOSTIC = """
Q1: What is a variable in programming?
A1: It's like a box that holds a value, you know, like x = 5.

Q2: What is recursion?
A2: (skipped)

Q3: What is time complexity?
A3: (skipped)

Q4: Describe the difference between a stack and a queue.
A4: A stack is LIFO and a queue is FIFO, I think. Like a pile of plates vs a queue at the bank.

Q5: What is dynamic programming?
A5: (skipped)
""".strip()


# ── JSON extraction helper ───────────────────────────────────────────────────

def _extract_json(text: str) -> dict[str, Any]:
    """Strip markdown fences (if the model added them anyway) and parse JSON."""
    # Remove ```json ... ``` or ``` ... ``` fences
    clean = re.sub(r"```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    clean = clean.replace("```", "").strip()
    # Find the outermost JSON object
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"No JSON object found in LLM response:\n{text[:500]}")
    return json.loads(clean[start:end])


# ── SSE helper ───────────────────────────────────────────────────────────────

async def _emit(state: TutorState, message: str, services: dict[str, Any]) -> None:
    state["agent_log"].append(message)
    await services["sse"].publish(state["session_id"], message)


# ── Helper: pick relevant chunks by id list ──────────────────────────────────

def _pick_chunks(
    all_chunks: list[dict], chunk_ids: list[str]
) -> list[dict]:
    id_set = set(chunk_ids)
    return [c for c in all_chunks if c["id"] in id_set]


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1a — RAG CHUNKER
# ══════════════════════════════════════════════════════════════════════════════

async def chunker_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    await _emit(state, "Agent 1a (Chunker): Splitting document into semantic chunks…", services)

    raw = state["raw_document"]
    text = generate_text(
        model=MODEL_CHUNKER,
        system_text=CHUNKER_SYSTEM,
        user_text=CHUNKER_USER.format(raw_document=raw[:20_000]),
        max_tokens=4096,
        temperature=0.1,
    )
    result = _extract_json(text)
    chunks = result.get("chunks", [])
    title = result.get("document_title_guess", "Untitled Document")

    await _emit(
        state,
        f"Agent 1a (Chunker): Created {len(chunks)} chunks. Title: '{title}'",
        services,
    )
    return {**state, "chunks": chunks, "document_title": title}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 1b — LEARNER PROFILER
# ══════════════════════════════════════════════════════════════════════════════

async def profiler_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    await _emit(state, "Agent 1b (Profiler): Analyzing learner profile…", services)

    # Accept a raw diagnostic from the state if available, else fall back
    diagnostic = (
        state.get("learner_profile") or _DEFAULT_DIAGNOSTIC
    )
    if isinstance(diagnostic, dict):
        # already profiled (shouldn't happen on first run, but guard it)
        await _emit(state, "Agent 1b (Profiler): Profile already computed, skipping.", services)
        return state

    text = generate_text(
        model=MODEL_PROFILER,
        system_text=PROFILER_SYSTEM,
        user_text=PROFILER_USER.format(learner_diagnostic=diagnostic),
        max_tokens=1024,
        temperature=0.2,
    )
    profile = _extract_json(text)
    level = profile.get("level", "intermediate")
    style = profile.get("style", "concrete")
    gaps = profile.get("gap_concepts", [])

    await _emit(
        state,
        f"Agent 1b (Profiler): Level={level}, Style={style}, Gaps={gaps}",
        services,
    )
    return {**state, "learner_profile": profile}


# ══════════════════════════════════════════════════════════════════════════════
# NODE 2 — ADAPTIVE ARCHITECT
# ══════════════════════════════════════════════════════════════════════════════

async def architect_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    await _emit(
        state,
        "Agent 2 (Architect): Designing personalized curriculum…",
        services,
    )

    chunks = state["chunks"] or []
    profile = state["learner_profile"] or {}

    text = generate_text(
        model=MODEL_ARCHITECT,
        system_text=ARCHITECT_SYSTEM,
        user_text=ARCHITECT_USER.format(
            source_chunks_json=json.dumps(chunks, indent=2),
            learner_profile_json=json.dumps(profile, indent=2),
        ),
        max_tokens=6144,
        temperature=0.2,
    )
    lesson_plan = _extract_json(text)

    # Filter out skipped lessons so the loop only processes active ones
    active = [
        l for l in lesson_plan.get("lessons", []) if l.get("status") != "skip"
    ]
    lesson_count = len(active)
    title = lesson_plan.get("curriculum_title", state.get("document_title", "Curriculum"))

    await _emit(
        state,
        f"Agent 2 (Architect): '{title}' — {lesson_count} active lessons.",
        services,
    )
    return {
        **state,
        "lesson_plan": lesson_plan,
        "current_lesson_index": 0,
        "final_curriculum": [],
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 3 — CONTENT WRITER
# ══════════════════════════════════════════════════════════════════════════════

async def content_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    lessons = [
        l
        for l in state["lesson_plan"]["lessons"]
        if l.get("status") != "skip"
    ]
    idx = state["current_lesson_index"]
    lesson = lessons[idx]
    iteration = state["iteration_count"]
    lesson_id = lesson.get("id", f"lesson_{idx + 1}")

    # Inject validator must_fix items into confusion_log if coming from a rejection
    confusion_log = state.get("confusion_log")
    validation_result = state.get("validation_result")
    if (
        validation_result
        and validation_result.get("overall_verdict") == "rejected"
        and confusion_log is None
    ):
        # Build a synthetic confusion log from validator must_fix list
        confusion_log = {
            "summary_feedback": "Validator rejected: " + "; ".join(
                validation_result.get("must_fix", [])
            ),
            "per_question": [
                {
                    "question_id": "validator",
                    "confusion_reason": claim,
                    "correct": False,
                }
                for claim in validation_result.get("must_fix", [])
            ],
        }

    if iteration == 0:
        await _emit(
            state, f"Agent 3 (Writer): Writing lesson {idx + 1} — '{lesson.get('title', '')}'", services
        )
        confusion_section = ""
    else:
        await _emit(
            state,
            f"Agent 3 (Writer): Rewriting lesson {idx + 1} — attempt {iteration + 1}.",
            services,
        )
        confusion_section = CONTENT_CONFUSION_ADDENDUM.format(
            confusion_log=json.dumps(confusion_log, indent=2)
        )

    # Gather only the chunks listed in this lesson's relevant_chunk_ids
    all_chunks = state.get("chunks") or []
    relevant_ids = lesson.get("relevant_chunk_ids", [])
    relevant_chunks = _pick_chunks(all_chunks, relevant_ids) if relevant_ids else all_chunks[:3]

    profile = state.get("learner_profile") or {}

    text = generate_text(
        model=MODEL_CONTENT,
        fallback_model=MODEL_CONTENT_FALLBACK,
        system_text=CONTENT_SYSTEM,
        user_text=CONTENT_USER.format(
            lesson_blueprint=json.dumps(lesson, indent=2),
            relevant_chunks_json=json.dumps(relevant_chunks, indent=2),
            learner_profile_json=json.dumps(profile, indent=2),
            iteration=iteration,
            confusion_section=confusion_section,
        ),
        max_tokens=6144,
        temperature=0.4,
    )
    content = _extract_json(text)
    # Ensure required fields
    content.setdefault("lesson_id", lesson_id)
    content.setdefault("iteration", iteration)

    q_count = len(content.get("quiz", {}).get("questions", []))
    await _emit(
        state,
        f"Agent 3 (Writer): Lesson written — {q_count} quiz questions.",
        services,
    )
    return {
        **state,
        "current_lesson_content": content,
        "validation_result": None,  # reset on each new write
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 4 — BLIND STUDENT
# ══════════════════════════════════════════════════════════════════════════════

async def student_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    attempt_num = state["iteration_count"] + 1
    await _emit(
        state,
        f"Agent 4 (Student): Taking quiz — attempt {attempt_num}…",
        services,
    )

    content = state["current_lesson_content"]

    # Build the lesson text from sections — student sees ONLY sections + quiz
    sections_text = "\n\n".join(
        f"[{s['type'].upper()}] {s.get('title', '')}\n{s.get('body') or s.get('snippet', '')}"
        for s in content.get("sections", [])
    )

    text = generate_text(
        model=MODEL_STUDENT,
        system_text=STUDENT_SYSTEM,
        user_text=STUDENT_USER.format(
            lesson_content=sections_text,
            attempt_number=attempt_num,
            quiz_json=json.dumps(content.get("quiz", {}), indent=2),
        ),
        max_tokens=2048,
        temperature=0.9,  # deliberate — makes confusion more realistic
    )
    result = _extract_json(text)

    # Recompute passed to be safe (don't trust the model's own calculation)
    quiz = content.get("quiz", {})
    threshold = float(quiz.get("pass_threshold", 0.75))
    questions = quiz.get("questions", [])
    total = len(questions)
    per_q = result.get("per_question", [])

    earned = 0.0
    for i, q in enumerate(questions):
        matched = next((r for r in per_q if r.get("question_id") == q["id"]), None)
        if matched is None and i < len(per_q):
            matched = per_q[i]
        if matched:
            credit = float(matched.get("partial_credit", 1.0 if matched.get("correct") else 0.0))
            earned += credit

    score = round(earned / total, 4) if total else 0.0
    passed = score >= threshold

    result["score"] = score
    result["passed"] = passed

    score_pct = int(score * 100)
    if passed:
        await _emit(state, f"Agent 4 (Student): PASSED with {score_pct}%.", services)
    else:
        await _emit(state, f"Agent 4 (Student): Failed with {score_pct}%.", services)
        fb = result.get("summary_feedback", "")
        if fb:
            await _emit(state, f"  Feedback: {fb}", services)

    return {
        **state,
        "confusion_log": result,
        "passed": passed,
        "iteration_count": state["iteration_count"] + 1,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE 5 — VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

async def validator_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    content = state["current_lesson_content"]
    lesson_id = content.get("lesson_id", "unknown")
    await _emit(
        state,
        f"Agent 5 (Validator): Validating lesson '{lesson_id}'…",
        services,
    )

    # Gather relevant chunks for this lesson
    lessons = [
        l for l in state["lesson_plan"]["lessons"] if l.get("status") != "skip"
    ]
    idx = state["current_lesson_index"]
    lesson = lessons[idx]
    all_chunks = state.get("chunks") or []
    relevant_ids = lesson.get("relevant_chunk_ids", [])
    relevant_chunks = _pick_chunks(all_chunks, relevant_ids) if relevant_ids else all_chunks[:3]

    text = generate_text(
        model=MODEL_VALIDATOR,
        system_text=VALIDATOR_SYSTEM,
        user_text=VALIDATOR_USER.format(
            lesson_content_json=json.dumps(content, indent=2),
            source_chunks_json=json.dumps(relevant_chunks, indent=2),
        ),
        max_tokens=4096,
        temperature=0.1,
    )
    validation = _extract_json(text)
    verdict = validation.get("overall_verdict", "approved_with_warnings")

    await _emit(
        state,
        f"Agent 5 (Validator): Verdict = {verdict.upper()}",
        services,
    )
    if validation.get("must_fix"):
        await _emit(
            state,
            f"  Must-fix claims: {validation['must_fix']}",
            services,
        )
    if validation.get("warnings"):
        await _emit(
            state,
            f"  Warnings: {len(validation['warnings'])} unsupported claims.",
            services,
        )

    return {**state, "validation_result": validation}


# ══════════════════════════════════════════════════════════════════════════════
# NODE — ADVANCE LESSON (bookkeeping, no LLM call)
# ══════════════════════════════════════════════════════════════════════════════

def advance_lesson_node(state: TutorState) -> TutorState:
    """
    Append the approved lesson to final_curriculum and reset per-lesson state.
    """
    curr = state.get("current_lesson_content")
    curriculum = list(state.get("final_curriculum") or [])
    if curr:
        curriculum.append(curr)

    return {
        **state,
        "current_lesson_index": state["current_lesson_index"] + 1,
        "iteration_count": 0,
        "passed": False,
        "confusion_log": None,
        "validation_result": None,
        "current_lesson_content": None,
        "final_curriculum": curriculum,
    }


# ══════════════════════════════════════════════════════════════════════════════
# NODE — FINALIZE (no LLM call)
# ══════════════════════════════════════════════════════════════════════════════

async def finalize_node(state: TutorState, services: dict[str, Any]) -> TutorState:
    """
    Append the last approved lesson (if any) and emit a completion event.
    """
    curr = state.get("current_lesson_content")
    curriculum = list(state.get("final_curriculum") or [])
    if curr and curr not in curriculum:
        curriculum.append(curr)

    total = len(curriculum)
    await _emit(
        state,
        f"Pipeline complete. {total} lesson(s) approved and assembled.",
        services,
    )
    return {**state, "final_curriculum": curriculum}
