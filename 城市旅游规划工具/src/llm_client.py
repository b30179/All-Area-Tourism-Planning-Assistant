"""
llm_client.py - LLM 大模型对话模块

基于 OpenAI 官方 SDK（OpenAI 兼容协议），支持：
- 多轮对话管理
- 流式输出（打字机效果）
- System Prompt 注入
- Function Calling / Tool Use
- 完整的异常捕获与容错
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Generator, List, Optional

from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from src.config import LLMConfig

logger = logging.getLogger(__name__)


# ============================================================
# 客户端工厂（单例模式）
# ============================================================
def create_llm_client(config: LLMConfig) -> OpenAI:
    """
    创建 OpenAI 兼容客户端

    :param config: LLM 配置
    :return: OpenAI 客户端实例
    """
    if not config.api_key:
        raise ValueError(
            "LLM_API_KEY 未配置！请在 .env 文件或 Streamlit 侧边栏填入 API Key。"
        )

    return OpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=60.0,
        max_retries=2,
    )


# ============================================================
# 流式对话（打字机效果）
# ============================================================
def chat_stream(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    config: LLMConfig,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Generator[Dict[str, Any], None, None]:
    """
    流式调用 LLM，逐 chunk 产出

    :param client: OpenAI 客户端
    :param messages: 消息列表（OpenAI Chat Completions 格式）
    :param config: LLM 配置
    :param tools: 工具 Schema 列表（OpenAI Function Calling 格式）
    :yield: {"type": "content" | "tool_calls" | "done" | "error", ...}
    """
    params = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "stream": True,
    }
    if tools:
        params["tools"] = tools
        params["tool_choice"] = "auto"

    logger.info(f"[LLM Stream] model={config.model}, msgs={len(messages)}, tools={len(tools) if tools else 0}")

    try:
        stream = client.chat.completions.create(**params)
    except AuthenticationError as e:
        logger.error(f"认证失败: {e}")
        yield {"type": "error", "message": "❌ API Key 认证失败，请检查 LLM_API_KEY 是否正确"}
        return
    except RateLimitError as e:
        logger.error(f"频率超限: {e}")
        yield {"type": "error", "message": "❌ API 调用频率超限，请稍后重试或升级套餐"}
        return
    except APITimeoutError as e:
        logger.error(f"超时: {e}")
        yield {"type": "error", "message": "❌ LLM 响应超时，请稍后重试"}
        return
    except APIConnectionError as e:
        logger.error(f"连接错误: {e}")
        yield {"type": "error", "message": f"❌ 无法连接 LLM 服务：{e!s}"}
        return
    except APIError as e:
        logger.error(f"API 错误: {e}")
        yield {"type": "error", "message": f"❌ LLM API 错误：{e!s}"}
        return
    except Exception as e:
        logger.exception("未预期的 LLM 调用异常")
        yield {"type": "error", "message": f"❌ LLM 调用失败：{e!s}"}
        return

    # 累积流式响应
    accumulated_content = ""
    tool_calls_acc: Dict[int, Dict[str, Any]] = {}
    finish_reason = None
    chunk_count = 0

    try:
        for chunk in stream:
            chunk_count += 1
            if not chunk.choices:
                continue

            choice = chunk.choices[0]
            delta = choice.delta
            finish_reason = choice.finish_reason or finish_reason

            # 1) 累积文本内容
            if delta.content:
                accumulated_content += delta.content
                yield {"type": "content", "delta": delta.content}

            # 2) 累积工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls_acc:
                        tool_calls_acc[idx] = {
                            "id": "",
                            "type": "function",
                            "function": {"name": "", "arguments": ""},
                        }
                    if tc.id:
                        tool_calls_acc[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        tool_calls_acc[idx]["function"]["name"] += tc.function.name
                    if tc.function and tc.function.arguments:
                        tool_calls_acc[idx]["function"]["arguments"] += tc.function.arguments

    except Exception as e:
        logger.exception("流式响应中断")
        yield {"type": "error", "message": f"❌ 流式响应中断：{e!s}"}
        return

    logger.info(
        f"[LLM Stream] 完成: chunks={chunk_count}, "
        f"content_len={len(accumulated_content)}, "
        f"tool_calls={len(tool_calls_acc)}, "
        f"finish_reason={finish_reason}"
    )

    # 最终汇总
    final_tool_calls = list(tool_calls_acc.values()) if tool_calls_acc else None
    yield {
        "type": "done",
        "content": accumulated_content,
        "tool_calls": final_tool_calls,
        "finish_reason": finish_reason,
    }


# ============================================================
# 一次性完整调用（非流式，用于工具调用循环）
# ============================================================
def chat_complete(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    config: LLMConfig,
    tools: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    一次性完整调用 LLM（用于工具调用循环中的中间步骤）

    :param client: OpenAI 客户端
    :param messages: 消息列表
    :param config: LLM 配置
    :param tools: 工具 Schema 列表
    :return: {"content": str, "tool_calls": List[Dict] | None, "error": str | None}
    """
    params = {
        "model": config.model,
        "messages": messages,
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
    }
    if tools:
        params["tools"] = tools
        params["tool_choice"] = "auto"

    try:
        response = client.chat.completions.create(**params)
    except AuthenticationError:
        return {"content": "", "tool_calls": None, "error": "API Key 认证失败"}
    except RateLimitError:
        return {"content": "", "tool_calls": None, "error": "API 频率超限"}
    except APITimeoutError:
        return {"content": "", "tool_calls": None, "error": "LLM 响应超时"}
    except APIConnectionError as e:
        return {"content": "", "tool_calls": None, "error": f"无法连接 LLM：{e!s}"}
    except APIError as e:
        return {"content": "", "tool_calls": None, "error": f"LLM API 错误：{e!s}"}
    except Exception as e:
        logger.exception("LLM 调用异常")
        return {"content": "", "tool_calls": None, "error": f"LLM 调用失败：{e!s}"}

    if not response.choices:
        return {"content": "", "tool_calls": None, "error": "LLM 返回空响应"}

    msg = response.choices[0].message

    # 提取工具调用（转为标准 dict）
    tool_calls = None
    if msg.tool_calls:
        tool_calls = []
        for tc in msg.tool_calls:
            tool_calls.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
            )

    return {
        "content": msg.content or "",
        "tool_calls": tool_calls,
        "finish_reason": response.choices[0].finish_reason,
        "error": None,
    }


# ============================================================
# 单元自测
# ============================================================
if __name__ == "__main__":
    from src.config import load_llm_config_from_env

    cfg = load_llm_config_from_env()
    if not cfg.api_key:
        print("❌ 未配置 LLM_API_KEY，无法自测")
    else:
        client = create_llm_client(cfg)
        print(f"客户端创建成功，模型: {cfg.model}")

        # 测试流式
        messages = [{"role": "user", "content": "你好，请用一句话介绍广州"}]
        print("\n--- 流式输出测试 ---")
        for event in chat_stream(client, messages, cfg):
            if event["type"] == "content":
                print(event["delta"], end="", flush=True)
            elif event["type"] == "done":
                print(f"\n\n[finish_reason]: {event['finish_reason']}")
            elif event["type"] == "error":
                print(f"\n[错误]: {event['message']}")