"""Path safety helpers"""
from pathlib import Path
import uuid

from app.config import settings


def _normalize_uuid(value: str) -> str:
    """Normalize and validate UUID string."""
    return str(uuid.UUID(str(value)))


def resolve_research_path(session_id: str, filename: str) -> Path:
    """Resolve research output path safely under outputs/research."""
    base_dir = (Path(settings.OUTPUTS_DIR) / "research").resolve()
    session_id = _normalize_uuid(session_id)
    target = (base_dir / session_id / filename).resolve()
    target.relative_to(base_dir)
    return target
