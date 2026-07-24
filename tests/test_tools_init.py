"""测试 src.tools.__init__ 工具注册表"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.tools import (
    TOOL_REGISTRY,
    get_all_tool_schemas,
    get_tool_executor,
    _make_executor,
)


class TestToolRegistry:
    """工具注册表"""

    def test_registry_has_weather(self):
        assert "get_weather" in TOOL_REGISTRY
        assert "schema" in TOOL_REGISTRY["get_weather"]
        assert "executor" in TOOL_REGISTRY["get_weather"]

    def test_registry_has_poi(self):
        assert "search_poi" in TOOL_REGISTRY

    def test_get_all_tool_schemas(self):
        schemas = get_all_tool_schemas()
        assert len(schemas) == 2
        names = [s["function"]["name"] for s in schemas]
        assert "get_weather" in names
        assert "search_poi" in names

    def test_get_tool_executor_exists(self):
        exec_fn = get_tool_executor("get_weather")
        assert callable(exec_fn)

    def test_get_tool_executor_not_exists(self):
        exec_fn = get_tool_executor("nonexistent")
        assert exec_fn is None


class TestMakeExecutor:
    """执行器包装"""

    def test_executor_success(self):
        def dummy(city, config=None):
            return json.dumps({"result": city})

        executor = _make_executor(dummy, required_args=["city"])
        result = executor('{"city": "广州"}', None)
        data = json.loads(result)
        assert data["result"] == "广州"

    def test_executor_missing_required_arg(self):
        def dummy(city, config=None):
            return json.dumps({"result": city})

        executor = _make_executor(dummy, required_args=["city"])
        result = executor("{}", None)
        data = json.loads(result)
        assert "error" in data
        assert "city" in data["error"]

    def test_executor_invalid_json(self):
        def dummy(city, config=None):
            return json.dumps({"result": city})

        executor = _make_executor(dummy, required_args=["city"])
        result = executor("not json", None)
        data = json.loads(result)
        assert "error" in data

    def test_executor_optional_args_default(self):
        def dummy(city, page_size=10, config=None):
            return json.dumps({"city": city, "page_size": page_size})

        executor = _make_executor(
            dummy,
            required_args=["city"],
            optional_args={"page_size": 10},
        )
        result = executor('{"city": "北京"}', None)
        data = json.loads(result)
        assert data["page_size"] == 10

    def test_executor_optional_args_override(self):
        def dummy(city, page_size=10, config=None):
            return json.dumps({"page_size": page_size})

        executor = _make_executor(
            dummy,
            required_args=["city"],
            optional_args={"page_size": 10},
        )
        result = executor('{"city": "北京", "page_size": 20}', None)
        data = json.loads(result)
        assert data["page_size"] == 20

    def test_executor_exception_handling(self):
        def dummy(city, config=None):
            raise ValueError("测试异常")

        executor = _make_executor(dummy, required_args=["city"])
        result = executor('{"city": "广州"}', None)
        data = json.loads(result)
        assert "error" in data
        assert "测试异常" in data["error"]


class TestToolSchemas:
    """Schema 一致性"""

    def test_weather_schema_in_registry(self):
        from src.tools.weather import WEATHER_TOOL_SCHEMA
        assert TOOL_REGISTRY["get_weather"]["schema"] is WEATHER_TOOL_SCHEMA

    def test_poi_schema_in_registry(self):
        from src.tools.poi import POI_TOOL_SCHEMA
        assert TOOL_REGISTRY["search_poi"]["schema"] is POI_TOOL_SCHEMA
