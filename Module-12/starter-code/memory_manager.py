"""
Memory manager: short-term summarization + long-term persistent storage.
Tracks token budget and triggers compaction with visible UI feedback.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import re
import shutil
from pathlib import Path
from typing import Optional

import chromadb
from langchain_openai import ChatOpenAI
from pydantic import BaseModel

HERE = Path(__file__).resolve().parent
DB_DIR = HERE / "memory_store"

# Configuration
SUMMARIZE_AFTER_TURNS = 5
KEEP_LAST = 3
TOP_K = 3
MIN_SIMILARITY = 0.20
MAX_CONTEXT_TOKENS = 2000

# Memory models
class Turn(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: dt.datetime


class ConversationSummary(BaseModel):
    summary: str
    turn_range: str  # "turns 1-5"
    token_count: int


class StoredMemory(BaseModel):
    text: str
    memory_type: str  # "preference", "fact", "context"
    timestamp: dt.datetime
    source: str  # which turn it came from


# Clients
llm: ChatOpenAI
chroma_client: chromadb.PersistentClient
collection: chromadb.Collection


def init_storage(wipe: bool = False):
    """Initialize chromadb collection for long-term memory."""
    global chroma_client, collection
    if wipe:
        shutil.rmtree(DB_DIR, ignore_errors=True)
    chroma_client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = chroma_client.get_or_create_collection(
        "chat_memories", metadata={"hnsw:space": "cosine"}
    )


def reset_memories() -> int:
    """Delete every long-term memory. Returns how many were removed."""
    global collection
    removed = collection.count()
    chroma_client.delete_collection("chat_memories")
    collection = chroma_client.get_or_create_collection(
        "chat_memories", metadata={"hnsw:space": "cosine"}
    )
    return removed


def init_llm(model: str = None, api_key: str = None, base_url: str = None):
    """Initialize the LLM client."""
    global llm
    if model is None:
        model = os.getenv("MODEL", "openai/gpt-4o-mini")
    if api_key is None:
        api_key = os.getenv("OPENROUTER_API_KEY")
    if base_url is None:
        base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    llm = ChatOpenAI(
        model=model,
        temperature=0,
        base_url=base_url,
        api_key=api_key,
    )


def estimate_tokens(text: str) -> int:
    """Rough token count: ~1 token per 4 chars."""
    return len(text) // 4


class ShortTermMemory:
    """Rolling buffer of recent turns with auto-summarization."""

    def __init__(self, summarize_after: int = SUMMARIZE_AFTER_TURNS):
        self.turns: list[Turn] = []
        self.summaries: list[ConversationSummary] = []
        self.summarize_after = summarize_after
        self.total_tokens = 0
        self.needs_compaction = False

    def add_turn(self, role: str, content: str) -> dict:
        """Add a turn and check if compaction is needed. Returns status dict."""
        turn = Turn(role=role, content=content, timestamp=dt.datetime.now())
        self.turns.append(turn)
        self.total_tokens += estimate_tokens(content)

        status = {"compacted": False, "summary_created": False}

        if len(self.turns) > self.summarize_after:
            status = self._compact()

        return status

    def _compact(self) -> dict:
        """Summarize older turns, keep recent ones."""
        self.needs_compaction = True
        status = {"compacted": True, "summary_created": False}

        # Prepare turns to summarize: all except the last KEEP_LAST
        to_summarize = self.turns[: len(self.turns) - KEEP_LAST]
        if not to_summarize:
            return status

        # Build conversation text
        conv_text = "\n".join([f"{t.role}: {t.content}" for t in to_summarize])
        turn_range = f"turns 1-{len(to_summarize)}"

        # Summarize via LLM
        summary_response = llm.invoke(
            f"""Summarize this conversation concisely (2-3 sentences max).
Focus on: facts learned, preferences stated, decisions made. Ignore pleasantries.

{conv_text}

