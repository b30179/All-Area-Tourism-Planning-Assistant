"""
weather.py - 天气查询工具

数据源：wttr.in（免费、支持中文城市名、JSON 格式）
功能：查询中国任意省/地级市的实时天气与未来 2-3 天预报
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

import requests

from src.config import WTTR_BASE_URL, ToolConfig

logger = logging.getLogger(__name__)


# ============================================================
# OpenAI Function Calling Schema
# ============================================================
WEATHER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": (
            "查询中国任意省/地级市/区县的实时天气与未来 2-3 天预报。"
            "支持中文城市名，如'广州'、'北京'、'上海'、'杭州西湖'等。"
            "返回 JSON 格式数据，包含当前实况（温度、体感、天气描述、湿度、紫外线）"
            "与未来 2-3 天的日期、温度范围、日间天气。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：'广州'、'北京'、'上海'",
                }
            },
            "required": ["city"],
        },
    },
}


# ============================================================
# 工具执行函数（被 LLM 通过 Tool Calling 调用）
# ============================================================
def get_weather(city: str, config: ToolConfig | None = None) -> str:
    """
    查询指定城市的实时天气与未来 2-3 天预报。

    :param city: 城市名称（中文，如"广州"、"北京"）
    :param config: 工具配置（可选）
    :return: JSON 字符串，包含 current 与 forecast
    """
    timeout = config.weather_timeout if config else 10

    try:
        # 调用 wttr.in API（format=j1 返回完整 JSON，lang=zh 返回中文）
        resp = requests.get(
            f"{WTTR_BASE_URL}/{city}",
            params={"format": "j1", "lang": "zh"},
            timeout=timeout,
            headers={"Accept-Language": "zh-CN,zh;q=0.9"},
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout:
        return json.dumps(
            {"error": f"天气查询超时（>{timeout}秒），请稍后重试"},
            ensure_ascii=False,
        )
    except requests.RequestException as e:
        logger.error("wttr.in 请求失败: %s", e)
        return json.dumps(
            {"error": f"天气服务请求失败：{e!s}"},
            ensure_ascii=False,
        )
    except json.JSONDecodeError:
        return json.dumps(
            {"error": "天气服务返回数据格式错误"},
            ensure_ascii=False,
        )

    # wttr.in 在城市不存在时仍返回 HTTP 200，但 current_condition 为空
    if not data.get("current_condition"):
        return json.dumps(
            {"error": f"未找到城市「{city}」的天气信息，请检查城市名是否正确"},
            ensure_ascii=False,
        )

    # 解析当前实况
    try:
        current = _parse_current(data["current_condition"][0])
        forecast = _parse_forecast(data.get("weather", [])[:3])

        result = {
            "city": city,
            "current": current,
            "forecast": forecast,
        }
        return json.dumps(result, ensure_ascii=False)
    except (KeyError, IndexError, TypeError) as e:
        logger.error("解析天气数据失败: %s", e)
        return json.dumps(
            {"error": f"解析天气数据失败：{e!s}"},
            ensure_ascii=False,
        )


def _parse_current(cur: Dict[str, Any]) -> Dict[str, Any]:
    """解析 wttr.in 当前天气数据为统一格式"""
    # 天气描述可能在 lang_zh 数组中
    weather_desc = ""
    lang_zh = cur.get("lang_zh") or []
    if lang_zh and isinstance(lang_zh, list):
        weather_desc = lang_zh[0].get("value", "")

    return {
        "温度(°C)": cur.get("temp_C", "未知"),
        "体感温度(°C)": cur.get("FeelsLikeC", "未知"),
        "天气描述": weather_desc or cur.get("weatherDesc", [{}])[0].get("value", ""),
        "湿度(%)": cur.get("humidity", "未知"),
        "风速(km/h)": cur.get("windspeedKmph", "未知"),
        "风向": cur.get("winddir16Point", ""),
        "紫外线指数": cur.get("uvIndex", "未知"),
        "观测时间": cur.get("observation_time", ""),
    }


def _parse_forecast(weather_days: list) -> list:
    """解析 wttr.in 未来预报数据"""
    forecast = []
    for day in weather_days:
        # 日间天气取 hourly[4]（中午 12 点左右）
        hourly = day.get("hourly", [])
        day_weather = ""
        if len(hourly) > 4:
            lang_zh = hourly[4].get("lang_zh") or []
            if lang_zh and isinstance(lang_zh, list):
                day_weather = lang_zh[0].get("value", "")

        forecast.append(
            {
                "日期": day.get("date", ""),
                "最低温度(°C)": day.get("mintempC", ""),
                "最高温度(°C)": day.get("maxtempC", ""),
                "日间天气": day_weather,
                "紫外线指数": day.get("uvIndex", ""),
            }
        )
    return forecast


# ============================================================
# 单元自测
# ============================================================
if __name__ == "__main__":
    # 直接运行此文件可测试工具
    print("测试 get_weather('广州')...")
    result = get_weather("广州")
    print(json.dumps(json.loads(result), ensure_ascii=False, indent=2))

    print("\n测试 get_weather('北京')...")
    result = get_weather("北京")
    print(json.dumps(json.loads(result), ensure_ascii=False, indent=2))

    print("\n测试 get_weather('不存在的城市xyz')...")
    result = get_weather("不存在的城市xyz")
    print(json.dumps(json.loads(result), ensure_ascii=False, indent=2))