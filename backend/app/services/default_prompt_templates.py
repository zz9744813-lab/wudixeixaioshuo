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
DRAFT_TEMPLATE = """请根据以下规划起草章节内容：

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

写作要求：
- 使用中文写作
- 注意节奏控制
- 对话自然，符合人物当前状态（参考记忆上下文）
- 场景描写生动
- 必须遵守上述技巧卡的使用指令
- 必须避免上述错误模式
- 必须尊重记忆上下文中的人物状态和关系变化
- 避免使用禁止设定: {forbidden_items}

请直接输出章节正文内容："""


# Continuity 默认模板
CONTINUITY_TEMPLATE = """请检查以下章节的连续性：

章节标题: {chapter_title}
章节序号: {chapter_index}

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
6. 潜在问题

请输出检查结果和建议。如检查通过，请说明"通过"。"""


# Critic 默认模板
CRITIC_TEMPLATE = """请对以下章节进行多维度审稿评分：

章节标题: {chapter_title}

章节内容:
{content}

请从以下维度评分（每项满分100）：
1. 剧情推进 (plot_progress)
2. 人物一致性 (character_consistency)
3. 节奏控制 (pacing)
4. 章节钩子 (hook)
5. 情绪回报 (emotional_reward)
6. 文风稳定 (style_consistency)
7. 连续性 (continuity)
8. 信息清晰度 (clarity)
9. 商业可读性 (readability)

请输出：
1. 综合评分（满分100）
2. 各维度得分（JSON格式）
3. 问题列表（如有）
4. 改进建议"""


# Rewrite 默认模板
REWRITE_TEMPLATE = """请根据审稿意见改写文章：

章节标题: {chapter_title}

原内容:
{content}

审稿意见:
{critique}

请输出改写后的完整章节内容，注意：
- 保持原有情节和风格
- 针对审稿意见进行改进
- 提高可读性和流畅度
- 章节字数保持在2000-5000字之间"""


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
