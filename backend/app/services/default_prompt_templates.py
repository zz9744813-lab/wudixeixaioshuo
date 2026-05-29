"""
Default Prompt Templates - 默认Prompt模板种子数据
首次启动时自动创建默认模板
"""

from sqlalchemy.orm import Session
from app.models.prompt_template import PromptTemplate
from app.utils.time_utils import utc_now


# Planner 默认模板
PLANNER_TEMPLATE = """请为以下章节进行详细规划：

章节标题: {chapter_title}
章节序号: {chapter_index}

世界观设定:
{world_setting}

人物设定:
{characters}

主线剧情:
{main_plot}

章纲:
{chapter_outline}

## 相关记忆上下文
{memory_context}

{tech_instructions}

{failure_warnings}

写作手册规则:
{playbook_rules}

风格约束:
{style_boundaries}

语气指导:
{tone_guidelines}

## 风格档案约束（重要）
{style_rules}

请输出：
1. 本章目标
2. 冲突设计（外部冲突、内部冲突）
3. 人物安排（参考记忆上下文中的人物状态）
4. 章节钩子（开头钩子、结尾钩子）
5. 情绪节奏设计
6. 关键剧情点（3-5个）
7. 要使用的技巧卡（列出具体技巧名称）
8. 要避免的错误模式（列出具体预防措施）
9. 需要回顾的前文伏笔（基于记忆上下文）"""


# Draft 默认模板
DRAFT_TEMPLATE = """请根据以下规划起草章节内容。

## 硬性长度要求（必须遵守）
- 目标字数：{target_words} 中文字
- 合格范围：{min_words} - {max_words} 中文字
- 如果内容不足，不允许用总结式结尾凑数，必须扩展冲突、动作、对话或心理变化
- 禁止使用"总之"、"综上所述"等总结性词语草草收尾

章节标题: {chapter_title}
章节序号: {chapter_index}

章节规划:
{chapter_plan}

## 相关记忆上下文（必读）
{memory_context}

世界观设定:
{world_setting}

人物设定:
{characters}

风格边界:
{style_boundaries}

{tech_instructions}

{failure_warnings}

写作手册规则:
{playbook_rules}

风格约束:
{style_boundaries}

语气指导:
{tone_guidelines}

## 风格档案写作指导（必须遵守）
{style_rules}

写作要求：
- 使用中文写作
- **严格遵守风格档案的字数要求**
- **严格执行爽点曲线规划（如为爽点章节必须达到情绪高潮）**
- **按照风格档案的节奏模板控制章节节奏**
- 注意节奏控制
- 对话自然，符合人物当前状态（参考记忆上下文）
- 场景描写生动
- 必须遵守上述技巧卡的使用指令
- 必须避免上述错误模式
- 必须尊重记忆上下文中的人物状态和关系变化
- 避免使用禁止设定: {forbidden_items}
- 必须达到字数要求，否则需要扩展内容

请直接输出章节正文内容："""


# Continuity 默认模板
CONTINUITY_TEMPLATE = """请检查以下章节的连续性。

章节标题: {chapter_title}
章节序号: {chapter_index}

{f"上一章结尾（本章必须承接）：\n{previous_ending}\n\n" if previous_ending else ""}
{f"待解悬念（本章必须回应或延续）：\n{open_hooks}\n\n" if open_hooks else ""}

章节内容:
{content_preview}

人物设定:
{characters}

伏笔列表:
{foreshadowing}

## 相关记忆上下文
{memory_context}

请检查：
1. 人设一致性（对照记忆上下文中的人物状态）
2. 设定一致性（对照世界观记忆）
3. 时间线连续性（对照最近章节摘要）
4. 伏笔回收情况
5. 与记忆上下文的一致性
{f"6. 上一章衔接：本章开头是否自然承接上一章结尾？是否回应了待解悬念？（重要）" if chapter_index > 1 else ""}
7. 潜在问题

{f"特别要求：\n- 本章开头必须自然承接上一章结尾\n- 必须回应或延续上一章留下的悬念\n- 不允许像新故事一样重新开场\n" if chapter_index > 1 else ""}

请输出检查结果和建议。如检查通过，请说明"通过"。"""


