"""Database connection settings.

The connection string comes from the DATABASE_URL environment variable, or from
the project's .env file (gitignored; see .env.example).
"""

from __future__ import annotations

import os
from pathlib import Path

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"


class DatabaseNotConfiguredError(RuntimeError):
    pass


def _read_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                values[key.strip()] = value.strip()
    return values


def database_url() -> str:
    url = os.environ.get("DATABASE_URL") or _read_env_file(ENV_FILE).get("DATABASE_URL")
    if not url:
        raise DatabaseNotConfiguredError("Set DATABASE_URL (see .env.example)")
    return url


def connect(url: str | None = None, **kwargs: object) -> psycopg.Connection:
    return psycopg.connect(url or database_url(), **kwargs)
