"""测试 src.tools.weather 天气模块"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.tools.weather import (
    WEATHER_TOOL_SCHEMA,
    _parse_current,
    _parse_forecast,
)


class TestWeatherToolSchema:
    """工具 Schema"""

    def test_schema_structure(self):
        assert WEATHER_TOOL_SCHEMA["type"] == "function"
        assert WEATHER_TOOL_SCHEMA["function"]["name"] == "get_weather"

    def test_schema_required_params(self):
        params = WEATHER_TOOL_SCHEMA["function"]["parameters"]
        assert "city" in params["properties"]
        assert "city" in params["required"]


class TestParseCurrent:
    """当前天气解析"""

    def test_basic_current(self):
        cur = {"temp_C": "25", "humidity": "60"}
        result = _parse_current(cur)
        assert result["温度(°C)"] == "25"
        assert result["湿度(%)"] == "60"

    def test_missing_fields(self):
        result = _parse_current({})
        assert result["温度(°C)"] == "未知"
        assert result["湿度(%)"] == "未知"

    def test_chinese_weather_desc(self):
        cur = {
            "temp_C": "30",
            "lang_zh": [{"value": "晴"}],
        }
        result = _parse_current(cur)
        assert result["天气描述"] == "晴"

    def test_fallback_weather_desc(self):
        cur = {
            "weatherDesc": [{"value": "Sunny"}],
        }
        result = _parse_current(cur)
        assert result["天气描述"] == "Sunny"

    def test_lang_zh_empty_list(self):
        cur = {"lang_zh": []}
        # 不会崩溃
        result = _parse_current(cur)
        assert "天气描述" in result


class TestParseForecast:
    """预报解析"""

    def test_empty_forecast(self):
        result = _parse_forecast([])
        assert result == []

    def test_basic_forecast(self):
        days = [
            {
                "date": "2026-07-25",
                "mintempC": "22",
                "maxtempC": "30",
                "hourly": [{}, {}, {}, {}, {"lang_zh": [{"value": "多云"}]}],
                "uvIndex": "5",
            }
        ]
        result = _parse_forecast(days)
        assert len(result) == 1
        assert result[0]["日期"] == "2026-07-25"
        assert result[0]["最低温度(°C)"] == "22"
        assert result[0]["最高温度(°C)"] == "30"
        assert result[0]["日间天气"] == "多云"

    def test_forecast_no_hourly(self):
        days = [{"date": "2026-07-25", "mintempC": "20", "maxtempC": "28"}]
        result = _parse_forecast(days)
        assert len(result) == 1
        assert result[0]["日期"] == "2026-07-25"
