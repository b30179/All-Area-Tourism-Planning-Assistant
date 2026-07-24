# 🧳 全域旅游规划助手

基于 **Streamlit + 大语言模型 + 工具调用 (Function Calling)** 的智能旅游规划 AI Agent。

用户用自然语言描述出行需求（如"增城七日游"），AI 自主调用 **4 个工具**——天气查询、POI 检索、网页爬取、知识库检索——生成完整、可执行的行程规划。数据越用越多（POI 自动存库、爬虫内容缓存），次日同一城市秒出结果。

---

## ✨ 核心功能

| 模块 | 功能 | 数据源 |
|------|------|--------|
| 💬 LLM 对话 | 多轮对话 / 流式打字机 / System Prompt | OpenAI 兼容 API |
| 🌤️ 天气查询 | 中文城市 / 实时 + 未来 2-3 天 / JSON 结构化 | [wttr.in](https://wttr.in/) |
| 📍 POI 检索 | 关键词检索 / 双源降级 / 结果自动入库 | 腾讯位置服务 → 百度地图 |
| 📚 知识库检索 | SQLite + FTS5 全文搜索 / 中文 LIKE 降级 | 本地 `src/kb/travel_kb.db` |
| 🕷️ 网页爬取 | static（HTTP）+ js（Playwright 渲染）双策略 | crawl4ai |
| 🔁 工具调用循环 | 模型自主决策 / 最大 4 轮 / 工具失败自动注入提醒 | — |
| 🛡️ 反编造 | 工具失败时禁止 LLM 凭空生成景点/餐厅名 | — |
| 🎨 Streamlit 前端 | 侧边栏配置 / 地图 Key Web 端输入 / 工具调用可视化 | — |

---

## 📂 项目结构

```
├── app.py                       # Streamlit 入口
├── requirements.txt             # 依赖清单
├── .env.example                 # 环境变量样例
├── run.bat                      # Windows 一键启动
├── README.md
├── tests/                       # 82 个单元测试
│   ├── test_config.py
│   ├── test_agent.py
│   ├── test_weather.py
│   ├── test_poi.py
│   ├── test_tools_init.py
│   ├── test_kb.py
│   └── test_new_tools.py
└── src/
    ├── config.py                # 8 个服务商预设 + 安全环境变量解析
    ├── llm_client.py            # 流式 + 非流式 LLM 调用
    ├── agent.py                 # 多轮工具调用循环 + 错误注入提醒
    ├── ui.py                    # 侧边栏 + 聊天区 + 工具事件渲染
    ├── kb/
    │   ├── __init__.py          # SQLite + FTS5 知识库初始化
    │   └── store.py             # CRUD / 全文搜索 / SHA256 去重
    └── tools/
        ├── __init__.py          # 4 工具注册表
        ├── weather.py           # get_weather（wttr.in）
        ├── poi.py               # search_poi（腾讯 → 百度 + 自动存库）
        ├── crawler.py           # crawl_travel_info（static/js 双策略）
        └── search_kb.py         # search_knowledge_base（本地知识库）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

地图 API Key **可在 Web 侧边栏直接输入**，无需编辑文件。如需预设默认值：

```bash
copy .env.example .env
```

```ini
LLM_API_KEY=sk-your-real-key          # 必需
LLM_BASE_URL=https://tokenhub.tencentmaas.com/v1
LLM_MODEL=kimi-k2.7-code

TENCENT_LBS_KEY=your-key              # 可选（POI），也可在 Web 侧边栏填
BAIDU_MAP_AK=your-ak                  # 可选（POI 兜底）
```

### 3. 启动

双击 `run.bat` 或：

```bash
streamlit run app.py
```

浏览器打开 `http://localhost:8501`。

---

## 💡 使用示例

- 🌤️ `广州今天天气如何？`
- 📍 `广州有哪些必去景点？`
- 🧳 `帮我规划增城七日游`
- 💬 `第二天太热了，能换些室内景点吗？`

---

## 🏗️ 架构

```
Streamlit UI (app.py, ui.py)
    ↓
Agent 工具调用循环 (agent.py) ← LLM 引擎 (llm_client.py)
    ↓
工具层 (tools/__init__.py)
    ├── get_weather           → wttr.in
    ├── search_poi            → 腾讯 → 百度  → 自动存知识库
    ├── search_knowledge_base → SQLite + FTS5（本地）
    └── crawl_travel_info     → crawl4ai（static/js）
```

### 数据闭环

```
POI 检索成功 → 自动写入 KB
爬虫抓取成功 → 自动写入 KB
下次同城市   → KB 直接命中，无需调外部 API
```

---

## ⚠️ 常见问题

**Q1: POI 检索失败？**
A: 在 Web 侧边栏「🗺️ 地图 API」填入腾讯 LBS Key 或百度 AK。注意腾讯 Key 需在控制台启用「WebService API → 地点搜索」。

**Q2: 爬虫抓不到内容？**
A: 部分 SPA 页面（马蜂窝、携程）有反爬。crawl4ai 会自动 static→js 降级，但不保证 100% 成功。百科类页面（baike.baidu.com）稳定可用。

**Q3: wttr.in 查询失败？**
A: wttr.in 是免费服务偶有故障，AI 会如实告知而不是编造天气数据。

**Q4: LLM 不调用工具 / 只用 3 天截断？**
A: 建议使用 `kimi-k2.7-code`、`deepseek-chat`、`gpt-4o` 等；侧边栏 Max Tokens 可调至 4000+。

---

## 🧪 测试

```bash
pytest tests/ -v    # 82 个单元测试
```

覆盖：config、agent、weather、poi、tools 注册表、知识库、爬虫 schema。

---

## 📜 License

MIT License