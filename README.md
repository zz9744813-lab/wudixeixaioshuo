# NovelForge · 24小时小说 Agent 工作台

> **拆书学习 + 自动写作 + 自我进化** 的小说创作 AI 工作台
> 一站式从「读完一本好书」到「持续生产自己的小说」

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61dafb)](https://react.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## ✨ 这是什么

NovelForge 是面向**长篇小说**创作者的 AI Agent 工作台，核心三大能力：

| 能力 | 说明 |
|------|------|
| 📚 **拆书学习** | 上传小说 → 自动分章、抽取技巧卡、构建可迁移的「写作套路库」 |
| ✍️ **24小时写作 Agent** | 5 步流水线：Planner → Draft → Critic → Rewrite → Continuity，自动循环直到质量达标 |
| 🧬 **自我进化** | 评分 + 反馈 + Darwin 进化引擎 + A/B 测试，越写越好 |

支持**任何 OpenAI 兼容的 LLM**（OpenAI / Anthropic / Gemini / DeepSeek / 自建 API …），不同 Agent 角色可绑定不同模型，按需平衡成本与质量。

---

## 🚀 快速开始

### 方式一：Docker 部署（推荐）

```bash
# 1. 准备环境变量
cp .env.example .env
# 必填两项：APP_API_KEY 和 APP_SECRET_KEY（生成方法见 .env 注释）

# 2. 一键启动
docker compose up -d --build

# 3. 访问
# 前端:   http://localhost:3005
# 后端:   http://localhost:8000/api
# API 文档: http://localhost:8000/docs
```

数据存放在 `./data/`，升级 / 卸载都不会丢。

### 方式二：本地源码运行

```bash
# 后端（终端 1）
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# 前端（终端 2）
cd frontend
npm install
npm start   # 默认 http://localhost:3000
```

> 本地开发时 `.env` 留空即可，前端走 `http://localhost:8000/api`，后端 CORS 默认已放开 `localhost`。

---

## 🧭 功能一览

### 一、核心创作闭环

1. **拆书学习** — `/books`
   - 上传 TXT / MD，**自动分章 + 章节摘要 + 技巧卡抽取**
   - 技巧进入全局 `Techniques` 库，可被所有项目复用

2. **小说项目** — `/projects`
   - 创建项目：题材 / 风格 / 目标字数 / 每日目标
   - 项目详情：写作手册（Playbook）/ 失败模式记录 / 一键启停

3. **Bible 编辑器** — `/bible-editor`
   - 世界观设定（含 AI 生成）
   - 人物档案（主角 / 配角 / 反派 / 导师）
   - 卷 / 章 大纲

4. **写作工厂** — `/factory`
   - **Planner → Draft → Critic → Rewrite → Continuity** 5 步流水线
   - 质量不达标时自动重写，最多 N 轮（可配）
   - 支持**并行 Draft 候选**（多稿择优）和**并行 Critic**（多维度评估）

5. **24h 自动写作** — `/worker`
   - Worker 后台守护，按调度自动产出下一章
   - 每日目标 / 预算控制 / 任务队列

### 二、Agent 编排

| 页面 | 作用 |
|------|------|
| `/agents` | Agent 控制台，多 Agent 协作状态 |
| `/agent-orchestrator` | 主编 Agent，统一调度 |
| `/agent-runs/:id` | 单次 run 的完整步骤溯源 |
| `/subagents` | 子 Agent 注册与管理 |
| `/reader-training` | 读者反馈训练 |
| `/research-agent` | 资料调研 Agent |
| `/evolution-auto` | 自动进化触发器 |

### 三、自我进化

- `/feedback` — 多维度反馈收集
- `/evolution` — Darwin 进化引擎 + A/B 测试
- `/prompts` — Prompt 模板管理 + 模板版本化
- `/skills` — 写作技能库

### 四、运维

- `/dashboard` / `/dashboard-v2` — 统计 + 快捷入口
- `/llm-routes` — LLM 路由（按角色分配 provider）
- `/agent-models` — Agent × 模型矩阵
- `/models` — Provider / API Key 管理（加密存储）
- `/usage` — Token 成本与每日用量
- `/logs` — 系统日志 / LLM 调用日志
- `/export` — 导出 Markdown / TXT / DOCX / EPUB / PDF

---

## 🏗️ 架构

```
+------------------------------------------------------------------+
|                      前端 (React 18 SPA)                         |
|  Dashboard · Projects · Books · BibleEditor · Factory · ...    |
+------------------------------------------------------------------+
                            |  REST + SSE
                            v
+------------------------------------------------------------------+
|                    后端 (FastAPI · Python 3.11)                  |
|                                                                  |
|  Routers ─┬─ projects / chapters / books / bible                |
|           ├─ agents / agent_runs / subagents / orchestrator     |
|           ├─ evolution / feedback / prompts / skills            |
|           ├─ models / llm_routes / model_assignments / usage    |
|           └─ worker / tasks / export / events (SSE)             |
|                                                                  |
|  Services ─┬─ pipeline_service        (5 步章节流水线)          |
|            ├─ production_loop_service  (24h Worker)              |
|            ├─ llm_router              (角色 → Provider)          |
|            ├─ evolution_orchestrator   (Darwin / A/B)            |
|            └─ bible_service / book_state_service / ...          |
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|                  LLM Provider 池（OpenAI 兼容）                  |
|   OpenAI · Anthropic · Gemini · DeepSeek · 自建 API · ...      |
+------------------------------------------------------------------+
                            |
                            v
+------------------------------------------------------------------+
|       数据层：SQLite (开发) / PostgreSQL (生产)                  |
|   projects · chapters · books · bible · feedback · evolution    |
+------------------------------------------------------------------+
```

### 关键模块

- **`LLMServiceManager`** (`backend/app/services/openai_llm_service.py`)
  统一管理多 provider，按 `role` 路由到不同模型；所有调用自动写入 `model_call_logs`。
- **`pipeline_service`** — 5 步章节生成流水线
- **`production_loop_service`** — 24h 后台循环
- **`llm_router`** — 模型角色路由 + 失败重试 + 成本统计
- **`evolution_orchestrator`** — A/B 测试 + 优胜劣汰

---

## ⚙️ 配置说明

### 环境变量（完整列表见 `.env.example`）

| 变量 | 必填 | 说明 |
|------|------|------|
| `APP_API_KEY` | 生产必填 | 前端 → 后端鉴权 |
| `APP_SECRET_KEY` | 生产必填 | Fernet 密钥，用于加密 LLM API Key |
| `APP_ENV` | 否 | `development` / `production` / `staging` |
| `DATABASE_URL` | 否 | 留空 → SQLite，填 `postgresql://...` → PG |
| `CORS_ORIGINS` | 是 | **浏览器实际访问前端的完整 URL**，逗号分隔 |
| `REACT_APP_API_URL` | 是（构建期） | **浏览器请求后端的完整 URL** |
| `LOG_LEVEL` | 否 | `debug` / `info` / `warning` / `error` |
| `UPLOAD_DIR` / `ARTIFACTS_DIR` | 否 | 默认 `./data/uploads`、`./data/artifacts` |

### 部署到任意服务器

> 核心原则：**前端 → 后端**用浏览器可达的地址；**后端 CORS** 放行前端所在 origin。

#### 本机 / Docker（同机访问）
```bash
# .env
CORS_ORIGINS=http://localhost:3000,http://localhost:3005
REACT_APP_API_URL=http://localhost:8000/api
```

#### 远程 VPS（公网访问）
```bash
# 假设你的服务器公网 IP 是 1.2.3.4
# .env
CORS_ORIGINS=http://1.2.3.4:3005
REACT_APP_API_URL=http://1.2.3.4:8000/api
```
> `REACT_APP_*` 是**构建期**变量，改完必须重新构建前端镜像：
> `docker compose build --no-cache frontend && docker compose up -d`

#### 反向代理（Nginx / Caddy 域名）
```bash
# .env
CORS_ORIGINS=https://novel.example.com
REACT_APP_API_URL=    # 留空 → 前端走相对路径 /api
```

#### 启用 HTTPS + 多域名
```bash
CORS_ORIGINS=https://novel.example.com,https://www.example.com
```

### 模型配置（首启必做）

1. 进入 **模型配置中心** `/models`
2. 添加 Provider：OpenAI / Anthropic / Gemini / DeepSeek / OpenRouter / 自定义
3. 填入 `Base URL` + `API Key`（加密存储）
4. 测试连接
5. 到 **Agent 模型分配** `/agent-models` 把每个角色（planner / draft / critic / rewrite / continuity …）绑定到合适的模型

> 没配置 API Key 时，系统自动走 `MockLLMService` 演示流程，方便先体验 UI。

---

## 🔌 API 端点速查

| 前缀 | 模块 |
|------|------|
| `/api/health` | 健康检查（无需鉴权） |
| `/api/dashboard` | 仪表盘统计 |
| `/api/projects` | 小说项目 CRUD + 启停 |
| `/api/chapters` | 章节查询 / 状态 |
| `/api/books` | 拆书上传 / 分章 / 摘要 |
| `/api/projects/{id}/bible` | Bible（**注意：不是 `/api/bible`**） |
| `/api/agents` / `/api/agent-runs` | Agent 编排 |
| `/api/worker` | 24h Worker 控制 |
| `/api/tasks` | 任务队列 |
| `/api/models` / `/api/model-assignments` / `/api/llm-routes` | 模型 / 路由 |
| `/api/feedback` / `/api/evolution` / `/api/prompts` / `/api/skills` | 进化 |
| `/api/usage` / `/api/logs` | 成本 / 日志 |
| `/api/export` | 导出 |
| `/api/events` | SSE 实时事件流（支持 query 鉴权） |

> 除 `/api/health` 和 `/api/events` 外，所有路由需 `X-API-Key: <APP_API_KEY>`。
> 完整 OpenAPI 文档：访问 `/docs`。

---

## 🧪 测试

```bash
cd backend
python -m pytest tests/ -v
```

---

## 🛠️ 开发约定

1. **模型变更** → `alembic revision --autogenerate` + `alembic upgrade head`，不要直接删表
2. **API Key** 加密存储，前端仅显示掩码
3. **所有 LLM 调用** 必须经过 `llm_manager`，不要直接实例化 provider
4. **路由注册**：前端新增页面**必须**在 `App.js` 的 `<Routes>` 中注册，否则会显示空 main 区
5. **JSX 表达式** 是**即时求值**的，对可能为 `null` 的对象做属性访问必须用 `?.` 或显式判空

---

## 🐛 故障排查

| 症状 | 排查 |
|------|------|
| 前端「Network Error」 | 检查 `REACT_APP_API_URL` 是否是**浏览器可访问**的地址；改完要 `docker compose build --no-cache frontend` |
| 浏览器控制台 CORS 报错 | `CORS_ORIGINS` 是否包含前端所在 origin（含端口），多个用逗号分隔 |
| 生产环境启动失败 | `APP_API_KEY` / `APP_SECRET_KEY` 是否已配置；生产模式启动即校验（Fail-Fast） |
| 详情页白屏 | 打开 Console 看 React 错误；常见是 `null.xxx` → 改 `?.` 或显式判空 |
| 章节流水线一直失败 | 查 `/logs`，`model_call_logs` 表里有完整 provider / 状态 / 错误 |

---

## 📁 目录结构

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # Pydantic Settings 配置中心
│   │   ├── database.py             # SQLAlchemy 引擎
│   │   ├── models/                 # ORM 模型
│   │   ├── routers/                # API 路由（35+）
│   │   ├── schemas/                # Pydantic 请求/响应
│   │   ├── services/               # 业务逻辑
│   │   │   ├── pipeline_service.py        # 5 步流水线
│   │   │   ├── production_loop_service.py # 24h Worker
│   │   │   ├── openai_llm_service.py      # LLM 管理器
│   │   │   ├── llm_router.py             # 角色路由
│   │   │   └── ...
│   │   ├── middleware/             # 日志 / 异常处理
│   │   ├── deps/                   # 鉴权 / DB 依赖
│   │   └── utils/                  # 工具函数
│   ├── tests/                      # pytest 测试集
│   ├── alembic/                    # 数据库迁移
│   ├── requirements.txt
│   └── data/                       # SQLite / 上传 / 产物（运行时生成）
├── frontend/
│   ├── public/
│   │   ├── config.js               # 运行时配置注入（可被部署脚本覆盖）
│   │   └── index.html
│   ├── src/
│   │   ├── pages/                  # 页面组件（20+）
│   │   ├── components/             # 通用组件
│   │   ├── contexts/               # React Context（Toast / Theme）
│   │   ├── hooks/                  # 自定义 Hooks
│   │   ├── services/               # axios 封装
│   │   ├── styles/                 # Design Tokens
│   │   ├── utils/                  # 工具函数
│   │   └── App.js                  # 路由表
│   ├── package.json
│   └── .env.example
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── data/                           # 数据持久化（运行时生成）
├── docs/                           # 文档
├── scripts/                        # 辅助脚本
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🗺️ 路线图

- [x] P0 拆书学习 + 项目骨架
- [x] P1 多 Agent 框架
- [x] P2 Bible + 大纲
- [x] P3 章节生成流水线
- [x] P4 24h Worker / 调度器
- [x] P5 反馈 + 进化 + A/B
- [x] P6 导出多格式
- [x] P7 并行 Draft / Critic
- [x] P8 主编 Agent / Darwin 进化
- [ ] P9 多人协作（WebSocket / 多用户）
- [ ] P10 移动端适配

---

## 🤝 贡献

欢迎 Issue / PR！
- 改前端：先看 `frontend/src/styles/tokens.css` 了解设计系统
- 改后端：先看 `backend/app/services/openai_llm_service.py` 了解 LLM 调用约定
- 加新模型角色：同时改 `model_assignments.py` 的 `SUPPORTED_ROLES` 和 `llm_router.py`

---

## 📄 License

[MIT](LICENSE)
