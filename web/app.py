"""Small web UI for the agent: streaming chat plus a run inspector.

    uvicorn web.app:app --reload     →  http://localhost:8000

One Agent per browser session, kept in memory (same as the terminal chat).
"""

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from src.agent import Agent

app = FastAPI(title="Empório da Música")
sessions: dict[str, Agent] = {}


class ChatRequest(BaseModel):
    session_id: str
    message: str


@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "index.html")


@app.post("/api/chat")
def chat(req: ChatRequest):
    agent = sessions.setdefault(req.session_id, Agent.from_env())

    def events():  # Server-Sent Events: one JSON event per line
        try:
            for event in agent.stream(req.message):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")


@app.post("/api/reset/{session_id}")
def reset(session_id: str):
    sessions.pop(session_id, None)
    return {"ok": True}
