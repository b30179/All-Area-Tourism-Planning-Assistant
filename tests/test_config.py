"""测试 src.config 配置模块"""
import os
import pytest

# 确保项目根在 sys.path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import (
    LLMConfig,
    ToolConfig,
    AppConfig,
    _safe_float,
    _safe_int,
    load_llm_config_from_env,
    load_tool_config_from_env,
    merge_config,
    DEFAULT_TEMPERATURE,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MAX_TOOL_ROUNDS,
    DEFAULT_WEATHER_TIMEOUT,
)


class TestSafeParsers:
    """安全数值解析器"""

    def test_safe_float_valid(self):
        assert _safe_float("0.5", 0.7) == 0.5

    def test_safe_float_invalid(self):
        assert _safe_float("abc", 0.7) == 0.7

    def test_safe_float_empty(self):
        assert _safe_float("", 0.7) == 0.7

    def test_safe_float_clamped(self):
        assert _safe_float("-1", 0.7, min_val=0.0) == 0.0
        assert _safe_float("99", 0.7, max_val=2.0) == 2.0

    def test_safe_int_valid(self):
        assert _safe_int("100", 200) == 100

    def test_safe_int_invalid(self):
        assert _safe_int("abc", 200) == 200

    def test_safe_int_clamped(self):
        assert _safe_int("0", 4, min_val=1) == 1
        assert _safe_int("99999", 2000, max_val=8000) == 8000


class TestConfigLoading:
    """配置加载"""

    def test_llm_config_defaults(self):
        cfg = load_llm_config_from_env()
        assert isinstance(cfg, LLMConfig)
        assert cfg.temperature == DEFAULT_TEMPERATURE
        assert cfg.max_tokens == DEFAULT_MAX_TOKENS

    def test_tool_config_defaults(self):
        cfg = load_tool_config_from_env()
        assert isinstance(cfg, ToolConfig)
        assert cfg.max_tool_rounds == DEFAULT_MAX_TOOL_ROUNDS
        assert cfg.weather_timeout == DEFAULT_WEATHER_TIMEOUT

    def test_merge_config_no_override(self):
        base = AppConfig()
        result = merge_config(base)
        assert result is base

    def test_merge_config_with_override(self):
        base = AppConfig()
        override = LLMConfig(api_key="test-key", model="gpt-test")
        result = merge_config(base, llm_override=override)
        assert result.llm.api_key == "test-key"
        assert result.llm.model == "gpt-test"

    def test_llm_config_with_env(self, monkeypatch):
        monkeypatch.setenv("LLM_TEMPERATURE", "1.5")
        monkeypatch.setenv("LLM_MAX_TOKENS", "500")
        cfg = load_llm_config_from_env()
        assert cfg.temperature == 1.5
        assert cfg.max_tokens == 500

    def test_llm_config_with_invalid_env(self, monkeypatch):
        monkeypatch.setenv("LLM_TEMPERATURE", "bad_value")
        monkeypatch.setenv("LLM_MAX_TOKENS", "not_a_number")
        cfg = load_llm_config_from_env()
        # 应回退到默认值
        assert cfg.temperature == DEFAULT_TEMPERATURE
        assert cfg.max_tokens == DEFAULT_MAX_TOKENS


class TestConfigDataClasses:
    """配置数据类"""

    def test_llmconfig_instantiation(self):
        cfg = LLMConfig(api_key="sk-test")
        assert cfg.api_key == "sk-test"

    def test_toolconfig_instantiation(self):
        cfg = ToolConfig(tencent_lbs_key="t-key")
        assert cfg.tencent_lbs_key == "t-key"

    def test_appconfig_nesting(self):
        app = AppConfig()
        assert isinstance(app.llm, LLMConfig)
        assert isinstance(app.tool, ToolConfig)
