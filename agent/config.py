"""Agent runtime configuration — model id and paths live here, not hardcoded in graph.py."""

from __future__ import annotations

import os
from pathlib import Path

# Gemini via GOOGLE_API_KEY; override with AGENT_MODEL for experiments.
# Verified against LangChain + Deep Agents docs (2026-06): gemini-2.5-flash on Developer API.
MODEL: str = os.environ.get("AGENT_MODEL", "google_genai:gemini-2.5-flash")

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = Path(__file__).resolve().parent / "knowledge"
SYSTEM_PROMPT_PATH = REPO_ROOT / "prompts" / "system_prompt.md"
BRIEFINGS_DIR = KNOWLEDGE_ROOT / "briefings"

# Dev persistence: MemorySaver in-process; set CHECKPOINT_SQLITE for durable local threads.
CHECKPOINT_SQLITE = os.environ.get("CHECKPOINT_SQLITE", str(REPO_ROOT / "data" / "agent_checkpoints.db"))
