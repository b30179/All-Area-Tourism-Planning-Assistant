"""测试新增的爬虫和知识库检索工具"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.tools.crawler import CRAWL_TOOL_SCHEMA, _extract_title
from src.tools.search_kb import SEARCH_KB_SCHEMA, search_knowledge_base


class TestCrawlerSchema:
    def test_schema_name(self):
        assert CRAWL_TOOL_SCHEMA["function"]["name"] == "crawl_travel_info"

    def test_required_params(self):
        params = CRAWL_TOOL_SCHEMA["function"]["parameters"]
        assert "url" in params["required"]
        assert "category" in params["required"]


class TestSearchKBSchema:
    def test_schema_name(self):
        assert SEARCH_KB_SCHEMA["function"]["name"] == "search_knowledge_base"

    def test_required_params(self):
        params = SEARCH_KB_SCHEMA["function"]["parameters"]
        assert "query" in params["required"]


class TestExtractTitle:
    def test_h1_title(self):
        md = "# Guangzhou Travel Guide\n\nSome content."
        assert _extract_title(md) == "Guangzhou Travel Guide"

    def test_no_title(self):
        md = "No heading here\nJust content."
        assert _extract_title(md) == ""

    def test_multiple_headings(self):
        md = "# First\n## Second\n# Third"
        assert _extract_title(md) == "First"


class TestSearchKB:
    def test_search_empty_db(self):
        result = search_knowledge_base("gz_search_test")
        data = json.loads(result)
        assert data["found"] is False
        assert "kb_stats" in data

    def test_search_with_category(self):
        result = search_knowledge_base("test", category="attraction", limit=3)
        data = json.loads(result)
        assert "found" in data
