from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"
MEMORY_DIR = ROOT / "memory"

load_dotenv(ROOT / ".env")


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass
class Settings:
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    writer_model: str = field(default_factory=lambda: os.getenv("WRITER_MODEL", "qwen/qwen3.8-27b"))
    judge_model: str = field(default_factory=lambda: os.getenv("JUDGE_MODEL", "openai/gpt-oss-120b"))
    reflector_model: str = field(default_factory=lambda: os.getenv("REFLECTOR_MODEL", "qwen/qwen3.8-27b"))
    writer_tpm: int = field(default_factory=lambda: _int("WRITER_TPM", 8000))
    judge_tpm: int = field(default_factory=lambda: _int("JUDGE_TPM", 8000))
    max_retries: int = field(default_factory=lambda: _int("MAX_RETRIES", 2))
    writer_temperature: float = 0.6
    judge_temperature: float = 0.0
    # Groq counts prompt + max_tokens against the per-minute limit, so keep these modest.
    writer_max_tokens: int = field(default_factory=lambda: _int("WRITER_MAX_TOKENS", 3000))
    judge_max_tokens: int = field(default_factory=lambda: _int("JUDGE_MAX_TOKENS", 2500))
    db_path: Path = field(default_factory=lambda: Path(os.getenv("LESSONFORGE_DB_PATH", MEMORY_DIR / "lessonforge.db")))
    outputs_dir: Path = field(default_factory=lambda: Path(os.getenv("LESSONFORGE_OUTPUTS_DIR", OUTPUTS_DIR)))
    data_dir: Path = DATA_DIR
    # Reflection: a check must fail in this many distinct runs before a rule is learned.
    reflection_min_runs: int = 2
    max_active_rules: int = 12
