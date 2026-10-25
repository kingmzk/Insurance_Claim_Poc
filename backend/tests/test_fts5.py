import pytest
from backend.app.db.database import init_db, search_policy_clauses

def test_fts5_indexing_and_search():
    init_db()
    
    # Test collision clause retrieval
    results = search_policy_clauses("collision damage deductible", policy_no="POL-AUTO-99201")
    assert len(results) > 0
    section_titles = [r["section_title"] for r in results]
    assert any("Collision" in title for title in section_titles)
    assert any(r["page_number"] > 0 for r in results)

def test_fts5_exclusion_search():
    init_db()
    
    # Test racing exclusion clause retrieval
    results = search_policy_clauses("racing speed contest track", policy_no="POL-AUTO-99201")
    assert len(results) > 0
    assert any("Exclusions" in r["section_title"] for r in results)

def test_fts5_empty_query():
    init_db()
    results = search_policy_clauses("xyznonexistentterm12345")
    assert results == []
