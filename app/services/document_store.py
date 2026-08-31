"""Document metadata store — tracks uploaded files and their chunks."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.config import BASE_DIR

_META_FILE = BASE_DIR / "doc_metadata.json"


def _load() -> dict:
    if _META_FILE.exists():
        return json.loads(_META_FILE.read_text(encoding="utf-8"))
    return {}


def _save(data: dict) -> None:
    _META_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")


def add_document(
    filename: str,
    original_path: str,
    page_count: int,
    chunk_count: int,
) -> str:
    """Register a newly ingested document. Returns its ID."""
    data = _load()
    doc_id = uuid.uuid4().hex[:12]
    data[doc_id] = {
        "filename": filename,
        "original_path": original_path,
        "page_count": page_count,
        "chunk_count": chunk_count,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    }
    _save(data)
    return doc_id


def list_documents() -> list[dict]:
    """Return all documents with their IDs."""
    data = _load()
    return [{"id": k, **v} for k, v in data.items()]


def get_document(doc_id: str) -> Optional[dict]:
    data = _load()
    entry = data.get(doc_id)
    if entry:
        return {"id": doc_id, **entry}
    return None


def delete_document(doc_id: str) -> bool:
    data = _load()
    if doc_id in data:
        del data[doc_id]
        _save(data)
        return True
    return False
