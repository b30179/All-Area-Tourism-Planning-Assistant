"""
config.py - 全局配置管理

统一管理 LLM API、工具 API、运行参数等配置。
优先级：Streamlit 侧边栏输入 > .env 文件 > 代码默认值
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()


# ============================================================
# 默认配置（OpenAI 兼容接口）
# ============================================================
DEFAULT_LLM_BASE_URL = "https://tokenhub.tencentmaas.com/v1"
DEFAULT_LLM_MODEL = "kimi-k2.7-code"

# ============================================================
# 预置大模型服务商（侧边栏下拉框使用）
# ============================================================
# 用户可在网页上一键切换，无需手动修改 Base URL
LLM_PROVIDERS = {
    "🔵 OpenAI 官方": {
        "base_url": "https://api.openai.com/v1",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "default_model": "gpt-4o-mini",
        "note": "需要科学上网",
    },
    "🟢 DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "default_model": "deepseek-chat",
        "note": "国内可用，注册送额度，性价比高",
    },
    "🌙 月之暗面 Kimi": {
        "base_url": "https://api.moonshot.cn/v1",
        "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"],
        "default_model": "moonshot-v1-8k",
        "note": "国内可用，支持长上下文",
    },
    "🐯 智谱 GLM": {
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "models": ["glm-4-plus", "glm-4-flash", "glm-4-air", "glm-4-airx"],
        "default_model": "glm-4-flash",
        "note": "国内可用，GLM-4-Flash 免费",
    },
    "🐧 腾讯 TokenHub MaaS": {
        "base_url": "https://tokenhub.tencentmaas.com/v1",
        "models": [
            "kimi-k2.7-code",
            "deepseek-v3",
            "glm-4.6",
            "hunyuan-pro",
            "hunyuan-turbo",
        ],
        "default_model": "kimi-k2.7-code",
        "note": "腾讯云，汇聚多模型，需 TokenHub Key",
    },
    "🚀 阿里通义千问 DashScope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "models": ["qwen-plus", "qwen-turbo", "qwen-max", "qwen-long"],
        "default_model": "qwen-plus",
        "note": "国内可用，OpenAI 兼容模式",
    },
    "🅼 MiniMax": {
        "base_url": "https://api.MiniMax.com/v1",
        "models": ["MiniMax-Text-01", "MiniMax-Text-01-32k"],
        "default_model": "MiniMax-Text-01",
        "note": "MiniMax API（OpenAI 兼容）",
    },
    "🛠️ 自定义（Custom）": {
        "base_url": "",
        "models": [],
        "default_model": "",
        "note": "手动填写 Base URL 和模型名",
    },
}

DEFAULT_LLM_PROVIDER = "🐧 腾讯 TokenHub MaaS"

# 工具 API
TENCENT_PLACE_URL = "https://apis.map.qq.com/ws/place/v1/search"
BAIDU_PLACE_URL = "https://api.map.baidu.com/place/v2/search"

# wttr.in 天气服务
WTTR_BASE_URL = "https://wttr.in"

# 运行参数
DEFAULT_MAX_TOOL_ROUNDS = 4
DEFAULT_WEATHER_TIMEOUT = 10  # 秒
DEFAULT_HTTP_TIMEOUT = 8     # 地图 API 超时
DEFAULT_TEMPERATURE = 0.7
DEFAULT_MAX_TOKENS = 2000


# ============================================================
# 环境变量安全解析
# ============================================================
def _safe_float(value: str, default: float, min_val: float = 0.0, max_val: float = 2.0) -> float:
    """安全解析浮点数，非法值返回默认值并限制范围"""
    try:
        v = float(value)
        return max(min_val, min(max_val, v))
    except (ValueError, TypeError):
        return default


def _safe_int(value: str, default: int, min_val: int = 1, max_val: int = 10000) -> int:
    """安全解析整数，非法值返回默认值并限制范围"""
    try:
        v = int(value)
        return max(min_val, min(max_val, v))
    except (ValueError, TypeError):
        return default


# ============================================================
# System Prompt（系统提示词）
# ============================================================
DEFAULT_SYSTEM_PROMPT = """你是"全域旅游规划助手"，一位专业的 AI 旅游顾问，专注于为中国用户提供个性化、可执行的旅游行程规划服务。

