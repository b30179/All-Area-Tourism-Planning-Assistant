# 贡献指南

感谢你对全域旅游规划助手的关注！我们欢迎任何形式的贡献。

## 项目结构

```
src/
├── config.py        # 8 个 LLM 服务商预设 + 配置管理
├── llm_client.py    # OpenAI 兼容流式/非流式调用
├── agent.py         # 多轮工具调用循环
├── ui.py            # Streamlit UI 组件
├── kb/              # SQLite + FTS5 知识库
│   ├── __init__.py
│   └── store.py
└── tools/           # 4 个 LLM 工具
    ├── __init__.py   # 工具注册表
    ├── weather.py    # 天气查询 (wttr.in)
    ├── poi.py        # POI 检索 (腾讯/百度地图)
    ├── crawler.py    # 网页爬取 (crawl4ai)
    └── search_kb.py  # 知识库检索
```

## 开发环境

```bash
# 克隆并安装
git clone https://github.com/b30179/All-Area-Tourism-Planning-Assistant.git
cd All-Area-Tourism-Planning-Assistant
pip install -r requirements.txt

# 安装爬虫依赖（可选）
pip install crawl4ai>=0.9.0
crawl4ai-setup

# 配置
copy .env.example .env
# 编辑 .env 填入 API Key
```

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat: 新增爬虫工具 + 知识库系统
fix: 修复 POI 工具错误信息不显示
docs: 更新 README 使用示例
test: 新增知识库单元测试
refactor: 重构 agent 工具调用循环
```

## 运行测试

```bash
pytest tests/ -v
```

> 需要 Python 3.10+ 和有效的 LLM_API_KEY。

## 提交 PR

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feat/amazing-feature`)
3. 提交改动 (`git commit -m 'feat: add amazing feature'`)
4. 推送到你的 fork (`git push origin feat/amazing-feature`)
5. 创建 Pull Request

PR 应该包含：
- 改动说明（做了什么、为什么）
- 测试结果截图（如有 UI 改动）
- 新增依赖说明（如有）
