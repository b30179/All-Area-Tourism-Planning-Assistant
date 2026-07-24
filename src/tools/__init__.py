"""
tools/__init__.py - 工具注册表

统一注册所有可被 LLM 调用的工具：
- tool_schema:  OpenAI Function Calling 格式的 JSON Schema
- tool_function: 实际执行的 Python 函数
- tool_executor: 包装函数，处理参数解析与异常
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict

from src.config import ToolConfig
from src.tools.crawler import CRAWL_TOOL_SCHEMA, crawl_travel_info
from src.tools.poi import POI_TOOL_SCHEMA, search_poi
from src.tools.search_kb import SEARCH_KB_SCHEMA, search_knowledge_base
from src.tools.weather import WEATHER_TOOL_SCHEMA, get_weather

logger = logging.getLogger(__name__)


# ============================================================
# 工具执行器统一包装
# ============================================================
def _make_executor(
    func: Callable[..., str], required_args: list, optional_args: dict | None = None
) -> Callable[..., str]:
    """
    为工具函数创建统一执行器：解析参数 + 异常捕获 + 注入 config

    :param func: 原始工具函数
    :param required_args: 必填参数名列表
    :param optional_args: 可选参数默认值
    :return: 包装后的执行器
    """
    optional_args = optional_args or {}

    def executor(arguments_json: str, config: ToolConfig) -> str:
        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError as e:
            return json.dumps(
                {"error": f"参数解析失败：{e!s}"}, ensure_ascii=False
            )

        # 构造调用参数
        call_kwargs = {"config": config}
        for arg in required_args:
            if arg not in args:
                return json.dumps(
                    {"error": f"缺少必填参数：{arg}"}, ensure_ascii=False
                )
            call_kwargs[arg] = args[arg]
        for arg, default in optional_args.items():
            call_kwargs[arg] = args.get(arg, default)

        try:
            return func(**call_kwargs)
        except Exception as e:
            logger.exception("工具 %s 执行失败", func.__name__)
            return json.dumps(
                {"error": f"工具执行异常：{e!s}"}, ensure_ascii=False
            )

    return executor


# ============================================================
# 工具注册表
# ============================================================
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "get_weather": {
        "schema": WEATHER_TOOL_SCHEMA,
        "executor": _make_executor(
            func=get_weather,
            required_args=["city"],
        ),
    },
    "search_poi": {
        "schema": POI_TOOL_SCHEMA,
        "executor": _make_executor(
            func=search_poi,
            required_args=["query", "region"],
            optional_args={"page_size": 10},
        ),
    },
    "crawl_travel_info": {
        "schema": CRAWL_TOOL_SCHEMA,
        "executor": _make_executor(
            func=crawl_travel_info,
            required_args=["url", "category"],
        ),
    },
    "search_knowledge_base": {
        "schema": SEARCH_KB_SCHEMA,
        "executor": _make_executor(
            func=search_knowledge_base,
            required_args=["query"],
            optional_args={"category": None, "limit": 5},
        ),
    },
}


def get_all_tool_schemas() -> list:
    """获取所有工具的 OpenAI Function Calling Schema 列表"""
    return [tool["schema"] for tool in TOOL_REGISTRY.values()]


def get_tool_executor(name: str) -> Callable[..., str] | None:
    """根据工具名获取执行器"""
    tool = TOOL_REGISTRY.get(name)
    return tool["executor"] if tool else None


__all__ = [
    "TOOL_REGISTRY",
    "get_all_tool_schemas",
    "get_tool_executor",
    "WEATHER_TOOL_SCHEMA",
    "POI_TOOL_SCHEMA",
    "CRAWL_TOOL_SCHEMA",
    "SEARCH_KB_SCHEMA",
    "get_weather",
    "search_poi",
    "crawl_travel_info",
    "search_knowledge_base",
]