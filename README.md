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

# 2. 启动服务
docker-compose up --build

# 3. 访问
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
┌─────────────────────────────────────────────────────────────┐
│                    前端 (React)                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Dashboard│ │ 项目   │ │ 拆书   │ │ Agent  │           │
│  │ 仪表盘   │ │ 管理   │ │ 学习   │ │ 控制台  │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ REST API
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    后端 (FastAPI)                            │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐           │
│  │ Projects│ │ Books   │ │ Tasks   │ │ Models  │           │
│  │ 项目    │ │ 书籍    │ │ 任务    │ │ 模型配置 │           │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘           │
├─────────────────────────────────────────────────────────────┤
│                    Agents 层                                 │
│  Planner → Draft → Critic → Rewrite → Continuity           │
├─────────────────────────────────────────────────────────────┤
│                    Services 层                               │
│  MockLLM / OpenAI / Anthropic / ...                         │
├─────────────────────────────────────────────────────────────┤
│                    数据层 (SQLite)                           │
│  Projects │ Books │ Chapters │ Tasks │ Techniques          │
└─────────────────────────────────────────────────────────────┘
```

## 功能模块

| 模块 | 描述 | 状态 |
|------|------|------|
| Dashboard | 仪表盘，显示统计信息和快捷入口 | ✅ |
| 拆书学习 | 上传小说，自动分章和分析 | ✅ |
| 技巧库 | 提取的写作技巧和套路 | ✅ |
| 小说项目 | 创建和管理小说项目 | ✅ |
| 24小时写作工厂 | 自动写作循环 | ✅ |
| Agent 控制台 | 三栏式Agent工作台 | ✅ |
| 任务队列 | 查看和管理任务 | ✅ |
| 模型配置中心 | 配置LLM API | ✅ |
| 反馈中心 | 用户反馈和系统反馈 | ✅ |
| 失败模式库 | 进化记录和失败案例 | ✅ |

## 数据库模型

- **Project**: 小说项目
- **NovelBible**: 小说圣经（世界观、人物设定）
- **Book**: 导入的书籍
- **BookChapter**: 书籍章节
- **Chapter**: 小说章节（生成的）
- **GenerationTask**: 生成任务
- **GenerationStep**: 生成步骤（记录Agent过程）
- **TechniqueCard**: 技巧卡
- **ModelProvider**: 模型提供商
- **Feedback**: 反馈
- **EvolutionRun**: 进化记录

## 开发阶段

### Phase 1: 项目骨架 ✅
- [x] FastAPI 后端
- [x] SQLite 数据库
- [x] 所有数据库模型
- [x] MockLLMService
- [x] React 前端
- [x] Docker 配置
- [x] 基础 Dashboard

### Phase 2: 模型配置中心 ✅
- [x] Provider CRUD
- [x] API Key 加密存储
- [x] 模型角色映射
- [x] 连接测试

### Phase 3: 拆书学习模块 ✅
- [x] 文件上传（TXT/MD）
- [x] 自动分章
- [x] 章节摘要
- [x] 技巧卡提取

### Phase 4-8: 待开发
- 小说 Bible 与大纲
- 章节生成流水线
- 24小时任务循环
- 反馈与进化
- 体验优化

## API 端点

### Dashboard
- `GET /api/dashboard/stats` - 获取统计数据
- `GET /api/dashboard/recent-activity` - 获取最近活动

### Projects
- `GET /api/projects/` - 项目列表
- `POST /api/projects/` - 创建项目
- `GET /api/projects/{id}` - 项目详情
- `PUT /api/projects/{id}` - 更新项目
- `DELETE /api/projects/{id}` - 删除项目
- `POST /api/projects/{id}/start` - 启动项目
- `POST /api/projects/{id}/pause` - 暂停项目

### Books
- `GET /api/books/` - 书籍列表
- `POST /api/books/upload` - 上传书籍
- `GET /api/books/{id}` - 书籍详情
- `POST /api/books/{id}/split` - 分章
- `POST /api/books/{id}/analyze` - 分析

### Agents
- `GET /api/agents/status` - Agent 状态
- `POST /api/agents/generate-chapter` - 生成章节

### Tasks
- `GET /api/tasks/` - 任务列表
- `POST /api/tasks/` - 创建任务
- `GET /api/tasks/{id}` - 任务详情
- `POST /api/tasks/{id}/cancel` - 取消任务
- `POST /api/tasks/{id}/retry` - 重试任务

## 技术栈

- **后端**: Python 3.11, FastAPI, SQLAlchemy, SQLite
- **前端**: React 18, React Router, CSS3
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
│   │   │   ├── task.py
│   │   │   └── ...
│   │   ├── routers/             # API 路由
│   │   │   ├── dashboard.py
│   │   │   ├── projects.py
│   │   │   └── ...
│   │   └── services/            # 服务层
│   │       ├── llm_service.py
│   │       └── mock_llm_service.py
│   ├── requirements.txt
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/          # React 组件
│   │   ├── pages/               # 页面组件
│   │   ├── services/            # API 服务
│   │   ├── App.js
│   │   └── index.js
│   └── package.json
├── data/                        # 数据目录
│   ├── uploads/                 # 上传文件
│   ├── artifacts/               # 生成产物
│   └── novel_agent.db           # SQLite 数据库
├── docker/
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
├── docker-compose.yml
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
5. 映射模型角色（Planner/Draft/Critic/...）

### 环境变量

```bash
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
4. **日志**: 运行日志保存在 `./data/logs/`

## 贡献

欢迎提交 Issue 和 PR！

## 许可证

MIT License
