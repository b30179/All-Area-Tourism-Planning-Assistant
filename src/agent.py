"""
agent.py - 工具调用循环 Agent

核心机制：
  LLM 推理 → 检测 tool_calls → 执行工具 → 结果回传 LLM → 再推理 → ...
  直到 LLM 不再请求工具调用，或达到 MAX_TOOL_ROUNDS 上限。

防死循环：MAX_TOOL_ROUNDS = 4
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, Generator, List, Optional

from openai import OpenAI

from src.config import LLMConfig, ToolConfig
from src.llm_client import chat_complete, chat_stream
from src.tools import get_all_tool_schemas, get_tool_executor

logger = logging.getLogger(__name__)


# ============================================================
# 流式 Agent（用于 UI 实时渲染）
# ============================================================
def run_agent_stream(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    llm_config: LLMConfig,
    tool_config: ToolConfig,
    max_rounds: int = 4,
) -> Generator[Dict[str, Any], None, None]:
    """
    流式运行 Agent，支持多轮工具调用。

    工作流程：
      Round 0: 流式调用 LLM（首轮）
        ├─ 如果 LLM 返回 tool_calls：
        │   ├─ yield "tool_start" 事件
        │   ├─ 执行工具，yield "tool_result" 事件
        │   ├─ 拼接 tool 消息到 messages
        │   └─ 进入 Round 1（非流式，因为已知道有工具调用）
        └─ 如果 LLM 直接给出最终答案：
            └─ yield "done" 事件，结束

      Round 1+: 非流式调用 LLM（循环直到无 tool_calls 或达上限）

    :yield: 事件 dict
        - {"type": "content", "delta": str}        # 流式文本片段
        - {"type": "tool_start", "tool": str, "args": dict, "round": int}
        - {"type": "tool_result", "tool": str, "result": str, "round": int}
        - {"type": "tool_error", "tool": str, "error": str, "round": int}
        - {"type": "tool_done", "round": int}      # 一轮工具调用完成
        - {"type": "round", "index": int}          # 切换到下一轮
        - {"type": "done", "content": str, "rounds": int}
        - {"type": "error", "message": str}
    """
    tools = get_all_tool_schemas()
    rounds = 0

    # ---- Round 0: 流式首轮 ----
    accumulated_content = ""
    tool_calls_first = None

    for event in chat_stream(client, messages, llm_config, tools=tools):
        if event["type"] == "content":
            accumulated_content += event["delta"]
            yield {"type": "content", "delta": event["delta"]}
        elif event["type"] == "done":
            tool_calls_first = event.get("tool_calls")
        elif event["type"] == "error":
            yield {"type": "error", "message": event["message"]}
            return

    # 检查首轮是否有工具调用
    if not tool_calls_first:
        yield {"type": "done", "content": accumulated_content, "rounds": 0}
        return

    # 拼接 assistant 消息（含 tool_calls）
    messages.append(
        _build_assistant_message(content=accumulated_content, tool_calls=tool_calls_first)
    )

    # ---- Round 1+: 工具调用循环 ----
    while rounds < max_rounds:
        rounds += 1
        yield {"type": "round", "index": rounds}

        # 执行当前轮的所有工具调用
        tool_results = []  # (tool_call_id, name, content)
        for tc in tool_calls_first if rounds == 1 else tool_calls_next:
            tool_name = tc["function"]["name"]
            tool_args_raw = tc["function"]["arguments"]
            tool_id = tc["id"]

            try:
                tool_args = json.loads(tool_args_raw) if tool_args_raw else {}
            except json.JSONDecodeError as e:
                err_msg = f"参数解析失败：{e!s}"
                yield {
                    "type": "tool_error",
                    "tool": tool_name,
                    "error": err_msg,
                    "round": rounds,
                }
                tool_results.append((tool_id, tool_name, json.dumps({"error": err_msg}, ensure_ascii=False)))
                continue

            # 通知 UI 工具开始
            yield {
                "type": "tool_start",
                "tool": tool_name,
                "args": tool_args,
                "round": rounds,
            }

            # 执行工具
            executor = get_tool_executor(tool_name)
            if not executor:
                err_msg = f"未注册的工具：{tool_name}"
                yield {
                    "type": "tool_error",
                    "tool": tool_name,
                    "error": err_msg,
                    "round": rounds,
                }
                tool_results.append((tool_id, tool_name, json.dumps({"error": err_msg}, ensure_ascii=False)))
                continue

            try:
                result_str = executor(tool_args_raw, tool_config)
                # 检查工具返回是否包含业务错误
                is_error, error_msg = _check_tool_error(result_str)
                if is_error:
                    yield {
                        "type": "tool_error",
                        "tool": tool_name,
                        "error": error_msg,
                        "round": rounds,
                    }
                else:
                    yield {
                        "type": "tool_result",
                        "tool": tool_name,
                        "args": tool_args,
                        "result": result_str,
                        "round": rounds,
                    }
                tool_results.append((tool_id, tool_name, result_str))
            except Exception as e:
                logger.exception("工具 %s 执行异常", tool_name)
                err_msg = f"工具执行异常：{e!s}"
                yield {
                    "type": "tool_error",
                    "tool": tool_name,
                    "error": err_msg,
                    "round": rounds,
                }
                tool_results.append((tool_id, tool_name, json.dumps({"error": err_msg}, ensure_ascii=False)))

        # 拼接所有 tool 消息
        for tool_id, tool_name, content in tool_results:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": tool_name,
                    "content": content,
                }
            )

        yield {"type": "tool_done", "round": rounds}

        # 达到上限，停止循环
        if rounds >= max_rounds:
            logger.warning("达到 MAX_TOOL_ROUNDS=%d 上限，强制结束", max_rounds)
            # 让 LLM 基于已有信息生成最终总结（不传 tools，强制输出文本）
            response = chat_complete(client, messages, llm_config, tools=None)
            if response.get("error"):
                yield {"type": "error", "message": response["error"]}
                return
            final = response["content"]
            if final:
                yield {"type": "content", "delta": final}
                yield {"type": "done", "content": accumulated_content + final, "rounds": rounds}
            else:
                # LLM 仍未返回文本 → 用已有的累积内容作为最终答案
                logger.warning("达到上限后 LLM 未返回文本，使用已有内容作为最终回答")
                if accumulated_content:
                    yield {"type": "done", "content": accumulated_content, "rounds": rounds}
                else:
                    yield {"type": "error", "message": "已达到工具调用轮次上限，且未能生成有效回答，请简化需求后重试"}
            return

        # 调用 LLM 继续推理（此轮为非流式，因为还要判断是否还要调用工具）
        response = chat_complete(client, messages, llm_config, tools=tools)
        if response.get("error"):
            yield {"type": "error", "message": response["error"]}
            return

        next_content = response["content"]
        tool_calls_next = response["tool_calls"]

        # 没有工具调用 → 输出最终答案
        if not tool_calls_next:
            if next_content:
                accumulated_content += ("\n\n" + next_content if accumulated_content else next_content)
                yield {"type": "content", "delta": next_content}
            yield {"type": "done", "content": accumulated_content, "rounds": rounds}
            return

        # 还有工具调用 → 拼接 assistant 消息，进入下一轮
        messages.append(
            _build_assistant_message(content=next_content, tool_calls=tool_calls_next)
        )
        if next_content:
            accumulated_content += ("\n\n" + next_content if accumulated_content else next_content)
            yield {"type": "content", "delta": "\n\n" + next_content}


# ============================================================
# 辅助函数
# ============================================================
def _check_tool_error(result_str: str) -> tuple[bool, str]:
    """
    检查工具返回是否为业务错误。
    工具有两种错误返回形式：
      1. JSON: {"error": "..."}
      2. 纯文本错误信息

    :return: (is_error, error_message)
    """
    if not result_str:
        return False, ""
    try:
        data = json.loads(result_str)
        if isinstance(data, dict) and "error" in data:
            return True, str(data["error"])
    except (json.JSONDecodeError, TypeError):
        pass
    return False, ""


def _build_assistant_message(
    content: str, tool_calls: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """构建 assistant 消息（含 tool_calls）"""
    msg = {"role": "assistant", "content": content or ""}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg