"""
Centralized configuration module.

Loads environment variables ONCE from .env using python-dotenv and
exposes them as class attributes on `Config`.  Every other module should
import `Config` instead of calling os.getenv / os.environ.get directly.
"""

import os
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

# Resolve the project root (structured-extract/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load .env exactly once at import time
load_dotenv(PROJECT_ROOT / ".env", override=True)
load_dotenv(find_dotenv(), override=True)


class Config:
    """Single source of truth for all environment-driven configuration."""

    PROJECT_ROOT: Path = PROJECT_ROOT

    # ── Groq settings ──────────────────────────────────────────────
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    # ── Anthropic settings (used by eval/generate_samples) ────────
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
