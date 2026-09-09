# backend/app/services/file_store.py
"""
Content-addressed blob store for the *original* uploaded file bytes
(docs/v2/ROADMAP.md Phase 7 -- "Filesystem/object storage").

`POST /api/upload` has always persisted the *extracted* text
(`Document.full_text` + `blocks`) but never the original file itself, in
any deployment profile. That's a real gap independent of the "collapsed
data layer" question -- there is no object-storage tier to substitute for,
so this is the tier: a plain directory on local disk, content-addressed by
SHA-256, needing no separate service (S3/MinIO/GCS). A cloud profile can
later point `FILE_STORAGE_DIR` at a mounted bucket without any code change.

Design notes:
- **Content-addressed**: the path is derived from the SHA-256 of the bytes,
  so re-uploading an identical file is a no-op write and two documents that
  happen to be the same file share one blob. Sharding by the first byte of
  the hash keeps any one directory from growing unbounded.
- **Fail-soft at write time**: extraction has already succeeded and the
  `Document` row is the primary artifact -- a storage error must not fail
  the upload. `store_bytes` returns `None` on failure (logged); the caller
  records "not stored" and the app keeps working.
- **Path traversal**: `sha256` is validated as 64 hex chars before it ever
  touches the filesystem, so a malformed/hostile id can't escape the root.
"""
from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import get_settings

logger = logging.getLogger("legalai.file_store")

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class StoredBlob:
    sha256: str
    size: int


def _root() -> Path:
    return Path(get_settings().FILE_STORAGE_DIR)


def _blob_path(sha256: str) -> Path:
    if not _SHA256_RE.match(sha256):
        raise ValueError(f"not a sha256 hex digest: {sha256!r}")
    root = _root()
    return root / sha256[:2] / sha256


def store_bytes(data: bytes) -> StoredBlob | None:
    """Persist `data` under its SHA-256. Idempotent (an existing identical
    blob is left untouched). Returns the blob descriptor, or None if the
    write failed for any reason (logged, never raised) -- see module docstring."""
    sha256 = hashlib.sha256(data).hexdigest()
    try:
        path = _blob_path(sha256)
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temp file in the same directory, then atomically
            # rename -- a crash mid-write never leaves a truncated blob at
            # the content-addressed path.
            tmp = path.with_suffix(".tmp")
            tmp.write_bytes(data)
            tmp.replace(path)
        return StoredBlob(sha256=sha256, size=len(data))
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("file_store: could not store blob %s (%s)", sha256[:12], e)
        return None


def load_bytes(sha256: str) -> bytes | None:
    """Return the stored blob, or None if it isn't present / can't be read."""
    try:
        path = _blob_path(sha256)
        if not path.is_file():
            return None
        return path.read_bytes()
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("file_store: could not load blob %s (%s)", str(sha256)[:12], e)
        return None


def exists(sha256: str) -> bool:
    try:
        return _blob_path(sha256).is_file()
    except ValueError:
        return False


def delete_bytes(sha256: str) -> bool:
    """Remove a blob. Returns True if a file was deleted. Best-effort: a
    missing blob or an unreadable directory is not an error."""
    try:
        path = _blob_path(sha256)
        if path.is_file():
            path.unlink()
            return True
        return False
    except Exception as e:  # pragma: no cover - defensive
        logger.warning("file_store: could not delete blob %s (%s)", str(sha256)[:12], e)
        return False
