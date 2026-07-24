"""
search_kb.py - 知识库检索工具

LLM 通过 Function Calling 搜索本地已爬取的旅游信息。
优先使用此工具查缓存；无结果时再调用 crawl_travel_info 爬新内容。
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from src.config import ToolConfig
from src.kb.store import search_kb as search_kb_store, get_kb_stats

logger = logging.getLogger(__name__)

# ----- Schema -----
SEARCH_KB_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_knowledge_base",
        "description": (
            "搜索本地知识库中已爬取的旅游信息（景点攻略、美食推荐、住宿、交通等）。"
            "优先使用此工具查缓存；若无结果，可调用 crawl_travel_info 爬取相关网页。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "搜索关键词，如'广州塔'、'火锅'、'快捷酒店'",
                },
                "category": {
                    "type": "string",
                    "enum": ["attraction", "food", "hotel", "transport", "general"],
                    "description": "限定内容类别（可选，不填则搜索全部）",
                },
                "limit": {
                    "type": "integer",
                    "description": "返回结果数量，默认 5，最多 10",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
}


# ----- 执行入口 -----
def search_knowledge_base(
    query: str,
    category: Optional[str] = None,
    limit: int = 5,
    config: ToolConfig | None = None,
) -> str:
    """搜索本地知识库，返回 JSON"""
    try:
        results = search_kb_store(
            query=query,
            category=category or None,
            limit=min(max(limit, 1), 10),
        )

        if not results:
            stats = get_kb_stats()
            return json.dumps(
                {
                    "query": query,
                    "found": False,
                    "message": "知识库中暂无相关内容",
                    "kb_stats": stats,
                    "suggestion": "你可以调用 crawl_travel_info 爬取相关网页来丰富知识库",
                },
                ensure_ascii=False,
            )

        items = []
        for r in results:
            items.append(
                {
                    "id": r["id"],
                    "url": r["url"],
                    "category": r["category"],
                    "title": r["title"],
                    "summary": r.get("summary", "")[:200],
                    "source": r.get("source_domain", ""),
                    "crawled_at": r.get("crawled_at", ""),
                }
            )

        return json.dumps(
            {
                "query": query,
                "found": True,
                "count": len(items),
                "results": items,
                "hint": "如需完整攻略内容，请根据 title 和 url 引用对应条目",
            },
            ensure_ascii=False,
        )

    except Exception as e:
        logger.exception("search_knowledge_base 异常")
        return json.dumps({"error": f"知识库搜索失败：{e!s}"}, ensure_ascii=False)
