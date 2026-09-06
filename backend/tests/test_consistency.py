"""
The Cross-Document Consistency embedding-similarity baseline
(app/services/consistency.py, docs/v2/ROADMAP.md Phase 8). Mocks
embed_content with controllable per-text vectors so the similarity
threshold and the deontic-conflict check are actually exercised, not just
"the route doesn't crash" (see tests/test_v2_routes.py for that half).
"""
from types import SimpleNamespace

from app.db_models import Document
from app.services.consistency import find_cross_document_consistency

# Two clauses with near-identical vectors (similar), a third orthogonal one
# (dissimilar) -- lets a test assert both "found" and "correctly not found".
_VECTORS = {
    "near_a": [1.0, 0.0, 0.0, 0.0],
    "near_b": [0.99, 0.05, 0.0, 0.0],  # cosine ~0.9987 with near_a -- above threshold
    "far": [0.0, 0.0, 0.0, 1.0],  # orthogonal to near_a -- cosine 0.0
}


def _doc(id_: int, filename: str, full_text: str) -> Document:
    d = Document(filename=filename, full_text=full_text, org_id=1)
    d.id = id_
    return d


def _fake_embed(vector_for_text):
    def fn(contents, **kwargs):
        vecs = [SimpleNamespace(values=vector_for_text(text)) for text in contents]
        return SimpleNamespace(embeddings=vecs)
    return fn


def test_flags_a_similar_conflicting_pair_across_documents(monkeypatch):
    # obligation in doc A, prohibition on the near-identical-embedding clause in doc B
    doc_a = _doc(1, "a.txt", "The Vendor shall deliver the goods within 10 days.")
    doc_b = _doc(2, "b.txt", "The Vendor shall not deliver the goods within 10 days.")

    def vector_for_text(text: str):
        return _VECTORS["near_a"] if "shall not" not in text else _VECTORS["near_b"]

    monkeypatch.setattr("app.services.consistency.embed_content", _fake_embed(vector_for_text))

    findings = find_cross_document_consistency(doc_a, [doc_b])

    assert len(findings) == 1
    f = findings[0]
    assert f.document_id == 1
    assert f.other_document_id == 2
    assert f.similarity >= 0.9
    assert f.modality == "obligation"
    assert f.other_modality == "prohibition"
    assert f.is_conflict is True


def test_does_not_flag_dissimilar_clauses(monkeypatch):
    doc_a = _doc(1, "a.txt", "The Vendor shall deliver the goods within 10 days.")
    doc_b = _doc(2, "b.txt", "The Tenant may sublease the premises with written consent.")

    def vector_for_text(text: str):
        return _VECTORS["near_a"] if "Vendor" in text else _VECTORS["far"]

    monkeypatch.setattr("app.services.consistency.embed_content", _fake_embed(vector_for_text))

    findings = find_cross_document_consistency(doc_a, [doc_b])

    assert findings == []


def test_similar_same_modality_is_flagged_but_not_a_conflict(monkeypatch):
    doc_a = _doc(1, "a.txt", "The Vendor shall deliver the goods within 10 days.")
    doc_b = _doc(2, "b.txt", "The Vendor shall deliver the goods within fourteen days.")

    monkeypatch.setattr(
        "app.services.consistency.embed_content",
        _fake_embed(lambda text: _VECTORS["near_a"]),
    )

    findings = find_cross_document_consistency(doc_a, [doc_b])

    assert len(findings) == 1
    assert findings[0].modality == "obligation"
    assert findings[0].other_modality == "obligation"
    assert findings[0].is_conflict is False


def test_no_deontic_tags_produces_no_findings(monkeypatch):
    doc_a = _doc(1, "a.txt", "This is a recital with no obligations at all.")
    doc_b = _doc(2, "b.txt", "Another plain descriptive sentence, also no modality.")

    called = {"n": 0}

    def fn(contents, **kwargs):
        called["n"] += 1
        return SimpleNamespace(embeddings=[SimpleNamespace(values=_VECTORS["near_a"]) for _ in contents])

    monkeypatch.setattr("app.services.consistency.embed_content", fn)

    findings = find_cross_document_consistency(doc_a, [doc_b])

    assert findings == []
    # short-circuits before ever calling embed_content -- no deontic-tagged clauses to embed
    assert called["n"] == 0


def test_respects_max_other_documents(monkeypatch):
    import app.services.consistency as consistency_module

    monkeypatch.setattr(consistency_module, "MAX_OTHER_DOCUMENTS", 1)
    doc_a = _doc(1, "a.txt", "The Vendor shall deliver the goods within 10 days.")
    doc_b = _doc(2, "b.txt", "The Vendor shall deliver the goods within 10 days.")
    doc_c = _doc(3, "c.txt", "The Vendor shall deliver the goods within 10 days.")

    monkeypatch.setattr(
        "app.services.consistency.embed_content",
        _fake_embed(lambda text: _VECTORS["near_a"]),
    )

    findings = find_cross_document_consistency(doc_a, [doc_b, doc_c])

    assert {f.other_document_id for f in findings} == {2}
