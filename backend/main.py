import asyncio
import os
import uuid
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from dotenv import load_dotenv

from backend.db.client import (
    close_db,
    create_user,
    create_session as db_create_session,
    get_user_by_email,
    get_user_by_id,
    get_session,
    init_db,
    mark_session_complete,
    mark_session_failed,
)
from backend.graph.graph import build_graph
from backend.graph.state import TutorState
from backend.services.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from backend.services.gemini import gemini_generate_text
from backend.services.parser import extract_text
from backend.services.sse import sse_manager
from google.genai import errors as gemini_errors

# Explicitly load backend/.env regardless of current working directory.
load_dotenv(dotenv_path=Path(__file__).with_name(".env"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(title="Algorithmic Instructional Designer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

services = {"sse": sse_manager}
tutor_graph = build_graph(services)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


class ChatResponse(BaseModel):
    reply: str


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


def _extract_bearer_token(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip()


async def _require_user(authorization: Optional[str]) -> dict:
    token = _extract_bearer_token(authorization)
    if not token:
        raise HTTPException(401, "Missing bearer token")
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(401, "Invalid or expired token")
    user = await get_user_by_id(str(payload["sub"]))
    if not user:
        raise HTTPException(401, "User not found")
    return user


@app.post("/api/auth/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    if len(request.password) < 6:
        raise HTTPException(400, "Password must be at least 6 characters.")

    user = await create_user(
        name=request.name.strip(),
        email=str(request.email).lower(),
        password_hash=hash_password(request.password),
    )
    if not user:
        raise HTTPException(409, "Email already registered.")
    token = create_access_token(user["id"], user["email"])
    return AuthResponse(access_token=token, user=user)


@app.post("/api/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    user = await get_user_by_email(str(request.email).lower())
    if not user or not verify_password(request.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password.")
    token = create_access_token(user["id"], user["email"])
    return AuthResponse(
        access_token=token,
        user={"id": user["id"], "name": user["name"], "email": user["email"]},
    )


@app.get("/api/auth/me")
async def me(authorization: Optional[str] = Header(default=None)):
    user = await _require_user(authorization)
    return {"user": user}


@app.post("/api/sessions")
async def create_session(file: UploadFile = File(...)):
    content = await file.read()
    filename = file.filename or "uploaded_document"
    raw_text = extract_text(content, filename)

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
    await db_create_session(session_id, filename, raw_text)

    async def run_graph():
        try:
            final_state = await tutor_graph.ainvoke(initial_state)
            await mark_session_complete(session_id, final_state)
        except Exception as exc:  # noqa: BLE001
            await mark_session_failed(session_id, str(exc))
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
    session = await get_session(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    return {
        "status": session["status"],
        "curriculum": session["result_json"] if session["status"] == "complete" else None,
        "error": session["error_message"] if session["status"] == "failed" else None,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, authorization: Optional[str] = Header(default=None)):
    user = await _require_user(authorization)
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

    try:
        reply = gemini_generate_text(
            model="gemini-2.5-flash",
            system_text=(
                "You are Lumos AI Tutor. Be concise, friendly, and pedagogically helpful. "
                "Use simple language unless user asks for depth. "
                f"The current user is {user['name']} ({user['email']})."
            ),
            user_text=prompt,
            max_output_tokens=512,
            temperature=0.5,
        )
        return ChatResponse(reply=reply)
    except gemini_errors.ClientError as exc:
        return ChatResponse(
            reply=(
                "Gemini API request failed. Check if your API key is valid/active "
                f"and not restricted. Error: {exc}"
            )
        )
