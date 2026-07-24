"""测试 src.kb 知识库模块"""
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.kb import get_connection, get_db_path, DB_PATH
from src.kb.store import (
    upsert_kb_item, search_kb, get_kb_stats, log_crawl_error,
    _extract_domain, _compute_hash,
)


@pytest.fixture(autouse=True)
def _clean_kb():
    """每个测试前清空知识库，避免状态污染"""
    conn = get_connection()
    conn.execute("DELETE FROM kb_items")
    conn.execute("DELETE FROM kb_crawl_log")
    # 重建 FTS 索引
    conn.execute("INSERT INTO kb_fts(kb_fts) VALUES('rebuild')")
    conn.commit()
    conn.close()


class TestDatabase:
    def test_get_connection_returns_valid(self):
        conn = get_connection()
        assert conn is not None
        conn.close()

    def test_db_path_exists(self):
        conn = get_connection()
        conn.close()
        assert os.path.exists(DB_PATH)

    def test_get_db_path(self):
        path = get_db_path()
        assert path.endswith("travel_kb.db")


class TestStoreCRUD:
    def test_upsert_new_item(self):
        result = upsert_kb_item(
            url="https://example.com/test",
            category="general",
            title="Test Page",
            content_md="This is a test page content.",
            summary="test summary",
        )
        assert result["is_new"] is True
        assert "id" in result

    def test_upsert_duplicate_same_hash(self):
        content = "Duplicate test content."
        r1 = upsert_kb_item("https://a.com", "general", "A", content)
        r2 = upsert_kb_item("https://b.com", "general", "B", content)
        assert r1["is_new"] is True
        assert r2["is_new"] is False
        assert r1["id"] == r2["id"]

    def test_search_finds_inserted(self):
        content = "Guangzhou travel guide with 白云山 and 珠江"
        upsert_kb_item(
            url="https://travel.com/gz",
            category="attraction",
            title="Guangzhou Guide",
            content_md=content,
            summary="Guide to Guangzhou",
        )
        results = search_kb("白云山", limit=3)
        assert len(results) >= 1
        titles = [r["title"] for r in results]
        assert any("Guangzhou" in t for t in titles)

    def test_search_by_category(self):
        upsert_kb_item(
            url="https://food.com/gz",
            category="food",
            title="GZ Food",
            content_md="Delicious 广州 food guide.",
        )
        results = search_kb("广州", category="food", limit=3)
        for r in results:
            assert r["category"] == "food"

    def test_search_no_results(self):
        results = search_kb("nonexistent_xyz_12345", limit=5)
        assert results == []

    def test_get_kb_stats(self):
        stats = get_kb_stats()
        assert "total_items" in stats
        assert "by_category" in stats
        assert stats["total_items"] >= 0

    def test_log_crawl_error(self):
        log_crawl_error("https://err.com", "general", "Test error")
        # Should not raise


class TestHelpers:
    def test_extract_domain(self):
        assert _extract_domain("https://www.example.com/path") == "www.example.com"

    def test_compute_hash_deterministic(self):
        h1 = _compute_hash("hello")
        h2 = _compute_hash("hello")
        assert h1 == h2
        assert len(h1) == 32
