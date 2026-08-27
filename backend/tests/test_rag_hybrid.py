"""
Tests for the hybrid RAG layer: BM25 (real, no mocking needed -- pure
Python, no network) and the citation validator. Dense retrieval (Gemini
embeddings) is exercised indirectly through the contextualize route test in
test_routes.py, where embed_content is mocked.
"""
from app.services.rag.bm25 import BM25Index
from app.services.rag.citation_validator import find_invalid_citations
from app.services.rag.corpus import LEGAL_KNOWLEDGE_BASE, LegalKnowledgeEntry


def test_corpus_entries_have_required_fields():
    assert len(LEGAL_KNOWLEDGE_BASE) > 10
    for entry in LEGAL_KNOWLEDGE_BASE:
        assert entry.text
        assert entry.topic


def test_corpus_does_not_fabricate_citations_for_every_entry():
    # A meaningful chunk of entries must be uncited (citation=None) -- if
    # every single entry had a citation, that would suggest we invented
    # sources for general-principle statements that don't have one.
    uncited = [e for e in LEGAL_KNOWLEDGE_BASE if e.citation is None]
    assert len(uncited) >= 10


def test_bm25_finds_keyword_matching_entry():
    index = BM25Index(LEGAL_KNOWLEDGE_BASE)
    hits = index.search("security deposit California", k=3)

    assert hits
    top_entry, _score = hits[0]
    assert "security deposit" in top_entry.text.lower()


def test_bm25_returns_nothing_for_a_query_with_no_word_overlap_at_all():
    # No stopword filtering is applied (see bm25.py), so a query sharing even
    # common words like "to"/"and" with the corpus gets tiny nonzero scores --
    # that's real BM25 behavior, not a bug. Use nonsense tokens that share no
    # words with the corpus at all to test the true no-overlap case.
    index = BM25Index(LEGAL_KNOWLEDGE_BASE)
    hits = index.search("qwzxjklm vprnbfgh zzyqxwv", k=3)
    assert hits == []


def test_bm25_empty_corpus_is_safe():
    index = BM25Index([])
    assert index.search("anything", k=3) == []


def test_find_invalid_citations_flags_out_of_range_numbers():
    text = "This is grounded [1] and also [5], which was never given."
    assert find_invalid_citations(text, num_hints=2) == [5]


def test_find_invalid_citations_empty_when_all_valid():
    text = "Grounded in [1] and [2]."
    assert find_invalid_citations(text, num_hints=2) == []


def test_find_invalid_citations_empty_when_no_citations_present():
    assert find_invalid_citations("No citations here.", num_hints=3) == []
