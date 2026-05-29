# 24小时小说 Agent 工作台

> 拆书学习 + 自动写作 + 自我进化的小说创作系统

## 项目简介

这是一个面向小说创作者的 AI Agent 工作台，核心能力包括：

1. **拆书学习模块**：上传小说后，系统自动拆解作品结构，提取可迁移的写作技巧
2. **24小时写作 Agent**：自动规划、生成、审稿、改稿、续写、复盘
3. **自我进化机制**：通过评分、反馈持续学习进步

## 快速开始

### 方式一：使用 Docker（推荐）

```bash
# 1. 确保已安装 Docker 和 Docker Compose

# 2. 配置环境变量（重要！）
cp .env.example .env
# 编辑 .env 文件，设置 APP_SECRET_KEY（用于加密 API Key）
# 生成密钥: openssl rand -hex 32

# 3. 启动服务
docker-compose up --build

# 4. 访问
# 前端: http://localhost:3000
# 后端 API: http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### 方式二：本地运行

```bash
# 1. 后端
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000

# 2. 前端（新开终端）
cd frontend
npm install
npm start
```

## 系统架构

```
+------------------------------------------------------------------+
|                         前端 (React)                              |
|  +------------+  +------------+  +------------+  +------------+ |
|  | Dashboard  |  |   项目     |  |   拆书     |  |   Bible    | |
|  |   仪表盘   |  |   管理     |  |   学习     |  |   编辑器   | |
|  +------------+  +------------+  +------------+  +------------+ |
|  +------------+  +------------+  +------------+  +------------+ |
|  | 写作工厂   |  |   Worker   |  |  Agent     |  |  Darwin    | |
|  | 章节流水线 |  | 自动控制台 |  | 控制台    |  | 进化中心   | |
|  +------------+  +------------+  +------------+  +------------+ |
|  +------------+  +------------+  +----------------------------+ |
|  | 反馈中心   |  | 导出中心   |  |       模型配置中心         | |
|  +------------+  +------------+  +----------------------------+ |
+------------------------------------------------------------------+
                              |
                              | REST API
                              v
