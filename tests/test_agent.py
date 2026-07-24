"""测试 src.agent Agent 模块"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from src.agent import (
    _build_assistant_message,
    _check_tool_error,
)


class TestBuildAssistantMessage:
    """辅助消息构建"""

    def test_empty_content_no_tools(self):
        msg = _build_assistant_message("", [])
        assert msg == {"role": "assistant", "content": ""}
        assert "tool_calls" not in msg

    def test_with_content(self):
        msg = _build_assistant_message("你好", [])
        assert msg["content"] == "你好"

    def test_with_tool_calls(self):
        tcs = [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "get_weather", "arguments": '{"city": "广州"}'},
            }
        ]
        msg = _build_assistant_message("", tcs)
        assert msg["tool_calls"] == tcs
        assert msg["role"] == "assistant"

    def test_none_content(self):
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        msg = _build_assistant_message("", [])
        assert msg["content"] == ""


class TestCheckToolError:
    """工具错误检测"""

    def test_valid_success_result(self):
        result = json.dumps({"city": "广州", "current": {"温度": "25"}})
        is_err, msg = _check_tool_error(result)
        assert not is_err
        assert msg == ""

    def test_error_result(self):
        result = json.dumps({"error": "天气查询超时"})
        is_err, msg = _check_tool_error(result)
        assert is_err
        assert msg == "天气查询超时"

    def test_empty_string(self):
        is_err, msg = _check_tool_error("")
        assert not is_err

    def test_none_or_empty(self):
        is_err, msg = _check_tool_error("")
        assert not is_err

    def test_invalid_json(self):
        is_err, msg = _check_tool_error("not json")
        assert not is_err

    def test_json_but_no_error_key(self):
        result = json.dumps({"status": "ok"})
        is_err, msg = _check_tool_error(result)
        assert not is_err

    def test_nested_error_key(self):
        # 只有顶层的 error 才判定为错误
        result = json.dumps({"data": {"error": "some value"}})
        is_err, msg = _check_tool_error(result)
        assert not is_err
