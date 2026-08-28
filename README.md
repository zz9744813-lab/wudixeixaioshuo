# Novel Genome · 小说基因组计划

**Computational Narrative Science & Story World Modeling Platform**

计算叙事科学与小说世界模型平台。本仓库实现《小说基因组计划 Novel Genome 工程总设计规范 v2.0》的 **Stage 0 / EPIC-A / EPIC-B** 阶段:

- 协议冻结(Scene / Event / Fact / Claim / Evidence / CharacterState / KnowledgeState / RelationshipState / EmotionState / Technique / Hypothesis / Experiment)
- 基础设施(FastAPI 骨架、配置、日志、ID 系统、Run Registry)
- 语料与 Scene Genome 的数据库 Schema(40+ 核心表的 SQLAlchemy 模型 + Alembic 迁移)
- **语料摄入流水线 EPIC-B(规则驱动、无 LLM)**:TXT/MD/EPUB/DOCX 解析 → 章节检测 → 场景切分 → 重复检测 → 持久化为 Book/Chapter/Scene/SceneSpan
- Agent I/O 协议与 ContextPackage 的 Pydantic 契约

> 本阶段**不依赖 LLM**:解析、章节/场景检测、去重、基础 API 均为规则驱动，可在本地用
> SQLite/PostgreSQL 直接跑通。反事实实验、读者模拟、NovelForge 联调等依赖 LLM 的阶段见规范后续 EPIC。

## 架构分层(对应规范 §4)

```
Corpus Layer      → corpus_sources / books / chapters / scenes / scene_spans
Decomposition     → events / perceptions / beliefs / goals
Story World Model → characters / character_states / knowledge_states /
                    relationship_states / emotion_states / facts
Research Layer    → hypotheses / experiments / experiment_variants / artifacts
Evaluation Layer  → evaluations / reader_profiles
Knowledge Layer   → techniques / behavior_patterns / knowledge_rules
Infra             → prompt_registry / model_registry / model_calls /
                    context_packages / runs / tasks / research_edges / benchmarks
```

## 快速开始

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows
pip install -e ".[dev]"

# 本地用 SQLite 验证迁移(无需 PostgreSQL)
cp .env.example .env          # DATABASE_URL 默认指向 sqlite
alembic upgrade head

uvicorn app.main:app --reload --port 8123
# → http://127.0.0.1:8123/docs
```

生产目标数据库为 PostgreSQL(见 `.env.example` 中的 `DATABASE_URL` 示例)。
SQLAlchemy 2.0 async 模型 + Alembic 多后端兼容,迁移在 PostgreSQL 与 SQLite 上均可生成。

## 目录

```
app/
  config.py          # Settings (pydantic-settings)
  main.py            # FastAPI app + 路由装配 + health
  db/                # engine / session / Base
  models/            # SQLAlchemy 模型(按规范分组)
  schemas/           # Pydantic API + Agent 协议契约
  api/               # 路由(Corpus / Scene / Character / Research / Knowledge / NovelForge)
  agents/            # Agent I/O 协议常量与基类
  core/              # ID 系统 / Run Registry
alembic/             # 迁移
tests/               # 冒烟测试
```

## 状态机 / 幂等 / 可追溯

- 任务状态:PENDING→READY→RUNNING→…→SUCCESS/PARTIAL/FAILED_RETRYABLE/FAILED_FINAL/CANCELLED(规范 §33)
- 知识等级:OBSERVATION→CANDIDATE→SUPPORTED→REPLICATED→VALIDATED→PRODUCTION_PROVEN(规范 §26)
- 所有 Run 记录 model / prompt_version / context_package / input / output / schema_version(规范 §35)

## 语料摄入流水线(EPIC-B, 规范 §6)

摄入一个小说文件 → 注册不可变 `CorpusSource` → 解析 → 章节检测 → 场景切分 → 重复检测 →
持久化 `Book` / `Chapter` / `Scene` / `SceneSpan`。全程规则驱动、确定性、可复现。

```
原始字节
  → data/object_store/corpus_sources/<SRC>.<ext>   (不可变原文件副本, §6.3/§38)
  → CorpusSource 行
  → 解析器(TXT/MD/EPUB/DOCX, 仅用标准库)
  → 章节检测(regex + 结构化标题, §7)
  → 场景切分(装饰线 / 时间跳跃 / POV 标记 / 二级标题, §7)
  → 重复检测(精确 + 近似 shingle/Jaccard, §6.2)
  → Book / Chapter / Scene / SceneSpan 行
  → Task 状态机(PENDING→RUNNING→SUCCESS / FAILED→DeadLetter, §33)
  → 幂等(相同字节重复摄入 = 同一 Book, 不产生重复章节)
```

模块:`app/ingest/`(`parsers/`、`chapter_detector.py`、`scene_splitter.py`、`dedup.py`、
`service.py`、`worker.py`)。

摄入 API:

```http
POST /api/v1/corpus/ingest          # 文件 → 新建 CorpusSource + Book + 章节/场景
POST /api/v1/books/{book_id}/ingest # 文件 → 摄入到已有 Book
```

无 LLM 阶段摄入仅完成结构性拆分;人物/情绪/因果等语义分析由后续 EPIC-C 的多轮 Agent 完成。
