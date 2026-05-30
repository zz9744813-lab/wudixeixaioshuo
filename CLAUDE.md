# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个面向小说创作者的 AI Agent 工作台（24小时小说 Agent 工作台），核心能力包括：
- **拆书学习模块**：上传小说后，系统自动拆解作品结构，提取可迁移的写作技巧
- **24小时写作 Agent**：自动规划、生成、审稿、改稿、续写、复盘
- **自我进化机制**：通过评分、反馈持续学习进步

## 技术栈

- **后端**: Python 3.11, FastAPI, SQLAlchemy, SQLite (生产可用 PostgreSQL)
- **前端**: React 18, Design Tokens (CSS 自定义属性), Lucide Icons
- **部署**: Docker, Docker Compose

## 常用命令

### 开发环境启动

```bash
# Docker 方式（推荐）
docker-compose up --build

# 本地方式 - 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# 本地方式 - 前端（新开终端）
cd frontend
npm install
npm start
```

### 数据库迁移

```bash
cd backend

# 生成迁移（自动检测模型变化）
python -m alembic revision --autogenerate -m "描述"

# 应用迁移
python -m alembic upgrade head

# 回滚到上一版本
python -m alembic downgrade -1
```

### 测试

```bash
# 后端测试
cd backend
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_llm_router.py -v

# 运行特定测试
python -m pytest tests/test_llm_router.py::test_provider_fallback -v
```

### 代码格式化

```bash
# 后端代码格式化
cd backend
black app/
isort app/
```

## 项目架构

### 后端结构 (FastAPI)

```
backend/app/
├── main.py              # FastAPI 入口，注册所有路由
├── config.py            # Pydantic Settings 配置中心
├── database.py          # SQLAlchemy 引擎和会话
├── models/              # 数据模型 (SQLAlchemy)
│   ├── __init__.py      # 模型导出
│   ├── project.py       # Project, NovelBible
│   ├── book.py          # Book, BookChapter
│   ├── chapter.py       # Chapter, ChapterVersion
│   ├── task.py          # GenerationTask, GenerationStep
│   └── ...
├── routers/             # API 路由 (FastAPI Router)
│   ├── __init__.py      # 路由聚合
│   ├── projects.py      # /api/projects
│   ├── chapters.py      # /api/chapters
│   └── ...
├── schemas/             # Pydantic 请求/响应模型
├── services/            # 业务逻辑层
│   ├── llm_service.py           # LLM 服务基类
│   ├── openai_llm_service.py    # OpenAI 兼容服务 + LLMServiceManager
│   ├── pipeline_service.py      # 章节生成流水线
│   ├── bible_service.py         # Bible 管理
│   └── ...
├── deps/                # FastAPI 依赖 (auth, db)
└── middleware/          # 中间件 (日志、异常处理)
```

### 前端结构 (React)

```
frontend/src/
├── App.js               # 路由配置
├── index.js             # 入口
├── components/          # 可复用组件
│   ├── Layout.jsx       # 布局组件
│   └── ui/                # UI 原始组件
├── pages/               # 页面组件
│   ├── Dashboard.js
│   ├── Projects.js
│   ├── WritingFactory.js
│   └── ...
├── services/            # API 封装
│   └── api.js           # axios 实例和请求函数
├── hooks/               # 自定义 Hooks
│   ├── useFetch.js      # API 请求状态管理
│   └── useTheme.js      # 主题管理
└── styles/              # 设计系统
    ├── tokens.css       # Design Tokens (颜色、间距等)
    ├── primitives.css   # 原始组件样式
    └── base.css         # 基础样式
```

## 关键架构模式

### LLM 服务管理

系统通过 `LLMServiceManager` (在 `openai_llm_service.py`) 统一管理多 provider 调用：

- **角色映射**: planner, draft, critic, rewrite, continuity, memory_update 等角色可配置不同 provider/model
- **调用日志**: 所有调用自动记录到 `model_call_logs` 表，包含 token/cost/status
- **Mock 回退**: 未配置 API Key 时自动使用 MockLLMService

