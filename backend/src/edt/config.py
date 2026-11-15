"""Configuration, read once from environment variables (see ARCHITECTURE.md section 8)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# backend/src/edt/config.py -> repository root is three levels above the package dir
REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO_ROOT / "contracts" / "trend-detective-api.openapi.yaml"


@dataclass(frozen=True)
class Settings:
    data_root: Path
    session_store: str
    allowed_origins: tuple[str, ...]
    guide_llm: str

    @property
    def cube_dir(self) -> Path:
        return self.data_root / "cube"

    @property
    def maps_dir(self) -> Path:
        return self.data_root / "maps"

    @property
    def raw_dir(self) -> Path:
        return self.data_root / "raw"

    @property
    def manifest_path(self) -> Path:
        return self.data_root / "manifest.json"

    @property
    def sessions_path(self) -> Path:
        return self.data_root / "sessions.sqlite"


def load_settings() -> Settings:
    data_root = os.environ.get("DATA_ROOT")
    if not data_root:
        raise RuntimeError("DATA_ROOT is not set. Use the absolute path of the data folder.")
    path = Path(data_root).expanduser()
    if not path.is_absolute():
        raise RuntimeError("DATA_ROOT must be an absolute path.")
    origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
    return Settings(
        data_root=path,
        session_store=os.environ.get("SESSION_STORE", "sqlite"),
        allowed_origins=tuple(o.strip() for o in origins.split(",") if o.strip()),
        guide_llm=os.environ.get("GUIDE_LLM", "off"),
    )