## 你的核心能力
1. **天气查询**：使用 `get_weather` 工具查询中国任意城市的实时天气与未来 2-3 天预报。
2. **POI 检索**：使用 `search_poi` 工具检索景点、美食、酒店、商场等兴趣点信息。

## 你的工作准则
- **必须调用工具**：涉及天气、景点、美食、住宿等实时信息时，**务必调用相应工具**获取真实数据，禁止凭空捏造。
- **多工具协作**：复杂行程规划（如"X 日游"）应先查天气、再查景点与美食、综合生成行程。
- **数据真实**：所有行程内容必须基于工具返回的真实数据。
- **结构化输出**：行程规划使用清晰的"Day 1 / Day 2"分段格式，包含时间、景点、用餐建议。
- **友好专业**：使用第二人称交流，语言亲切，给出贴心的旅行小贴士（如穿衣、防晒、避开高峰）。

## 输出格式示例
- 天气回答：当前温度 + 未来 2-3 天预报 + 出行建议
- 景点回答：列表形式（名称 + 简介 + 推荐理由）
- 行程规划：分日详细安排（上午/中午/下午/晚上）

现在请等待用户的旅游规划需求，并主动调用工具完成任务。"""


# ============================================================
# 配置数据类
# ============================================================
@dataclass
class LLMConfig:
    """LLM 配置"""

    api_key: str = ""
    base_url: str = DEFAULT_LLM_BASE_URL
    model: str = DEFAULT_LLM_MODEL
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS


@dataclass
class ToolConfig:
    """工具配置"""

    tencent_lbs_key: str = ""
    baidu_map_ak: str = ""
    weather_timeout: int = DEFAULT_WEATHER_TIMEOUT
    http_timeout: int = DEFAULT_HTTP_TIMEOUT
    max_tool_rounds: int = DEFAULT_MAX_TOOL_ROUNDS


@dataclass
class AppConfig:
    """应用总配置"""

    llm: LLMConfig = field(default_factory=LLMConfig)
    tool: ToolConfig = field(default_factory=ToolConfig)
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


# ============================================================
# 从 .env / 环境变量加载
# ============================================================
def load_llm_config_from_env() -> LLMConfig:
    """从环境变量加载 LLM 配置（非法值回退为默认值）"""
    return LLMConfig(
        api_key=os.getenv("LLM_API_KEY", ""),
        base_url=os.getenv("LLM_BASE_URL", DEFAULT_LLM_BASE_URL),
        model=os.getenv("LLM_MODEL", DEFAULT_LLM_MODEL),
        temperature=_safe_float(
            os.getenv("LLM_TEMPERATURE", ""), DEFAULT_TEMPERATURE, min_val=0.0, max_val=2.0
        ),
        max_tokens=_safe_int(
            os.getenv("LLM_MAX_TOKENS", ""), DEFAULT_MAX_TOKENS, min_val=100, max_val=8000
        ),
    )


def load_tool_config_from_env() -> ToolConfig:
    """从环境变量加载工具配置（非法值回退为默认值）"""
    return ToolConfig(
        tencent_lbs_key=os.getenv("TENCENT_LBS_KEY", ""),
        baidu_map_ak=os.getenv("BAIDU_MAP_AK", ""),
        weather_timeout=_safe_int(
            os.getenv("WEATHER_TIMEOUT", ""), DEFAULT_WEATHER_TIMEOUT, min_val=3, max_val=60
        ),
        http_timeout=DEFAULT_HTTP_TIMEOUT,
        max_tool_rounds=_safe_int(
            os.getenv("MAX_TOOL_ROUNDS", ""), DEFAULT_MAX_TOOL_ROUNDS, min_val=1, max_val=10
        ),
    )


def merge_config(
    base: AppConfig, llm_override: Optional[LLMConfig] = None
) -> AppConfig:
    """
    合并配置：UI 侧边栏输入优先级最高
    :param base: 基础配置（从 .env 加载）
    :param llm_override: UI 覆盖配置
    :return: 合并后的配置
    """
    if llm_override is None:
        return base
    base.llm = llm_override
    return base