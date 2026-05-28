# P3 端到端验收文档

本文档描述完整的系统验收流程，验证从拆书到写作的完整闭环。

## 验收流程

### 1. 配置 OpenAI-compatible 模型

```bash
curl -X POST http://localhost:8000/api/models/configs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI GPT-4",
    "provider": "openai",
    "model": "gpt-4",
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1",
    "is_active": true
  }'
```

**预期结果**: 返回 200，包含配置 ID

### 2. 上传 TXT

```bash
curl -X POST http://localhost:8000/api/books/upload \
  -F "file=@test_novel.txt" \
  -F "title=测试小说" \
  -F "genre=玄幻"
```

**预期结果**:
```json
{
  "id": 1,
  "title": "测试小说",
  "status": "imported",
  "message": "书籍上传成功"
}
```

### 3. 真实分章

```bash
curl -X POST http://localhost:8000/api/books/1/split
```

**预期结果**:
```json
{
  "message": "分章完成，共识别 X 章",
  "total_chapters": 5,
  "total_words": 10000
}
```

### 4. 拆书分析 (analyze)

```bash
curl -X POST http://localhost:8000/api/books/1/analyze
```

**预期结果**:
```json
{
  "message": "分析完成",
  "chapters_analyzed": 5,
  "analysis_summary": {
    "narrative_model": "...",
    "character_model": "...",
    "hooks_count": 10
  }
}
```

**验证数据库**:
```sql
SELECT summary, structure_analysis, character_mentions 
FROM book_chapters WHERE book_id = 1;
-- 应返回非空值
```

### 5. 提取技巧卡 (extract-techniques)

```bash
curl -X POST http://localhost:8000/api/books/1/extract-techniques
```

**预期结果**:
```json
{
  "message": "成功提取 5 个技巧卡片",
  "techniques": [
    {"title": "悬念钩子设计", "category": "hook", "confidence": 0.85},
    {"title": "人物对话技巧", "category": "character", "confidence": 0.82},
    {"title": "情绪节奏控制", "category": "emotion", "confidence": 0.78}
  ]
}
```

**验证要求**: 至少生成 3 张 TechniqueCard

**验证数据库**:
```sql
SELECT COUNT(*) FROM technique_cards WHERE book_id = 1;
-- 应返回 >= 3
```

### 6. 创建小说项目

```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "我的小说",
    "genre": "玄幻",
    "target_length": 100000,
    "description": "这是一个测试项目"
  }'
```

**预期结果**:
```json
{
  "id": 1,
  "title": "我的小说",
  "status": "planning"
}
```

### 7. 绑定技巧卡

```bash
# 获取技巧卡列表
curl http://localhost:8000/api/techniques/

# 绑定到项目 (通过 Playbook)
curl -X POST http://localhost:8000/api/projects/1/playbook \
  -H "Content-Type: application/json" \
  -d '{
    "source_techniques": [1, 2, 3],
    "rules": ["使用悬念钩子", "控制情绪节奏"]
  }'
```

### 8. 创建章节任务

```bash
# 创建章节
curl -X POST http://localhost:8000/api/chapters/ \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "chapter_index": 1,
    "title": "第一章 初入江湖",
    "target_word_count": 3000
  }'

# 创建生成任务
curl -X POST http://localhost:8000/api/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "chapter_id": 1,
    "task_type": "draft",
    "priority": 3
  }'
```

### 9. Worker 执行完整流水线

启动 Worker:
```bash
# 在另一个终端
python -c "
import asyncio
from app.services.worker_service import WritingWorker

worker = WritingWorker()
asyncio.run(worker.start())
"
```

Worker 将自动执行:
1. **Planner**: 使用技巧卡和 Playbook 生成章节规划
2. **Draft**: 根据规划起草内容
3. **Critic**: 多维度审稿评分
4. **Rewrite** (如果需要): 基于反馈改稿
5. **Continuity**: 连续性检查
6. **Learning**: 生成学习总结

### 10. 验证 ChapterVersion

```sql
-- 检查版本记录
SELECT 
  version_number,
  draft_content IS NOT NULL as has_draft,
  final_content IS NOT NULL as has_final,
  total_score,
  is_accepted
FROM chapter_versions 
WHERE chapter_id = 1;
```

**预期结果**:
- 至少 1 个版本
- draft_content 不为空
- final_content 不为空 (接受的版本)
- total_score 有值
- is_accepted = 1 (接受的版本)

### 11. 验证 Darwin 保留/回滚

```sql
-- 检查失败模式记录
SELECT category, symptom, occurrence_count 
FROM failure_patterns 
WHERE project_id = 1;
```

**预期结果**:
- 如果有 Rewrite 失败，应记录 FailurePattern
- occurrence_count >= 1

```sql
-- 检查 Playbook 更新
SELECT rules FROM project_playbooks WHERE project_id = 1;
```

**预期结果**:
- rules 包含从低分维度生成的改进规则

### 12. 验证最终内容

```bash
curl http://localhost:8000/api/chapters/1
```

**预期结果**:
```json
{
  "id": 1,
  "title": "第一章 初入江湖",
  "final_content": "...章节正文内容...",
  "final_word_count": 2800,
  "total_score": 85,
  "status": "completed"
}
```

**验证要求**:
- `final_content` 有实际内容 (> 1000 字)
- `total_score` > 0
- `status` = "completed"

## 自动化测试脚本

运行完整的端到端测试:

```bash
cd backend
python p3_e2e_test.py
```

或手动执行:

```bash
# 1. 启动后端
python -m uvicorn app.main:app --reload --port 8000

# 2. 在另一个终端运行测试
python scripts/e2e_check.py
```

## 验收标准

| 步骤 | 检查项 | 状态 |
|------|--------|------|
| 1 | 模型配置成功 | ⬜ |
| 2 | TXT 上传成功 | ⬜ |
| 3 | 分章成功 (>=2章) | ⬜ |
| 4 | analyze 写回章节字段 | ⬜ |
| 5 | extract-techniques >=3张 | ⬜ |
| 6 | 项目创建成功 | ⬜ |
| 7 | 技巧卡绑定成功 | ⬜ |
| 8 | 章节任务创建成功 | ⬜ |
| 9 | Worker 执行完整流水线 | ⬜ |
| 10 | ChapterVersion 保存成功 | ⬜ |
| 11 | Darwin 保留/回滚逻辑正确 | ⬜ |
| 12 | final_content 有内容 | ⬜ |

**全部通过 = P3 验收成功**

## 问题排查

### Worker 不执行任务
- 检查 GenerationTask 状态是否为 `pending`
- 检查 Worker 是否已启动
- 查看日志: `tail -f backend/logs/worker.log`

### 技巧卡未生成
- 确认书籍已分析 (BookChapter.summary 不为空)
- 检查 LLM 配置是否正确
- 查看 extract-techniques 接口返回的错误信息

### Darwin 未记录失败
- 检查 Rewrite 是否实际执行
- 确认新评分是否低于旧评分
- 查看 failure_patterns 表是否有记录

## 相关文件

- `backend/app/routers/books.py` - 拆书相关接口
- `backend/app/services/worker_service.py` - Worker 实现
- `backend/app/models/technique.py` - TechniqueCard, FailurePattern 模型
- `backend/p3_e2e_test.py` - 自动化测试脚本
