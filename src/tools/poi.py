"""
poi.py - POI 兴趣点检索工具

双源策略：
  1. 优先调用腾讯位置服务（更稳定、数据更新及时）
  2. 失败时自动回退到百度地图

支持关键词检索：景点、美食、酒店、商场等
返回结构化 POI 列表（名称、地址、电话、坐标）
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import requests

from src.config import BAIDU_PLACE_URL, TENCENT_PLACE_URL, ToolConfig
from src.kb.store import upsert_kb_item

logger = logging.getLogger(__name__)


# ============================================================
# OpenAI Function Calling Schema
# ============================================================
POI_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_poi",
        "description": (
            "在指定城市检索某类别的兴趣点（POI），如景点、美食、酒店、商场等。"
            "采用双源策略：优先腾讯位置服务，失败时自动回退百度地图。"
            "返回结构化的 POI 列表，包含名称、地址、电话、坐标等。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "检索关键词，例如：'景点'、'美食'、'酒店'、'博物馆'",
                },
                "region": {
                    "type": "string",
                    "description": "城市名称（限定检索范围），例如：'广州'、'北京'",
                },
                "page_size": {
                    "type": "integer",
                    "description": "返回结果数量，默认 10，范围 1-20",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 20,
                },
            },
            "required": ["query", "region"],
        },
    },
}


# ============================================================
# 工具执行函数（被 LLM 通过 Tool Calling 调用）
# ============================================================
def search_poi(
    query: str,
    region: str,
    page_size: int = 10,
    config: ToolConfig | None = None,
) -> str:
    """
    POI 兴趣点检索：腾讯位置服务（优先）→ 百度地图（兜底）

    :param query: 检索关键词
    :param region: 城市名（如"广州"）
    :param page_size: 返回数量
    :param config: 工具配置（含 API Key）
    :return: JSON 字符串
    """
    cfg = config or ToolConfig()
    timeout = cfg.http_timeout

    # 用于收集详细的失败原因
    tencent_reason = None
    baidu_reason = None

    # 1) 优先腾讯位置服务
    if cfg.tencent_lbs_key:
        try:
            result = _search_tencent(
                query=query,
                region=region,
                page_size=page_size,
                api_key=cfg.tencent_lbs_key,
                timeout=timeout,
            )
            if result is not None:
                _save_pois_to_kb(result, query)
                return json.dumps(result, ensure_ascii=False)
            tencent_reason = "腾讯地图返回空结果（可能该区域无匹配 POI）"
            logger.warning("腾讯 POI 检索返回空，回退到百度地图")
        except Exception as e:
            tencent_reason = f"腾讯地图调用异常：{e!s}"
            logger.warning("腾讯 POI 检索异常: %s，回退到百度地图", e)
    else:
        tencent_reason = "未配置 TENCENT_LBS_KEY"

    # 2) 兜底百度地图
    if cfg.baidu_map_ak:
        try:
            result = _search_baidu(
                query=query,
                region=region,
                page_size=page_size,
                ak=cfg.baidu_map_ak,
                timeout=timeout,
            )
            if result is not None:
                _save_pois_to_kb(result, query)
                return json.dumps(result, ensure_ascii=False)
            baidu_reason = "百度地图返回空结果"
            logger.warning("百度 POI 检索返回空")
        except Exception as e:
            baidu_reason = f"百度地图调用异常：{e!s}"
            logger.error("百度 POI 检索异常: %s", e)
    else:
        baidu_reason = "未配置 BAIDU_MAP_AK"

    # 3) 两家都失败 — 给出详细原因
    error_msg = []
    if tencent_reason:
        error_msg.append(f"腾讯：{tencent_reason}")
    if baidu_reason:
        error_msg.append(f"百度：{baidu_reason}")

    return json.dumps(
        {"error": "POI 检索失败：" + "；".join(error_msg)},
        ensure_ascii=False,
    )


# ============================================================
# 腾讯位置服务
# ============================================================
def _search_tencent(
    query: str,
    region: str,
    page_size: int,
    api_key: str,
    timeout: int,
) -> Optional[Dict[str, Any]]:
    """调用腾讯位置服务 POI 检索"""
    params = {
        "key": api_key,
        "keyword": query,
        "boundary": f"region({region},0)",
        "page_size": min(max(page_size, 1), 20),
    }

    resp = requests.get(TENCENT_PLACE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # 腾讯返回 status: 0 表示成功
    status_code = data.get("status")
    if status_code != 0:
        logger.warning(
            "腾讯 POI 接口返回错误 [status=%s]: %s (key=%s***)",
            status_code, data.get("message", "未知错误"), api_key[:8],
        )
        return None

    pois_raw = data.get("data", [])
    if not pois_raw:
        return None

    pois = [_format_tencent_poi(p) for p in pois_raw]

    return {
        "source": "tencent",
        "query": query,
        "region": region,
        "count": len(pois),
        "pois": pois,
    }


def _format_tencent_poi(p: Dict[str, Any]) -> Dict[str, Any]:
    """统一格式化腾讯 POI 数据"""
    location = p.get("location", {})
    return {
        "name": p.get("title", ""),
        "address": p.get("address", ""),
        "tel": p.get("tel", "") or "暂无",
        "category": p.get("category", ""),
        "location": {
            "lat": float(location.get("lat", 0)),
            "lng": float(location.get("lng", 0)),
        },
    }


# ============================================================
# 百度地图
# ============================================================
def _search_baidu(
    query: str,
    region: str,
    page_size: int,
    ak: str,
    timeout: int,
) -> Optional[Dict[str, Any]]:
    """调用百度地图 POI 检索"""
    params = {
        "query": query,
        "region": region,
        "output": "json",
        "ak": ak,
        "page_size": min(max(page_size, 1), 20),
    }

    resp = requests.get(BAIDU_PLACE_URL, params=params, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()

    # 百度返回 status: 0 表示成功，status: 1 表示无结果
    if data.get("status") != 0:
        logger.warning("百度 POI 接口返回错误: %s", data.get("message"))
        return None

    results = data.get("results", [])
    if not results:
        return None

    pois = [_format_baidu_poi(r) for r in results]

    return {
        "source": "baidu",
        "query": query,
        "region": region,
        "count": len(pois),
        "pois": pois,
    }


def _format_baidu_poi(r: Dict[str, Any]) -> Dict[str, Any]:
    """统一格式化百度 POI 数据"""
    location = r.get("location", {})
    lat = float(location.get("lat", 0))
    lng = float(location.get("lng", 0))

    # 从 detail_info 提取文本类别（与腾讯返回的文本类别语义对齐）
    detail_info = r.get("detail_info", {}) or {}
    category = (
        detail_info.get("tag", "")
        or detail_info.get("type", "")
        or str(r.get("detail", ""))
    )

    return {
        "name": r.get("name", ""),
        "address": r.get("address", ""),
        "tel": r.get("telephone", "") or "暂无",
        "category": category,
        "location": {"lat": lat, "lng": lng},
    }


# ============================================================
# POI 结果自动存入知识库
# ============================================================
def _save_pois_to_kb(result: dict, query: str) -> None:
    """将 POI 检索结果自动存入知识库，供后续搜索复用"""
    pois = result.get("pois", [])
    region = result.get("region", "")
    source = result.get("source", "unknown")
    category = _map_query_to_category(query)

    for poi in pois:
        name = poi.get("name", "")
        if not name:
            continue
        address = poi.get("address", "")
        tel = poi.get("tel", "")
        cat = poi.get("category", "")

        content = f"# {name}\n\n- 地址：{address}\n- 电话：{tel}\n- 类别：{cat}\n- 城市：{region}\n- 来源：{source}"
        try:
            upsert_kb_item(
                url=f"poi://{source}/{region}/{name}",
                category=category,
                title=name,
                content_md=content,
                summary=f"{name} - {address} ({cat})",
            )
        except Exception:
            pass  # KB 写入失败不影响主流程


def _map_query_to_category(query: str) -> str:
    """将 POI 查询关键词映射到知识库类别"""
    q = query.lower()
    if any(kw in q for kw in ["景点", "景区", "公园", "博物馆", "attraction"]):
        return "attraction"
    if any(kw in q for kw in ["美食", "餐厅", "火锅", "小吃", "food"]):
        return "food"
    if any(kw in q for kw in ["酒店", "住宿", "宾馆", "hotel"]):
        return "hotel"
    if any(kw in q for kw in ["交通", "地铁", "公交", "transport"]):
        return "transport"
    return "general"


# ============================================================
# 单元自测
# ============================================================
if __name__ == "__main__":
    import os

    cfg = ToolConfig(
        tencent_lbs_key=os.getenv("TENCENT_LBS_KEY", ""),
        baidu_map_ak=os.getenv("BAIDU_MAP_AK", ""),
    )

    print("测试 search_poi('景点', '广州')...")
    result = search_poi("景点", "广州", page_size=5, config=cfg)
    print(json.dumps(json.loads(result), ensure_ascii=False, indent=2))

    print("\n测试 search_poi('美食', '北京')...")
    result = search_poi("美食", "北京", page_size=5, config=cfg)
    print(json.dumps(json.loads(result), ensure_ascii=False, indent=2))