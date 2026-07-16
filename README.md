# 🧳 全域旅游规划助手

基于 **Streamlit + 大语言模型 + 工具调用 (Function Calling)** 的智能旅游规划 AI Agent。

用户用自然语言描述出行需求（如"广州三日游"），AI 自动调用**天气查询**和**POI 检索**工具，生成完整、可执行的行程规划。

---

## ✨ 核心功能

| 模块 | 功能 | 数据源 |
|------|------|--------|
| 💬 LLM 对话 | 多轮对话 / 流式打字机 / System Prompt | OpenAI 兼容 API |
| 🌤️ 天气查询 | 中文城市 / 实时 + 未来 2-3 天 / JSON 结构化 | [wttr.in](https://wttr.in/) |
| 📍 POI 检索 | 关键词检索 / 双源降级 / 结构化列表 | 腾讯位置服务 → 百度地图 |
| 🔁 工具调用循环 | 模型自动决策 / 4 轮防死循环 | — |
| 🎨 Streamlit 前端 | 侧边栏配置 / 工具调用可视化 / 友好 UI | — |

---

## 📂 项目结构

```
tra1/
├── app.py                       # Streamlit 入口（主程序）
├── requirements.txt            # 依赖清单
├── .env.example                # 环境变量样例（复制为 .env 后填入 Key）
├── run.bat                     # Windows 一键启动脚本
├── README.md                   # 本文档
└── src/
    ├── __init__.py
    ├── config.py               # 配置管理（API Key、Base URL、模型名）
    ├── llm_client.py           # LLM 对话模块（流式、System Prompt、Tool Calls）
    ├── agent.py                # 工具调用循环 Agent
    ├── ui.py                   # Streamlit UI 组件
    └── tools/
        ├── __init__.py         # 工具注册表
        ├── weather.py          # get_weather 工具（wttr.in）
        └── poi.py              # search_poi 工具（腾讯 + 百度双源）
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd <项目根目录>
pip install -r requirements.txt
```

### 2. 配置 API Key

复制 `.env.example` 为 `.env`，并填入你的 API Key：

```bash
copy .env.example .env
```

**最小可用配置**（只需要 LLM Key 即可体验天气功能）：
```ini
LLM_API_KEY=sk-your-real-key
LLM_BASE_URL=https://tokenhub.tencentmaas.com/v1
LLM_MODEL=kimi-k2.7-code
```

**完整配置**（启用 POI 双源检索）：
```ini
LLM_API_KEY=sk-xxx
TENCENT_LBS_KEY=your-tencent-key    # https://lbs.qq.com/
BAIDU_MAP_AK=your-baidu-ak          # https://lbsyun.baidu.com/
```

### 3. 启动应用

**方式一：命令行**
```bash
streamlit run app.py
```

**方式二：双击脚本**
双击 `run.bat`

启动后浏览器自动打开 `http://localhost:8501`。

---

## 🔑 API Key 获取指引

### LLM 大模型 Key（必需）
| 服务商 | 申请地址 | 备注 |
|--------|---------|------|
| 腾讯 TokenHub MaaS | https://tokenhub.tencentmaas.com/ | 推荐：兼容 OpenAI，支持 GLM/Kimi 等 |
| OpenAI 官方 | https://platform.openai.com/ | 需要科学上网 |
| DeepSeek | https://platform.deepseek.com/ | 国内可用、价格低 |
| 月之暗面 Kimi | https://platform.moonshot.cn/ | 国内可用 |

> 💡 任何 **OpenAI 兼容** 服务均可使用，只需修改 `LLM_BASE_URL` 和 `LLM_MODEL` 即可。

### 腾讯位置服务 Key（可选）
1. 访问 https://lbs.qq.com/
2. 注册并创建应用 → 获得 `Key`
3. 启用「WebService API」→ 勾选「地点搜索」

### 百度地图 Key（可选）
1. 访问 https://lbsyun.baidu.com/
2. 注册并创建应用 → 获得 `AK`
3. 应用类型选择「服务端」

---

## 💡 使用示例

启动后，在聊天框输入：

- 🌤️ `广州今天天气如何？` → AI 自动查询并展示
- 📍 `广州有哪些必去景点？` → AI 自动检索景点列表
- 🧳 `帮我规划广州三日游` → AI 自动综合天气+景点，生成行程
- 💬 `第二天太热怎么办？` → 多轮对话，上下文保持

侧边栏可调节：Temperature、Max Tokens、清空对话。

---

## 🔄 切换大模型服务商

**启动后在左侧边栏的 "🤖 大模型服务商" 下拉框中选择**，无需修改代码：

| 服务商 | 默认模型 | 备注 |
|--------|---------|------|
| 🔵 OpenAI 官方 | gpt-4o-mini | 需要科学上网 |
| 🟢 DeepSeek | deepseek-chat | 国内可用，性价比高 |
| 🌙 月之暗面 Kimi | moonshot-v1-8k | 国内可用，长上下文 |
| 🐯 智谱 GLM | glm-4-flash | 国内可用，**免费** |
| 🐧 腾讯 TokenHub MaaS | kimi-k2.7-code | 聚合多模型 |
| 🚀 阿里通义千问 | qwen-plus | 国内可用 |
| 🅼 MiniMax | MiniMax-Text-01 | OpenAI 兼容 |
| 🛠️ 自定义 | — | 手动填写 Base URL |

切换后会自动填充对应的 **Base URL** 和**模型列表**，你只需在 API Key 输入框填入对应服务商的密钥即可。

---

## 🧪 测试用例

| 用例 | 输入 | 预期行为 |
|------|------|---------|
| TC-01 天气 | `广州今天天气如何？` | 调用 get_weather，返回实时+预报 |
| TC-02 POI | `广州有哪些必去景点？` | 调用 search_poi，返回景点列表 |
| TC-03 综合 | `广州三日游规划` | 自动串行调用天气+POI，生成行程 |
| TC-04 多轮 | 追问 `第二天太热怎么办？` | 上下文保持 |
| TC-05 流式 | 任意输入 | 打字机逐字输出 |
| TC-06 异常 | `abc天气` | 工具返回错误，AI 友好提示 |
| TC-07 清空 | 点击清空按钮 | 历史消息清空 |
| TC-08 降级 | 关闭腾讯 Key | POI 自动切换到百度 |

---

## 🏗️ 项目架构

采用经典三层架构：表现层（Streamlit UI）→ 逻辑层（Agent + LLM 引擎）→ 数据层（外部 API 服务）。

| 层级 | 模块 | 职责 |
|------|------|------|
| 表现层 | `src/ui.py` + `app.py` | 侧边栏配置、聊天界面、工具调用可视化 |
| 逻辑层 | `src/agent.py` + `src/llm_client.py` | 多轮对话管理、工具调用循环、流式输出 |
| 数据层 | `src/tools/weather.py` + `src/tools/poi.py` | wttr.in 天气、腾讯+百度 POI 双源检索 |

---

## ⚠️ 常见问题

**Q1: 启动后侧边栏没显示 API Key 输入框？**
A: Streamlit 默认记忆 session_state，请刷新浏览器或清空缓存重试。

**Q2: wttr.in 查询失败？**
A: 检查网络，或尝试访问 https://wttr.in/ 验证服务是否可用。

**Q3: POI 检索无结果？**
A: 检查 `TENCENT_LBS_KEY` / `BAIDU_MAP_AK` 是否正确配置。两家都未配置时工具会返回错误。

**Q4: LLM 不调用工具？**
A: 部分模型（如 gpt-3.5-turbo）对工具调用支持较弱，建议使用 `kimi-k2.7-code`、`gpt-4o`、`deepseek-chat` 等。

---

## 📜 License

MIT License - 详见 LICENSE 文件。