+------------------------------------------------------------------+
|                        后端 (FastAPI)                             |
|  +-------------+  +-------------+  +-------------+  +-----------+|
|  |   Projects  |  |    Books    |  |   Chapters  |  |   Bible   ||
|  |    项目     |  |    书籍     |  |    章节     |  |   设定    ||
|  +-------------+  +-------------+  +-------------+  +-----------+|
+------------------------------------------------------------------+
|                         Agents 层                                 |
|   Planner -> Draft -> Critic -> Rewrite -> Continuity           |
|   (规划)   (起草)   (审核)   (改写)     (连续性)                |
+------------------------------------------------------------------+
|                       Services 层                                 |
|   MockLLM / OpenAI / Anthropic / Azure / Custom API             |
+------------------------------------------------------------------+
|                       数据层 (SQLite)                             |
|   Projects | Books | Chapters | Bible | Feedback | Evolution    |
+------------------------------------------------------------------+
```

## 功能模块

| 模块 | 描述 | 状态 |
|------|------|------|
| Dashboard | 仪表盘，显示统计信息和快捷入口 | |
| 拆书学习 | 上传小说，自动分章和分析，提取技巧 | |
| 技巧库 | 提取的写作技巧和套路库 | |
| 小说项目 | 创建和管理小说项目 | |
| Bible编辑器 | 世界观、人物、大纲管理 | |
| 写作流水线 | 5步章节生成流程 | |
| 24h自动写作 | Worker后台循环自动写作 | |
| Agent控制台 | 多Agent协作控制 | |
| 任务队列 | 查看和管理任务状态 | |
| 模型配置 | 配置LLM API和角色映射 | |
| 反馈中心 | 多维度反馈收集和统计 | |
| Darwin进化 | 自我进化机制，A/B测试 | |
| 导出中心 | 支持多种格式导出小说 | |

## 开发阶段

### Phase 1: 项目骨架 
- [x] FastAPI 后端
- [x] SQLite 数据库
- [x] 所有数据库模型
- [x] MockLLMService
- [x] React 前端
- [x] Docker 配置
- [x] 基础 Dashboard

### Phase 2: 拆书学习模块 
- [x] 文件上传（TXT/MD）
- [x] 自动分章
- [x] 章节摘要
- [x] 技巧卡提取

### Phase 3: 多 Agent 框架 
- [x] Planner Agent
- [x] Draft Agent
- [x] Critic Agent
- [x] Rewrite Agent
- [x] Continuity Agent

### Phase 4: 小说 Bible 与大纲 
- [x] 世界观设定管理
- [x] 人物档案管理
- [x] 大纲编辑
- [x] AI辅助生成

### Phase 5: 章节生成流水线 
- [x] 5步写作流程
- [x] 多维度评分
- [x] 自动重写循环
- [x] 版本管理

### Phase 6: 24小时自动写作 
- [x] Worker后台调度器
- [x] 任务队列管理
- [x] 每日目标/预算控制
- [x] 自动触发下一章

### Phase 7: 反馈与进化 
- [x] 多维度反馈收集
- [x] AI自动分析
- [x] Darwin进化引擎
- [x] A/B测试
- [x] 最佳实践库

### Phase 8: 导出功能 
- [x] 支持 Markdown/TXT/DOCX/EPUB/PDF/JSON
- [x] 字数统计
- [x] 导出历史管理
- [x] 章节筛选

## API 端点概览

| 模块 | 端点前缀 | 主要功能 |
|------|----------|----------|
| Dashboard | `/api/dashboard` | 统计数据、最近活动 |
| 项目 | `/api/projects` | CRUD、启动/暂停 |
| Bible | `/api/bible` | 设定管理 |
| 章节 | `/api/chapters` | 生成、状态 |
| Agent | `/api/agents` | 状态、生成控制 |
| Worker | `/api/worker` | 自动写作控制 |
| 任务 | `/api/tasks` | 队列管理 |
| 模型 | `/api/models` | 配置管理 |
| 反馈 | `/api/feedback` | 反馈管理、统计 |
| 进化 | `/api/evolution` | Darwin进化 |
| 导出 | `/api/export` | 多格式导出 |

## 技术栈

- **后端**: Python 3.11, FastAPI, SQLAlchemy, SQLite
- **前端**: React 18, Material-UI, React Router
- **部署**: Docker, Docker Compose

## 目录结构

```
novel-agent-workbench/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── database.py          # 数据库配置
│   │   ├── models/              # 数据模型
│   │   │   ├── project.py
│   │   │   ├── book.py
│   │   │   ├── chapter.py
│   │   │   ├── bible.py
│   │   │   ├── feedback.py
│   │   │   └── evolution.py
│   │   ├── routers/             # API 路由
│   │   │   ├── projects.py
│   │   │   ├── books.py
│   │   │   ├── chapters.py
│   │   │   ├── bible.py
│   │   │   ├── worker.py
│   │   │   ├── feedback.py
│   │   │   ├── evolution.py
│   │   │   └── export.py
│   │   └── services/            # 服务层
│   │       ├── llm_service.py
│   │       ├── mock_llm_service.py
│   │       ├── bible_service.py
│   │       ├── writing_pipeline_service.py
│   │       ├── worker_service.py
│   │       ├── feedback_service.py
│   │       ├── evolution_service.py
│   │       └── export_service.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # React 组件
│   │   ├── pages/               # 页面组件
│   │   │   ├── Dashboard.js
│   │   │   ├── Projects.js
│   │   │   ├── BibleEditor.js
│   │   │   ├── WritingFactory.js
│   │   │   ├── WorkerDashboard.js
│   │   │   ├── FeedbackCenter.js
│   │   │   ├── EvolutionCenter.js
│   │   │   └── ExportPage.js
│   │   ├── App.js
│   │   └── index.js
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── exports/                     # 导出文件目录
└── README.md
```

## 配置说明

### 模型配置

系统不预置任何 API Key，需要用户自行配置：

1. 进入「模型配置中心」
2. 添加 Provider：
   - OpenAI
   - Anthropic
   - Gemini
   - OpenRouter
   - 自定义 OpenAI 兼容 API
3. 配置 Base URL 和 API Key
4. 测试连接
5. 映射模型角色（Planner/Draft/Critic/Rewrite/Continuity）

### 环境变量

```bash
# 安全密钥（必填）- 用于加密存储 LLM API Key
# 生产环境必须设置强随机密钥，生成: openssl rand -hex 32
APP_SECRET_KEY=your-secret-key-here

# 后端
DATABASE_URL=sqlite:///data/novel_agent.db
UPLOAD_DIR=/app/data/uploads
ARTIFACTS_DIR=/app/data/artifacts

# 前端
REACT_APP_API_URL=http://localhost:8000/api
```

## 注意事项

1. **Mock 模式**: 未配置 API 时，系统自动使用 MockLLMService 生成模拟内容
2. **API Key 安全**: API Key 加密存储，前端只显示掩码
3. **数据目录**: 所有数据保存在 `./data/` 目录
4. **导出目录**: 导出文件保存在 `./exports/` 目录

## 贡献

欢迎提交 Issue 和 PR！

## 许可证

MIT License