# Critic 默认模板
CRITIC_TEMPLATE = """请对以下章节进行严格的多维度审稿评分。

章节标题: {chapter_title}

章节内容:
{content}

请严格按照以下九维 Rubric 进行评分，每维度必须引用原文证据。

## 评分锚点（Rubric）

### 1. 剧情推进 (plot_progress, 满分100)
- 90: 主线显著推进，有明确的冲突升级和剧情转折
- 70: 主线有推进，但节奏平缓或转折力度不足
- 50: 推进有限，信息重复或原地踏步
- 30: 无明显推进，读者无法获得新信息

### 2. 节奏控制 (pacing, 满分100)
- 90: 信息密度高，冲突推进和喘息段落张弛有度，无明显注水
- 70: 整体流畅，但存在 1-2 处可压缩段落
- 50: 多处重复解释或情绪停滞，影响阅读推进
- 30: 章节缺乏推进，主要由说明、回忆、重复心理活动构成

### 3. 人物一致性 (character_consistency, 满分100)
- 90: 所有角色言行符合设定，情绪转变有充分铺垫
- 70: 主角一致，配角偶有偏差，情绪转变略快
- 50: 存在人设偏离或 OOC（Out of Character）现象
- 30: 人物行为逻辑混乱，读者无法理解动机

### 4. 对话辨识度 (dialogue_distinction, 满分100)
- 90: 每个角色语言风格独特，即使不标注也能分辨说话人
- 70: 主角有辨识度，配角区分度一般
- 50: 对话风格趋同，多个角色说话方式类似
- 30: 所有角色说话一个调，如同同一个人

### 5. 爽点达成度 (payoff_delivery, 满分100)
- 90: 爽点设计精巧，铺垫充分，释放时机精准，情绪到位
- 70: 有爽点但铺垫不足或释放略显仓促
- 50: 爽点平淡，缺乏高潮感，或强行塞入
- 30: 无爽点或爽点与主线无关

### 6. 章末钩子 (ending_hook, 满分100)
- 90: 钩子强烈，引发强烈追更欲望，与下一章紧密关联
- 70: 有悬念但力度中等，读者有一定期待
- 50: 钩子弱或过于套路，读者兴趣不大
- 30: 无钩子，章节结束得过于"圆满"

### 7. 文风稳定性 (style_stability, 满分100)
- 90: 全文风格统一，用词、句式、描写手法一致
- 70: 整体统一，偶有段落风格偏离
- 50: 前后风格明显不一致，仿佛不同作者
- 30: 风格混乱，影响阅读体验

### 8. 连续性/设定一致 (continuity, 满分100)
- 90: 无设定冲突，伏笔呼应到位，与前文衔接流畅
- 70:  minor 设定问题但不影响理解
- 50: 存在设定矛盾或伏笔丢失
- 30: 严重设定冲突或逻辑错误

### 9. 商业可读性 (commercial_readability, 满分100)
- 90: 开头抓人，节奏明快，有追更动力，符合网文套路但不俗套
- 70: 可读性良好，但缺乏亮点
- 50: 平铺直叙，缺乏吸引力
- 30: 晦涩难懂或过于文艺，不符合网文调性

## 输出要求（严格 JSON 格式）

必须输出以下结构的 JSON，不要 Markdown 代码块标记，不要解释：

{
  "overall_score": 78,
  "dimension_scores": {
    "plot_progress": 80,
    "pacing": 72,
    "character_consistency": 75,
    "dialogue_distinction": 62,
    "payoff_delivery": 70,
    "ending_hook": 85,
    "style_stability": 77,
    "continuity": 90,
    "commercial_readability": 76
  },
  "anchored_comments": {
    "pacing": "按 rubric 属于 70 档：整体流畅，但中段重复解释主角动机。",
    "dialogue_distinction": "按 rubric 属于 50 档：配角对话风格趋同，建议为每个主要配角设计独特的口头禅或句式。"
  },
  "line_comments": [
    {
      "quote": "原文短句，不超过 60 字",
      "line_number": 123,
      "issue_type": "telling_not_showing",
      "severity": "medium",
      "comment": "这里直接说明情绪，建议改成动作和对话体现。",
      "rewrite_suggestion": "建议改写方向"
    }
  ],
  "must_fix_items": [
    "问题1: 描述...",
    "问题2: 描述..."
  ],
  "nice_to_have_items": [
    "建议1: 描述..."
  ],
  "rewrite_plan": [
    "第1轮：修复设定冲突和连续性问题",
    "第2轮：加强爽点铺垫和释放",
    "第3轮：优化对话辨识度"
  ]
}

要求：
1. 每个低于 70 分的维度必须在 anchored_comments 中解释原因，并引用 rubric 档位
2. line_comments 至少包含 3-5 条，引用具体原文片段作为证据
3. must_fix_items 按优先级排序，必须是具体可执行的问题
4. rewrite_plan 必须是分轮次的改稿策略
5. 泛泛建议如"提高可读性"应被拆分为具体项"


# Rewrite 默认模板
REWRITE_TEMPLATE = """请根据审稿意见改写文章。

