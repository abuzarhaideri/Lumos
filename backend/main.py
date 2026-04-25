import asyncio
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from backend.graph.graph import build_graph
from backend.graph.state import TutorState
from backend.services.gemini import gemini_generate_text
from backend.services.parser import extract_text
from backend.services.sse import sse_manager

# Explicitly load backend/.env regardless of current working directory.
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))

app = FastAPI(title="Algorithmic Instructional Designer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

services = {"sse": sse_manager}
tutor_graph = build_graph(services)

# Demo-only store; replace with Postgres in production.
sessions: dict[str, dict] = {}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


@app.post("/api/sessions")
async def create_session(file: UploadFile = File(...)):
    content = await file.read()
    raw_text = extract_text(content, file.filename)

    if not raw_text.strip():
        raise HTTPException(400, "Could not extract text from document.")

    session_id = str(uuid.uuid4())
    initial_state: TutorState = {
        "session_id": session_id,
        "raw_document": raw_text,
        "lesson_plan": None,
        "current_lesson_index": 0,
        "current_lesson_content": None,
        "confusion_log": None,
        "iteration_count": 0,
        "max_iterations": 3,
        "passed": False,
        "agent_log": [],
        "final_curriculum": None,
    }

    sessions[session_id] = {"status": "running", "state": None}

    async def run_graph():
        try:
            final_state = await tutor_graph.ainvoke(initial_state)
            sessions[session_id]["status"] = "complete"
            sessions[session_id]["state"] = final_state
        except Exception as exc:  # noqa: BLE001
            sessions[session_id]["status"] = "failed"
            await sse_manager.publish(session_id, f"Error: {str(exc)}")
        finally:
            await sse_manager.close(session_id)

    asyncio.create_task(run_graph())
    return {"session_id": session_id}


@app.get("/api/sessions/{session_id}/stream")
async def stream_events(session_id: str):
    return StreamingResponse(
        sse_manager.subscribe(session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/sessions/{session_id}/result")
async def get_result(session_id: str):
    session = sessions.get(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "status": session["status"],
        "curriculum": session["state"] if session["status"] == "complete" else None,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    user_messages = [m for m in request.messages if m.role in {"user", "assistant"}]
    if not user_messages:
        raise HTTPException(400, "At least one user message is required.")

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        last_user = next((m.content for m in reversed(user_messages) if m.role == "user"), "")
        return ChatResponse(
            reply=(
                f"Hi! I received: '{last_user}'. "
                "Add GEMINI_API_KEY in backend env for real AI replies."
            )
        )

    # Gemini expects "model" for assistant role in explicit content arrays, but for simplicity
    # we turn chat history into a single text prompt.
    conversation = []
    for m in user_messages:
        prefix = "User" if m.role == "user" else "Assistant"
        conversation.append(f"{prefix}: {m.content}")
    prompt = "\n".join(conversation) + "\nAssistant:"

    reply = gemini_generate_text(
        model="gemini-2.5-flash",
        system_text=(
            "You are Lumos AI Tutor. Be concise, friendly, and pedagogically helpful. "
            "Use simple language unless user asks for depth."
        ),
        user_text=prompt,
        max_output_tokens=512,
        temperature=0.5,
    )
    return ChatResponse(reply=reply)
