"""
crawler.py - 旅游网页爬虫工具（crawl4ai 集成）

LLM 通过 Function Calling 自动调用，爬取携程/马蜂窝/大众点评等页面的
旅游攻略内容，自动清洗为 Markdown 并存入本地知识库。
"""
from __future__ import annotations

import asyncio
import json
import logging

from src.config import ToolConfig
from src.kb.store import upsert_kb_item, log_crawl_error, _extract_domain

logger = logging.getLogger(__name__)

# ----- Schema -----
CRAWL_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "crawl_travel_info",
        "description": (
            "爬取指定网页的旅游相关内容（景点攻略、美食推荐、住宿信息、交通指南等），"
            "自动清洗为结构化 Markdown 并存入本地知识库，供后续查询复用。"
            "适用网站：携程攻略、马蜂窝游记、小红书笔记、大众点评餐厅页等。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要爬取的网页 URL",
                },
                "category": {
                    "type": "string",
                    "enum": ["attraction", "food", "hotel", "transport", "general"],
                    "description": "内容类别",
                },
            },
            "required": ["url", "category"],
        },
    },
}


# ----- 执行入口 -----
def crawl_travel_info(
    url: str,
    category: str,
    config: ToolConfig | None = None,
) -> str:
    """爬取 URL，存入知识库，返回 JSON"""
    try:
        result = asyncio.run(_crawl_async(url, category))
        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("crawl_travel_info 异常")
        log_crawl_error(url, category, str(e))
        return json.dumps({"error": f"爬取失败：{e!s}"}, ensure_ascii=False)


async def _crawl_async(url: str, category: str) -> dict:
    from crawl4ai import AsyncWebCrawler, CacheMode

    async with AsyncWebCrawler(verbose=False) as crawler:
        result = await crawler.arun(url=url, cache_mode=CacheMode.BYPASS)

    if not result.success:
        err = result.error_message or "未知爬取错误"
        log_crawl_error(url, category, err)
        return {"error": f"爬取失败：{err}"}

    content_md = result.markdown or ""
    if not content_md.strip():
        log_crawl_error(url, category, "页面内容为空")
        return {"error": "页面内容为空，可能为纯 JS 渲染页面或需要登录"}

    title = _extract_title(content_md) or url.split("/")[-1] or "未命名"
    summary = content_md[:300].strip()

    kb_result = upsert_kb_item(
        url=url, category=category, title=title,
        content_md=content_md, summary=summary,
    )

    return {
        "url": url,
        "category": category,
        "title": title,
        "content_length": len(content_md),
        "summary": summary,
        "kb_id": kb_result["id"],
        "is_new": kb_result["is_new"],
        "source_domain": _extract_domain(url),
    }


def _extract_title(md: str) -> str:
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("# ") and len(s) > 2:
            return s[2:].strip()
    return ""