章节标题: {chapter_title}

## 必须修复的问题
{must_fix_items}

## 行级批注
{line_comments}

## 改稿计划
{rewrite_plan}

原内容:
{content}

请输出改写后的完整章节内容，注意：
- 保持原有情节和风格
- 针对审稿意见进行改进
- 提高可读性和流畅度
- 章节字数保持在目标范围内"""


# Learning 默认模板
LEARNING_TEMPLATE = """请总结本章写作过程的经验：

章节标题: {chapter_title}

写作流程回顾:
{steps_summary}

请提取：
1. 本章成功经验
2. 改进空间
3. 可复用的技巧（3-5个技巧卡片）"""


# Memory Update 默认模板
MEMORY_UPDATE_TEMPLATE = """请分析以下章节内容，提取关键记忆信息：

章节标题: {chapter_title}
章节序号: {chapter_index}

章节内容:
{chapter_content}

章节规划:
{chapter_plan}

请提取：
1. 章节摘要（200字以内）
2. 关键事件（2-5个）
3. 人物状态变化
4. 新出现的人物
5. 世界观设定揭示
6. 伏笔设置或回收"""


DEFAULT_TEMPLATES = [
    {
        "role": "planner",
        "name": "Planner 默认模板",
        "content": PLANNER_TEMPLATE,
        "description": "章节规划Agent的默认模板",
    },
    {
        "role": "draft",
        "name": "Draft 默认模板",
        "content": DRAFT_TEMPLATE,
        "description": "起草Agent的默认模板",
    },
    {
        "role": "continuity",
        "name": "Continuity 默认模板",
        "content": CONTINUITY_TEMPLATE,
        "description": "连续性检查Agent的默认模板",
    },
    {
        "role": "critic",
        "name": "Critic 默认模板",
        "content": CRITIC_TEMPLATE,
        "description": "审稿Agent的默认模板",
    },
    {
        "role": "rewrite",
        "name": "Rewrite 默认模板",
        "content": REWRITE_TEMPLATE,
        "description": "改写Agent的默认模板",
    },
    {
        "role": "learning",
        "name": "Learning 默认模板",
        "content": LEARNING_TEMPLATE,
        "description": "学习Agent的默认模板",
    },
    {
        "role": "memory_update",
        "name": "MemoryUpdate 默认模板",
        "content": MEMORY_UPDATE_TEMPLATE,
        "description": "记忆更新Agent的默认模板",
    },
]


def seed_default_prompt_templates(db: Session):
    """初始化默认Prompt模板"""
    for template_data in DEFAULT_TEMPLATES:
        # 检查是否已存在该角色的活跃模板
        existing = db.query(PromptTemplate).filter(
            PromptTemplate.role == template_data["role"],
            PromptTemplate.project_id == None,
            PromptTemplate.is_active == 1,
        ).first()

        if existing:
            # 已存在，跳过
            continue

        # 创建新模板
        template = PromptTemplate(
            role=template_data["role"],
            name=template_data["name"],
            version=1,
            content=template_data["content"],
            description=template_data["description"],
            is_active=1,
            project_id=None,
            created_at=utc_now(),
            updated_at=utc_now(),
        )
        db.add(template)
        print(f"[Seed] 创建默认模板: {template_data['role']} - {template_data['name']}")

    db.commit()
    print("[Seed] 默认Prompt模板初始化完成")
