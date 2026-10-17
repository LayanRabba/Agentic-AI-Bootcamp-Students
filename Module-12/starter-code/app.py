"""
General Chat Agent: WebSocket-based streaming chat with memory & budget tracking.
Demonstrates memory compaction with visible UI feedback.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")

from memory_manager import (
    ShortTermMemory,
    init_llm,
    init_storage,
    recall_memories,
    store_memory,
    get_memory_stats,
    estimate_tokens,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chat Agent with Memory & Budget")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize LLM, storage, and memory on app start."""
    init_llm()
    init_storage(wipe=False)
    logger.info("Agent initialized: LLM + memory storage ready")


class MessageRequest(BaseModel):
    message: str


conversation_memory = ShortTermMemory()  # latest session, used by /memory/stats


@app.get("/health")
async def health():
    """Health check endpoint."""
    return JSONResponse({"status": "ok", "service": "chat-agent"})


@app.get("/memory/stats")
async def memory_stats():
    """Get memory usage statistics."""
    stats = get_memory_stats()
    return JSONResponse(
        {
            "short_term_turns": len(conversation_memory.turns),
            "summaries": len(conversation_memory.summaries),
            "total_tokens": conversation_memory.total_tokens,
            "long_term_memories": stats.get("long_term_memories", 0),
            "needs_compaction": conversation_memory.needs_compaction,
        }
    )


@app.get("/")
async def index():
    """Serve the UI."""
    return FileResponse(HERE / "static" / "index.html")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for streaming chat."""
    global conversation_memory
    await websocket.accept()
    logger.info("WebSocket connection established")

    # Short-term memory is per session; long-term memory (chroma) is shared and persistent
    conversation_memory = ShortTermMemory()
    session_memory = conversation_memory

    try:
        while True:
            data = await websocket.receive_text()
            msg_req = MessageRequest(**json.loads(data))

            # Add user message to memory
            status = session_memory.add_turn("user", msg_req.message)

            # Notify of compaction
            if status.get("compacted"):
                await websocket.send_text(
                    json.dumps(
                        {"type": "compacting", "status": "Compacting conversation..."}
                    )
                )

            # Retrieve memories (before storing, so the message doesn't recall itself)
            memories = recall_memories(msg_req.message)
            store_memory(msg_req.message, memory_type="user_fact")
            memory_context = ""
            if memories:
                memory_context = "Relevant memories:\n"
                for mem in memories:
                    memory_context += f"  • {mem['text']}\n"

            # Build context
            conv_context = session_memory.get_context_for_llm()
            prompt = f"""{conv_context}

{memory_context}

User: {msg_req.message}
Assistant:"""

            # Stream response from LLM
            from langchain_openai import ChatOpenAI

            llm = ChatOpenAI(
                model=os.getenv("MODEL", "openai/gpt-4o-mini"),
                api_key=os.getenv("OPENROUTER_API_KEY"),
                base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                temperature=0,
            )

            response_text = ""
            try:
                # Real streaming: forward each chunk as soon as the LLM produces it
                async for chunk in llm.astream(prompt):
                    token = chunk.content
                    if not token:
                        continue
                    response_text += token
                    await websocket.send_text(
                        json.dumps({"type": "token", "text": token})
                    )

            except Exception as e:
                await websocket.send_text(
                    json.dumps({"type": "error", "text": str(e)})
                )
                continue

            # Store assistant response and extract memories
            await websocket.send_text(json.dumps({"type": "token", "text": "\n"}))
            session_memory.add_turn("assistant", response_text)

            # Send budget info
            budget = {
                "total_tokens": session_memory.total_tokens,
                "short_term_turns": len(session_memory.turns),
                "summaries": len(session_memory.summaries),
                "long_term_memories": get_memory_stats().get("long_term_memories", 0),
            }
            await websocket.send_text(json.dumps({"type": "budget", "data": budget}))
            await websocket.send_text(json.dumps({"type": "done"}))

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "text": str(e)}))
        except Exception:
            pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
