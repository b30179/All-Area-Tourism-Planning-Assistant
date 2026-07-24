"""
crawler.py - 旅游网页爬虫工具（crawl4ai 集成）

LLM 通过 Function Calling 自动调用，支持两种策略：
- static: 纯 HTTP 请求（快，1-3s），适合静态网页
- js: Playwright 渲染（慢，5-15s），适合 SPA/JS 页面（马蜂窝/携程/小红书）

建议流程：POI 检索成功 → 用 POI 数据中的景点名构造搜索 URL 爬取详情
"""
from __future__ import annotations

import asyncio
import json
import logging
from urllib.parse import quote

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
            "适用网站：马蜂窝、携程、穷游、百度百科、大众点评等。"
            "注意：POI 检索成功后也应调用此工具爬取景点的详细攻略和用户评价，"
            "以获取比 POI 更丰富的内容（开放时间、门票、游玩攻略、用户点评等）。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "要爬取的网页 URL。可从 POI 结果中获取景点名拼接：如 'https://www.mafengwo.cn/search/q.php?q=广州塔'",
                },
                "category": {
                    "type": "string",
                    "enum": ["attraction", "food", "hotel", "transport", "general"],
                    "description": "内容类别",
                },
                "strategy": {
                    "type": "string",
                    "enum": ["static", "js"],
                    "description": "爬取策略：static=纯HTTP请求（快，适合百科/穷游）；js=Playwright渲染（慢，适合马蜂窝/携程等SPA页面）。默认 static，static 失败时自动重试 js",
                    "default": "static",
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
    strategy: str = "static",
    config: ToolConfig | None = None,
) -> str:
    """爬取 URL，存入知识库。static 失败自动回退 js。"""
    try:
        # 先尝试 static
        if strategy in ("static", "auto"):
            result = asyncio.run(_crawl_async(url, category, use_js=False))
            if "error" not in result:
                return json.dumps(result, ensure_ascii=False)
            static_err = result.get("error", "")
            logger.info("static 爬取失败（%s），回退 js 模式", static_err)
        else:
            static_err = ""

        # static 失败或直接指定 js → 用 Playwright 渲染
        if strategy in ("js", "auto") or static_err:
            result = asyncio.run(_crawl_async(url, category, use_js=True))
            if "error" not in result:
                result["strategy"] = "js"
                result["note"] = "static 模式失败，使用 JS 渲染成功"
                return json.dumps(result, ensure_ascii=False)
            return json.dumps(result, ensure_ascii=False)

        return json.dumps(result, ensure_ascii=False)
    except Exception as e:
        logger.exception("crawl_travel_info 异常")
        log_crawl_error(url, category, str(e))
        return json.dumps({"error": f"爬取失败：{e!s}"}, ensure_ascii=False)


async def _crawl_async(url: str, category: str, use_js: bool = False) -> dict:
    from crawl4ai import AsyncWebCrawler, CacheMode

    kwargs = {"verbose": False}
    if use_js:
        kwargs["headless"] = True

    async with AsyncWebCrawler(**kwargs) as crawler:
        arun_kwargs = {
            "url": url,
            "cache_mode": CacheMode.BYPASS,
        }
        if use_js:
            # JS 渲染模式：等待页面加载 + 额外等待 3s 让 AJAX 完成
            arun_kwargs["magic"] = True
            arun_kwargs["wait_for"] = "timeout:5000"

        result = await crawler.arun(**arun_kwargs)

    if not result.success:
        err = result.error_message or "未知爬取错误"
        log_crawl_error(url, category, err)
        strategy_tag = " (js)" if use_js else ""
        return {"error": f"爬取失败{strategy_tag}：{err}"}

    content_md = result.markdown or ""
    if not content_md.strip() or len(content_md) < 100:
        reason = "页面内容为空" if not content_md.strip() else "提取内容过少（<100字符），可能为纯 JS 渲染页面"
        log_crawl_error(url, category, reason)
        return {"error": f"爬取失败：{reason}，请尝试 strategy=js"}

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
        "strategy": "js" if use_js else "static",
    }


def _extract_title(md: str) -> str:
    for line in md.split("\n"):
        s = line.strip()
        if s.startswith("# ") and len(s) > 2:
            return s[2:].strip()
    return ""
