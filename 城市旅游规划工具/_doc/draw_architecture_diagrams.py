"""Draw report-ready PNG diagrams for the travel planning assistant."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

OUT = Path(__file__).resolve().parent / "charts"
OUT.mkdir(exist_ok=True)


def chinese_font():
    candidates = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Arial Unicode MS"]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            return name
    return "DejaVu Sans"


FONT = chinese_font()
plt.rcParams["font.sans-serif"] = [FONT]
plt.rcParams["axes.unicode_minus"] = False

COLORS = {
    "navy": "#163B65",
    "blue": "#DCEAF7",
    "blue_border": "#2E6EAA",
    "green": "#E1F0E7",
    "green_border": "#39865B",
    "orange": "#FFF0D8",
    "orange_border": "#B76A15",
    "gray": "#F3F5F7",
    "gray_border": "#667085",
    "text": "#162433",
    "arrow": "#41566D",
}


def canvas(width=12, height=6.5):
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    return fig, ax


def box(ax, x, y, w, h, title, body, fill, border):
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.7,rounding_size=2.5",
        linewidth=1.6, edgecolor=border, facecolor=fill, zorder=3,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h - 7, title, ha="center", va="center", fontsize=11,
            fontweight="bold", color=COLORS["text"], zorder=4)
    ax.text(x + w / 2, y + h / 2 - 6, body, ha="center", va="center", fontsize=8.5,
            color=COLORS["text"], linespacing=1.55, zorder=4)


def arrow(ax, start, end, text=None, offset=0):
    arr = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=13,
                          linewidth=1.5, color=COLORS["arrow"], zorder=2)
    ax.add_patch(arr)
    if text:
        x = (start[0] + end[0]) / 2
        y = (start[1] + end[1]) / 2 + offset
        ax.text(x, y, text, ha="center", va="center", fontsize=8, color=COLORS["arrow"],
                bbox={"boxstyle": "round,pad=0.22", "facecolor": "white", "edgecolor": "none"}, zorder=5)


def title(ax, value, subtitle):
    ax.text(50, 95, value, ha="center", va="center", fontsize=16, fontweight="bold", color=COLORS["navy"])
    ax.text(50, 89, subtitle, ha="center", va="center", fontsize=9, color=COLORS["gray_border"])


def diagram_31():
    fig, ax = canvas(12, 7)
    title(ax, "全域旅游规划助手系统三层架构", "表现层 — 逻辑层 — 数据层")
    layers = [
        (68, "表现层（Streamlit Web UI）", "侧边栏配置 · 聊天输入 · 对话历史 · 工具状态展示", COLORS["blue"], COLORS["blue_border"]),
        (40, "逻辑层（业务与智能调度）", "app.py 入口 · LLM Client · Agent 工具调用循环 · 工具注册表", COLORS["green"], COLORS["green_border"]),
        (12, "数据层（外部服务与数据源）", "OpenAI 兼容 LLM · wttr.in 天气服务 · 腾讯位置服务 · 百度地图", COLORS["orange"], COLORS["orange_border"]),
    ]
    for y, heading, body, fill, border in layers:
        box(ax, 10, y, 80, 18, heading, body, fill, border)
    arrow(ax, (50, 68), (50, 59), "用户请求、页面渲染", 2)
    arrow(ax, (50, 40), (50, 31), "模型推理、工具查询", 2)
    ax.text(50, 4, "图 3-1  系统三层架构图", ha="center", fontsize=10, color=COLORS["gray_border"])
    fig.savefig(OUT / "fig_3-1_system_three_layer_architecture.png", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def diagram_32():
    fig, ax = canvas(12, 7.2)
    title(ax, "全域旅游规划助手功能模块关系图", "以 Agent 为核心，连接界面、模型、配置与工具")
    box(ax, 6, 60, 22, 18, "Streamlit 前端模块", "侧边栏配置\n聊天历史\n工具调用可视化", COLORS["blue"], COLORS["blue_border"])
    box(ax, 39, 58, 22, 22, "Agent 调度模块", "消息组装\n多轮工具调用\n结果回传\n最大轮数控制", COLORS["green"], COLORS["green_border"])
    box(ax, 72, 60, 22, 18, "LLM 对话模块", "OpenAI 兼容客户端\n流式输出\n异常处理", COLORS["blue"], COLORS["blue_border"])
    box(ax, 8, 20, 25, 18, "配置管理模块", "环境变量加载\n服务商预置配置\n运行参数", COLORS["gray"], COLORS["gray_border"])
    box(ax, 38, 17, 24, 22, "工具注册表", "JSON Schema\n参数解析\n执行器封装", COLORS["green"], COLORS["green_border"])
    box(ax, 71, 20, 23, 18, "实时数据工具", "天气查询\nPOI 检索\n双源降级", COLORS["orange"], COLORS["orange_border"])
    arrow(ax, (28, 69), (39, 69), "用户消息", 4)
    arrow(ax, (61, 69), (72, 69), "推理请求", 4)
    arrow(ax, (72, 64), (61, 64), "回复 / tool_calls", -4)
    arrow(ax, (49, 58), (50, 39), "调用工具", 0)
    arrow(ax, (62, 28), (71, 28), "执行", 4)
    arrow(ax, (71, 23), (62, 23), "JSON 结果", -4)
    arrow(ax, (33, 29), (38, 29), "配置注入", 4)
    arrow(ax, (20, 38), (20, 60), "界面参数", -4)
    ax.text(50, 5, "图 3-2  功能模块关系图", ha="center", fontsize=10, color=COLORS["gray_border"])
    fig.savefig(OUT / "fig_3-2_function_module_relationship.png", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


def diagram_33():
    fig, ax = canvas(12, 7.4)
    title(ax, "全域旅游规划助手交互流程", "用户 → LLM → 工具 → LLM → 用户")
    nodes = [
        (8, "用户", "输入旅游需求", COLORS["blue"], COLORS["blue_border"]),
        (27, "Streamlit 界面", "保存消息\n展示状态", COLORS["blue"], COLORS["blue_border"]),
        (47, "LLM", "理解意图\n决定是否调用工具", COLORS["green"], COLORS["green_border"]),
        (68, "Agent 与工具", "解析 tool_calls\n执行天气 / POI", COLORS["orange"], COLORS["orange_border"]),
        (88, "外部数据服务", "wttr.in\n腾讯 / 百度地图", COLORS["gray"], COLORS["gray_border"]),
    ]
    for x, heading, body, fill, border in nodes:
        box(ax, x - 8, 65, 16, 18, heading, body, fill, border)
        ax.plot([x, x], [15, 65], color="#D0D5DD", linewidth=1, linestyle="--", zorder=1)
    arrow(ax, (8, 60), (27, 60), "1. 提交问题", 4)
    arrow(ax, (27, 55), (47, 55), "2. 消息 + 系统提示词", -4)
    arrow(ax, (47, 50), (68, 50), "3. tool_calls", 4)
    arrow(ax, (68, 45), (88, 45), "4. API 请求", -4)
    arrow(ax, (88, 37), (68, 37), "5. JSON 数据", 4)
    arrow(ax, (68, 30), (47, 30), "6. tool 消息", -4)
    arrow(ax, (47, 23), (27, 23), "7. 最终行程文本", 4)
    arrow(ax, (27, 18), (8, 18), "8. 流式展示", -4)
    ax.text(50, 8, "图 3-3  用户→LLM→工具→LLM→用户的交互流程图", ha="center", fontsize=10, color=COLORS["gray_border"])
    fig.savefig(OUT / "fig_3-3_user_llm_tool_interaction_flow.png", bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)


if __name__ == "__main__":
    diagram_31()
    diagram_32()
    diagram_33()
    print(OUT)
