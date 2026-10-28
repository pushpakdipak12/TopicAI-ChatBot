"""FastAPI backend and single-page chat interface."""

import logging
from pathlib import Path
from uuid import UUID

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.agent import chat_with_agent
from app.formatting import render_answer_html
from app.topics import TOPICS

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="TopicChat AI", version="1.0.0")


class ChatRequest(BaseModel):
    session_id: UUID
    topic: str = Field(min_length=1, max_length=50)
    message: str = Field(min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    answer: str
    answer_html: str
    topic: str


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(BASE_DIR / "static" / "index.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/topics")
def topics():
    return {"topics": list(TOPICS)}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    if request.topic not in TOPICS:
        raise HTTPException(status_code=400, detail="Choose a topic from /topics")
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="Message cannot be blank")
    try:
        answer = chat_with_agent(request.message, request.topic, request.session_id)
        return ChatResponse(answer=answer, answer_html=render_answer_html(answer), topic=request.topic)
    except RuntimeError as exc:
        # This includes a missing GROQ_API_KEY, which is useful in local development.
        logger.warning("Chat unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Chat request failed")
        raise HTTPException(status_code=502, detail="Chat provider request failed. Check server logs.") from exc
