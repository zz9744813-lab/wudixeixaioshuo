# NovelForge AI

AI 长篇小说自动生产系统（小说锻炉）。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build
docker compose ps
```

访问：

- 前端：http://localhost:3005
- 后端：http://localhost:8000/api
- API 文档：http://localhost:8000/docs

## 开发

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000

cd frontend
npm install
npm run dev
```

## 环境变量

详见 `.env.example`。

## 当前阶段

P0 – 基础骨架。设置页、生产舱、诊断页已就绪。
