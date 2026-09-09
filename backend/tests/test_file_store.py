"""
Original uploaded file blob store (Phase 7, app/services/file_store.py) and
the GET /api/v2/documents/{id}/original download route.
"""
from __future__ import annotations

import hashlib

import pytest

from app.services import file_store


@pytest.fixture(autouse=True)
def _isolate_storage(tmp_path, monkeypatch):
    """Each test gets its own empty blob-store directory."""
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.setenv("FILE_STORAGE_DIR", str(tmp_path / "blobs"))
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_store_and_load_round_trips():
    data = b"the quick brown fox" * 100
    blob = file_store.store_bytes(data)
    assert blob is not None
    assert blob.sha256 == hashlib.sha256(data).hexdigest()
    assert blob.size == len(data)
    assert file_store.exists(blob.sha256)
    assert file_store.load_bytes(blob.sha256) == data


def test_store_is_content_addressed_and_idempotent():
    data = b"identical bytes"
    a = file_store.store_bytes(data)
    b = file_store.store_bytes(data)
    assert a is not None and b is not None
    assert a.sha256 == b.sha256


def test_load_missing_blob_returns_none():
    assert file_store.load_bytes("0" * 64) is None
    assert file_store.exists("0" * 64) is False


def test_malformed_sha_never_touches_the_filesystem():
    assert file_store.load_bytes("../../etc/passwd") is None
    assert file_store.exists("not-a-hash") is False


def test_delete_removes_the_blob():
    blob = file_store.store_bytes(b"delete me")
    assert blob is not None
    assert file_store.delete_bytes(blob.sha256) is True
    assert file_store.exists(blob.sha256) is False
    assert file_store.delete_bytes(blob.sha256) is False  # already gone, not an error


def test_store_failure_is_fail_soft(monkeypatch):
    def boom(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(file_store.Path, "write_bytes", boom, raising=True)
    assert file_store.store_bytes(b"anything") is None


# ---- route integration ----

CONTRACT = b"This Agreement is between ABC Corp and Jane Doe. The Tenant shall pay rent."


def test_upload_persists_original_and_it_downloads_back(client):
    resp = client.post(
        "/api/upload",
        files={"file": ("contract.txt", CONTRACT, "text/plain")},
    )
    assert resp.status_code == 200
    doc_id = resp.json()["document_id"]

    meta = client.get(f"/api/v2/documents/{doc_id}").json()
    assert meta["original_available"] is True
    assert meta["original_size"] == len(CONTRACT)

    dl = client.get(f"/api/v2/documents/{doc_id}/original")
    assert dl.status_code == 200
    assert dl.content == CONTRACT
    assert "attachment" in dl.headers["content-disposition"]
    assert "contract.txt" in dl.headers["content-disposition"]


def test_download_404_when_never_stored(client, db_session):
    from app.db_models import Document

    doc = Document(org_id=1, filename="x.txt", content_type="text/plain",
                   full_text="hi", blocks=[])
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    assert client.get(f"/api/v2/documents/{doc.id}/original").status_code == 404


def test_download_404_when_blob_missing_from_store(client, db_session):
    from app.db_models import Document

    doc = Document(org_id=1, filename="x.txt", content_type="text/plain",
                   full_text="hi", blocks=[], original_sha256="a" * 64, original_size=2)
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)

    resp = client.get(f"/api/v2/documents/{doc.id}/original")
    assert resp.status_code == 404
    assert "missing" in resp.json()["detail"].lower()