```python
from app.services.openai_llm_service import llm_manager

# 初始化（通常在 lifespan 中）
await llm_manager.init_from_db(db)

# 调用
response = await llm_manager.generate(
    prompt="...",
    role="draft",  # 根据角色选择 provider
    project_id=1,
)
```

### 章节生成流水线

章节生成采用 5 步流水线（在 `pipeline_service.py`）：

1. **Planner**: 规划章节内容
2. **Draft**: 起草章节
3. **Critic**: 多维度评分
4. **Rewrite**: 根据评分改写（如需要）
5. **Continuity**: 一致性检查

流水线支持自动循环：质量不达标时自动重写，最多 `max_rewrite_rounds` 次。

### 数据库模型关系

核心关系链：
```
Project (1) --> (N) Chapter
Project (1) --> (1) NovelBible
Project (1) --> (N) GenerationTask
GenerationTask (1) --> (N) GenerationStep
Chapter (1) --> (N) ChapterVersion
```

### API 鉴权

- 除 `/api/health` 和 `/api/events` (SSE) 外，所有路由需要 `X-API-Key` Header
- SSE 端点在内部自行验证 API Key（支持 header 或 query 参数）
- 生产环境必须配置 `APP_API_KEY` 和 `APP_SECRET_KEY`

## 配置说明

### 环境变量 (`.env`)

```bash
# 安全密钥（生产必填）
APP_API_KEY=your-api-key          # 前端鉴权用
APP_SECRET_KEY=your-secret-key    # 加密 LLM API Key 用 (必须是 Fernet key)

# 生成方法：
# API_KEY: python -c "import secrets; print(secrets.token_urlsafe(32))"
# SECRET_KEY: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 环境
APP_ENV=development  # 或 production, staging

# 数据库
DATABASE_URL=sqlite:///app/data/novel_agent.db

# 开发配置
APP_AUTO_CREATE_TABLES=true  # 开发环境自动建表（生产禁用，使用 alembic）
```

### 模型配置

系统不预置任何 API Key，需要用户在「模型配置中心」配置：

1. 添加 Provider (OpenAI/Anthropic/Gemini/OpenRouter/自定义)
2. 配置 Base URL 和 API Key
3. 测试连接
4. 映射模型角色（Planner/Draft/Critic/Rewrite/Continuity）

## 关键文件

- `backend/app/config.py` - 配置中心，环境变量定义
- `backend/app/database.py` - 数据库连接和初始化
- `backend/app/models/__init__.py` - 模型导出
- `backend/app/routers/__init__.py` - 路由注册
- `backend/app/services/openai_llm_service.py` - LLM 服务管理器
- `backend/app/services/pipeline_service.py` - 章节生成流水线
- `docker-compose.yml` - 服务编排

## 开发注意事项

1. **数据库变更**: 修改 models 后必须创建 alembic 迁移，不要直接删表重建
2. **API Key 安全**: API Key 加密存储，前端只显示掩码
3. **LLM 调用**: 所有 LLM 调用必须通过 `llm_manager`，不要直接实例化 provider
4. **事务管理**: 服务层负责业务逻辑，事务在 router 层用 `db.commit()` 控制
5. **日志记录**: LLM 调用日志独立提交，不跟随业务事务 rollback

## 前端设计系统

- **Design Tokens**: `src/styles/tokens.css` 定义颜色、间距、阴影、字体等 CSS 变量
- **主题切换**: 支持浅色/深色/跟随系统，通过 `data-theme` 属性切换
- **图标**: 使用 Lucide React (`import { IconName } from 'lucide-react'`)
- **API 请求**: 统一使用 `useFetch` Hook，自动处理 loading/error/retry

## 访问地址

- 前端: http://localhost:3000 (或 3005，见 docker-compose.yml)
- 后端 API: http://localhost:8000/api
- API 文档: http://localhost:8000/docs
