"""
app.py - 全域旅游规划助手 主入口

启动方式：
    streamlit run app.py

或双击 run.bat
"""
from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

# 将项目根目录加入 sys.path（以便直接 `streamlit run app.py`）
PROJECT_ROOT = Path(__file__).parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st  # noqa: E402

from src.agent import run_agent_stream  # noqa: E402
from src.config import (  # noqa: E402
    DEFAULT_SYSTEM_PROMPT,
    LLMConfig,
    ToolConfig,
    load_llm_config_from_env,
    load_tool_config_from_env,
)
from src.llm_client import create_llm_client  # noqa: E402
from src.ui import (  # noqa: E402
    add_message,
    ensure_session_state,
    get_messages,
    render_chat_history,
    render_header,
    render_sidebar,
    render_tool_event,
)

# ============================================================
# 日志配置
# ============================================================
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ============================================================
# Streamlit 页面配置（必须在最前）
# ============================================================
st.set_page_config(
    page_title="全域旅游规划助手",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "全域旅游规划助手 v1.0",
    },
)


# ============================================================
# 主入口
# ============================================================
def main() -> None:
    # 1) 加载 .env 中的配置
    env_llm_config = load_llm_config_from_env()
    env_tool_config = load_tool_config_from_env()

    # 2) 渲染顶部
    render_header()

    # 3) 渲染侧边栏（返回 UI 覆盖后的 LLMConfig + ToolConfig）
    final_llm_config, final_tool_config = render_sidebar(env_llm_config, env_tool_config)

    # 4) 初始化 session_state
    ensure_session_state()

    # 5) 渲染聊天历史
    render_chat_history(st.session_state.messages)

    # 6) 用户输入
    user_input = st.chat_input(
        "请输入目的地 + 天数，例如：广州三日游",
        key="user_input",
    )

    if not user_input:
        return

    # 7) 校验 API Key
    if not final_llm_config.api_key:
        st.error("❌ 请先在左侧边栏填写 API Key")
        return

    # 8) 添加用户消息到历史
    add_message("user", user_input)

    with st.chat_message("user"):
        st.markdown(user_input)

    # 9) 创建 LLM 客户端
    try:
        client = create_llm_client(final_llm_config)
    except Exception as e:
        st.error(f"❌ 创建 LLM 客户端失败：{e!s}")
        return

    # 10) 构造消息上下文（含 system prompt + 历史）
    messages = get_messages()

    # 11) 运行 Agent 流式推理
    with st.chat_message("assistant"):
        # 占位：流式文本 + 工具调用过程
        response_placeholder = st.empty()
        tool_container = st.container()

        accumulated_text = ""
        final_content = ""
        rounds = 0

        with tool_container:
            for event in run_agent_stream(
                client=client,
                messages=messages,
                llm_config=final_llm_config,
                tool_config=final_tool_config,
                max_rounds=final_tool_config.max_tool_rounds,
            ):
                event_type = event.get("type")
                logger.debug(f"[Agent Event] type={event_type}, keys={list(event.keys())}")

                if event_type == "content":
                    delta = event.get("delta", "")
                    accumulated_text += delta
                    response_placeholder.markdown(accumulated_text + "▌")

                elif event_type in ("tool_start", "tool_result", "tool_error", "round"):
                    render_tool_event(event)

                elif event_type == "done":
                    final_content = event.get("content", accumulated_text)
                    rounds = event.get("rounds", 0)
                    logger.info(f"[Agent Done] rounds={rounds}, content_len={len(final_content)}")
                    response_placeholder.markdown(final_content if final_content else "_(AI 未返回内容)_")

                elif event_type == "error":
                    err_msg = event.get("message", "未知错误")
                    logger.error(f"[Agent Error] {err_msg}")
                    st.error(err_msg)
                    final_content = f"⚠️ {err_msg}"
                    break

        # 12) 保存到历史
        if final_content:
            add_message("assistant", final_content)

        if rounds > 0:
            st.caption(f"🔁 本次对话经历了 {rounds} 轮工具调用")


# ============================================================
# 脚本入口
# ============================================================
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.exception("主程序异常")
        st.error(f"❌ 程序异常退出：{e!s}")
        st.stop()