Summary:"""
        )
        summary_text = summary_response.content

        # Store summary
        summary = ConversationSummary(
            summary=summary_text,
            turn_range=turn_range,
            token_count=estimate_tokens(conv_text),
        )
        self.summaries.append(summary)
        status["summary_created"] = True

        # Keep only recent turns
        self.turns = self.turns[-KEEP_LAST :]
        self.needs_compaction = False

        return status

    def get_context_for_llm(self) -> str:
        """Return conversation context within token budget."""
        context_parts = []

        # Add summaries
        for s in self.summaries:
            context_parts.append(f"[Summary: {s.turn_range}]\n{s.summary}\n")

        # Add recent turns
        for t in self.turns:
            context_parts.append(f"{t.role}: {t.content}\n")

        context = "".join(context_parts)

        # Truncate if needed
        remaining_budget = MAX_CONTEXT_TOKENS - estimate_tokens(context)
        if remaining_budget < 0:
            context = context[: MAX_CONTEXT_TOKENS * 4]

        return context


def should_remember(text: str) -> bool:
    """
    Write policy: decide if this text should go to long-term memory.
    Store preferences, facts, and decisions. Skip questions, pleasantries, and explanations.
    """
    # Patterns for memorable content
    facts = r"(is|are|was|were|called|named|known as|means|refers to)"
    preferences = r"(prefer|like|dislike|hate|love|want|need|need|avoid|refuse)"
    decisions = r"(decided|chose|will|plan to|should|must)"
    system_info = r"(my name|i am|i'm|i live|i work)"

    memorable_patterns = [facts, preferences, decisions, system_info]

    # Reject patterns
    questions = r"\?"
    pleasantries = r"(thanks|thank you|hello|hi|bye|goodbye|please|sorry)"

    if re.search(questions, text):
        return False
    if re.search(pleasantries, text, re.IGNORECASE):
        return False

    return any(re.search(p, text, re.IGNORECASE) for p in memorable_patterns)


def store_memory(text: str, memory_type: str = "fact"):
    """Store text in long-term memory with metadata."""
    if not should_remember(text):
        return

    stored = StoredMemory(
        text=text,
        memory_type=memory_type,
        timestamp=dt.datetime.now(),
        source="chat",
    )

    # Embed and store
    doc_id = hashlib.md5(text.encode()).hexdigest()[:12]
    collection.add(
        ids=[doc_id],
        documents=[text],
        metadatas=[
            {
                "type": memory_type,
                "timestamp": stored.timestamp.isoformat(),
                "source": stored.source,
            }
        ],
    )


def recall_memories(query: str, memory_type: Optional[str] = None) -> list[dict]:
    """
    Retrieve relevant memories from long-term storage.
    Returns list of {text, type, timestamp, similarity}.
    """
    try:
        # Query the collection
        where = {"type": {"$eq": memory_type}} if memory_type else None
        results = collection.query(
            query_texts=[query], n_results=TOP_K, where=where
        )

        if not results or not results["documents"] or not results["documents"][0]:
            return []

        # Format results
        memories = []
        for i, doc in enumerate(results["documents"][0]):
            if results["distances"] and i < len(results["distances"][0]):
                distance = results["distances"][0][i]
                similarity = 1 - distance  # cosine distance to similarity

                if similarity < MIN_SIMILARITY:
                    continue

                metadata = (
                    results["metadatas"][0][i] if results["metadatas"] else {}
                )
                memories.append(
                    {
                        "text": doc,
                        "type": metadata.get("type", "unknown"),
                        "timestamp": metadata.get("timestamp", ""),
                        "similarity": round(similarity, 3),
                    }
                )

        return memories
    except Exception as e:
        print(f"Recall error: {e}")
        return []


def get_memory_stats() -> dict:
    """Return memory usage statistics."""
    if not collection:
        return {"long_term_count": 0, "short_term_turns": 0}

    try:
        count = collection.count()
    except Exception:
        count = 0

    return {
        "long_term_memories": count,
        "collection_status": "ready" if collection else "not_initialized",
    }
