"""
ui.py - Streamlit UI 组件

包含：
1. render_sidebar() - 侧边栏配置面板
2. render_chat_history() - 聊天历史渲染
3. render_tool_event() - 工具调用可视化
4. get_tool_pretty_name() - 工具名友好映射
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import streamlit as st

from src.config import (
    DEFAULT_LLM_BASE_URL,
    DEFAULT_LLM_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
    DEFAULT_SYSTEM_PROMPT,
    LLM_PROVIDERS,
    DEFAULT_LLM_PROVIDER,
    LLMConfig,
    ToolConfig,
)


# ============================================================
# 工具名友好映射
# ============================================================
TOOL_DISPLAY_NAMES = {
    "get_weather": ("🌤️ 天气查询", "查询城市的实时天气与未来 2-3 天预报"),
    "search_poi": ("📍 POI 检索", "检索景点、美食、酒店等兴趣点"),
}


def get_tool_pretty_name(tool_name: str) -> tuple[str, str]:
    """获取工具的友好显示名"""
    return TOOL_DISPLAY_NAMES.get(tool_name, (f"🔧 {tool_name}", "工具调用"))


# ============================================================
# 侧边栏
# ============================================================
def render_sidebar(env_llm: LLMConfig, env_tool: ToolConfig) -> tuple[LLMConfig, ToolConfig]:
    """
    渲染侧边栏配置面板，返回最终生效的 LLMConfig 与 ToolConfig

    :param env_llm: 从 .env / 默认值加载的 LLM 基础配置
    :param env_tool: 从 .env / 默认值加载的工具基础配置
    :return: (UI 覆盖后的 LLMConfig, UI 覆盖后的 ToolConfig)
    """
    # 初始化 provider 状态
    if "selected_provider" not in st.session_state:
        st.session_state.selected_provider = DEFAULT_LLM_PROVIDER

    with st.sidebar:
        st.header("⚙️ 设置")

        # ---- 大模型服务商选择 ----
        st.subheader("🤖 大模型服务商")

        provider_name = st.selectbox(
            "选择服务商",
            options=list(LLM_PROVIDERS.keys()),
            index=list(LLM_PROVIDERS.keys()).index(st.session_state.selected_provider)
            if st.session_state.selected_provider in LLM_PROVIDERS
            else 0,
            key="provider_selectbox",
            help="选择后会自动填充 Base URL 和模型列表",
        )
        st.session_state.selected_provider = provider_name

        provider_info = LLM_PROVIDERS[provider_name]
        if provider_info.get("note"):
            st.caption(f"💡 {provider_info['note']}")

        st.divider()

        # ---- API 配置 ----
        st.subheader("🔑 API 配置")

        api_key = st.text_input(
            "API Key",
            value=env_llm.api_key,
            type="password",
            help="所选服务商的 API Key",
            placeholder="sk-...",
        )

        # Base URL：自定义时手动填，否则用预置值
        if provider_name == "🛠️ 自定义（Custom）":
            base_url = st.text_input(
                "Base URL",
                value=env_llm.base_url,
                help="OpenAI 兼容 API 的完整 base_url，例如 https://api.example.com/v1",
                placeholder="https://api.example.com/v1",
            )
        else:
            base_url = st.text_input(
                "Base URL（自动填充）",
                value=provider_info["base_url"],
                help=f"已自动填充 {provider_name} 的 base_url，可手动修改",
            )

        # 模型：下拉选择或自定义输入
        if provider_name == "🛠️ 自定义（Custom）":
            model = st.text_input(
                "模型名称",
                value=env_llm.model,
                placeholder="例如：gpt-4o-mini",
            )
        else:
            available_models = provider_info["models"]
            # 如果当前 model 在列表中则保留，否则用默认
            current_model = env_llm.model if env_llm.model in available_models else provider_info["default_model"]
            model = st.selectbox(
                "模型",
                options=available_models,
                index=available_models.index(current_model) if current_model in available_models else 0,
                help="切换不同的模型",
            )

        st.divider()

        # ---- 参数调节 ----
        st.subheader("🎛️ 生成参数")

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=env_llm.temperature or DEFAULT_TEMPERATURE,
            step=0.05,
            help="越高越有创造性，越低越稳定",
        )

        max_tokens = st.number_input(
            "Max Tokens",
            min_value=100,
            max_value=8000,
            value=env_llm.max_tokens or DEFAULT_MAX_TOKENS,
            step=100,
        )

        st.divider()

        # ---- 地图 API 配置 ----
        st.subheader("🗺️ 地图 API（POI 检索需要至少配一个）")

        tencent_key = st.text_input(
            "腾讯 LBS Key",
            value=env_tool.tencent_lbs_key,
            type="password",
            help="https://lbs.qq.com/ → 创建 WebService 应用 → 启用地点搜索",
            placeholder="XXXXX-XXXXX-XXXXX",
        )

        baidu_ak = st.text_input(
            "百度地图 AK",
            value=env_tool.baidu_map_ak,
            type="password",
            help="https://lbsyun.baidu.com/ → 创建服务端应用 → 获得 AK",
            placeholder="你的百度 AK",
        )

        if not tencent_key.strip() and not baidu_ak.strip():
            st.warning("⚠️ 未配置地图 Key，POI 检索不可用", icon="⚠️")
        else:
            sources = []
            if tencent_key.strip():
                sources.append("腾讯")
            if baidu_ak.strip():
                sources.append("百度")
            st.success(f"✅ 已配置 {' + '.join(sources)} 地图服务", icon="✅")

        st.divider()

        # ---- 系统提示词查看 ----
        with st.expander("🧭 查看内置系统提示词"):
            st.markdown(DEFAULT_SYSTEM_PROMPT)

        # ---- 已启用工具 ----
        st.markdown("**🛠️ 已启用工具**")
        for tool_name, (display_name, desc) in TOOL_DISPLAY_NAMES.items():
            st.markdown(f"- `{tool_name}` &nbsp; **{display_name}**")
            st.caption(f"  {desc}")

        st.divider()

        # ---- 操作按钮 ----
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ 清空对话", use_container_width=True):
                st.session_state.messages = []
                st.rerun()

        with col2:
            if st.button("🔄 重新初始化", use_container_width=True):
                # 清除所有会话状态，强制完全重建
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()

        st.divider()
        st.caption("💡 提示：侧边栏输入优先于 .env 文件")

    # 返回合并后的配置
    final_llm = LLMConfig(
        api_key=api_key.strip(),
        base_url=base_url.strip() or DEFAULT_LLM_BASE_URL,
        model=model.strip() or DEFAULT_LLM_MODEL,
        temperature=temperature,
        max_tokens=int(max_tokens),
    )
    final_tool = ToolConfig(
        tencent_lbs_key=tencent_key.strip(),
        baidu_map_ak=baidu_ak.strip(),
        weather_timeout=env_tool.weather_timeout,
        http_timeout=env_tool.http_timeout,
        max_tool_rounds=env_tool.max_tool_rounds,
    )
    return final_llm, final_tool


# ============================================================
# 聊天历史渲染
# ============================================================
def render_chat_history(messages: List[Dict[str, Any]]) -> None:
    """
    渲染聊天历史

    :param messages: 消息列表，每条格式：
        {"role": "user"|"assistant"|"tool", ...}
    """
    for msg in messages:
        role = msg.get("role")
        content = msg.get("content", "")

        if role == "user":
            with st.chat_message("user"):
                st.markdown(content)
        elif role == "assistant":
            with st.chat_message("assistant"):
                if content:
                    st.markdown(content)
        # tool 消息不在聊天区渲染（已在折叠面板中展示）


# ============================================================
# 工具调用事件渲染
# ============================================================
def render_tool_event(event: Dict[str, Any]) -> None:
    """
    渲染工具调用相关事件（用于工具调用过程可视化）

    :param event: agent.py yield 的事件 dict
    """
    event_type = event.get("type")

    if event_type == "round":
        # 进入新的一轮工具调用
        idx = event.get("index", 0)
        if idx > 0:
            st.info(f"🔁 进入第 **{idx}** 轮工具调用...", icon="🔁")

    elif event_type == "tool_start":
        tool_name = event.get("tool", "")
        args = event.get("args", {})
        display_name, _ = get_tool_pretty_name(tool_name)
        with st.status(
            f"{display_name}  [第 {event.get('round', '?')} 轮]",
            expanded=True,
            state="running",
        ):
            st.markdown("**📥 调用参数：**")
            st.json(args)

    elif event_type == "tool_result":
        tool_name = event.get("tool", "")
        result_str = event.get("result", "{}")
        display_name, _ = get_tool_pretty_name(tool_name)
        try:
            result_data = json.loads(result_str)
            with st.status(
                f"{display_name} ✅ 完成",
                expanded=False,
                state="complete",
            ):
                st.markdown("**📤 返回结果：**")
                st.json(result_data)
        except (json.JSONDecodeError, TypeError):
            with st.status(
                f"{display_name} ✅ 完成",
                expanded=False,
                state="complete",
            ):
                st.text(result_str)

    elif event_type == "tool_error":
        tool_name = event.get("tool", "")
        error_msg = event.get("error", "")
        display_name, _ = get_tool_pretty_name(tool_name)
        st.error(f"{display_name} ❌ {error_msg}")

    elif event_type == "tool_done":
        # 单轮工具调用结束，无需单独渲染
        pass

    elif event_type == "error":
        st.error(event.get("message", "未知错误"))


# ============================================================
# 顶部标题与说明
# ============================================================
def render_header() -> None:
    """渲染页面顶部"""
    st.title("🧳 全域旅游规划助手")
    st.caption(
        "告诉我 **目的地 + 天数 + 偏好**，"
        "AI 自动调用天气查询与 POI 检索工具，生成一站式行程规划。"
    )

    # 使用示例
    with st.expander("💡 使用示例", expanded=False):
        st.markdown(
            """
**🌤️ 天气查询**
- `广州今天天气怎么样？`
- `北京未来三天会下雨吗？`

**📍 POI 检索**
- `广州有哪些必去景点？`
- `上海有什么好吃的美食？`

**🧳 综合行程**
- `帮我规划广州三日游`
- `带父母去杭州玩两天，求推荐`

**💬 多轮对话**
- 第一轮：`广州三日游怎么安排？`
- 第二轮：`第二天太热了，能换些室内景点吗？`
            """
        )


# ============================================================
# 消息列表辅助
# ============================================================
def ensure_session_state() -> None:
    """确保 session_state 初始化"""
    if "messages" not in st.session_state:
        st.session_state.messages = []


def add_message(role: str, content: str, **kwargs: Any) -> None:
    """向 session_state 添加消息"""
    msg = {"role": role, "content": content}
    msg.update(kwargs)
    st.session_state.messages.append(msg)


def get_messages() -> List[Dict[str, Any]]:
    """获取当前所有消息（含 system prompt）"""
    msgs: List[Dict[str, Any]] = [
        {"role": "system", "content": DEFAULT_SYSTEM_PROMPT}
    ]
    msgs.extend(st.session_state.messages)
    return msgs