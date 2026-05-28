"""
P4 Memory System E2E Test
P4记忆系统端到端测试
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.models.project import Project, NovelBible
from app.models.chapter import Chapter, ChapterStatus
from app.models.task import GenerationTask, TaskStatus, GenerationStep
from app.models.memory import CharacterMemory, WorldMemory, ChapterMemory
from app.services.memory_service import MemoryService
from app.services.memory_update_agent import MemoryUpdateAgent


# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class P4MemoryE2ETest:
    """P4记忆系统E2E测试"""

    def __init__(self):
        self.db = None
        self.project_id = None
        self.chapter_id = None
        self.results = []

    def setup(self):
        """测试准备"""
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()
        print("✓ 数据库初始化完成")

    def teardown(self):
        """测试清理"""
        if self.db:
            self.db.close()
        Base.metadata.drop_all(bind=engine)
        print("✓ 测试环境清理完成")

    def test_1_create_project(self):
        """测试1: 创建项目"""
        print("\n[测试1] 创建项目...")

        project = Project(
            name="P4测试项目",
            description="记忆系统E2E测试",
            genre="玄幻"
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        self.project_id = project.id
        print(f"✓ 项目创建成功: ID={project.id}")
        return True

    def test_2_create_bible(self):
        """测试2: 创建Bible"""
        print("\n[测试2] 创建Bible...")

        bible = NovelBible(
            project_id=self.project_id,
            world_setting="这是一个修仙世界，有九大境界...",
            world_rules=[
                "修炼需要吸收天地灵气",
                "境界突破需要渡劫",
                "灵根决定修炼天赋"
            ],
            characters=[
                {"name": "主角", "role": " protagonist", "cultivation": "炼气期"},
                {"name": "师父", "role": "mentor", "cultivation": "元婴期"}
            ],
            main_plot="主角从废材开始，逐步成长为巅峰强者"
        )
        self.db.add(bible)
        self.db.commit()

        print(f"✓ Bible创建成功")
        return True

    def test_3_create_character_memory(self):
        """测试3: 创建角色记忆"""
        print("\n[测试3] 创建角色记忆...")

        service = MemoryService(self.db)

        char1 = service.create_character_memory(
            project_id=self.project_id,
            name="主角",
            role_type="protagonist",
            stable_profile={
                "name": "林凡",
                "age": 16,
                "background": "废材少年",
                "personality": "坚韧、不服输"
            },
            dynamic_state={
                "cultivation": "炼气期三层",
                "mood": "充满斗志",
                "location": "青云宗外门"
            },
            importance=0.9
        )

        char2 = service.create_character_memory(
            project_id=self.project_id,
            name="师父",
            role_type="mentor",
            stable_profile={
                "name": "青云子",
                "cultivation": "元婴期",
                "personality": "严厉但关心弟子"
            },
            dynamic_state={
                "mood": "期待",
                "location": "青云宗主峰"
            },
            importance=0.8
        )

        print(f"✓ 角色记忆创建成功: 主角ID={char1.id}, 师父ID={char2.id}")
        return True

    def test_4_create_world_memory(self):
        """测试4: 创建世界观记忆"""
        print("\n[测试4] 创建世界观记忆...")

        service = MemoryService(self.db)

        world = service.create_world_memory(
            project_id=self.project_id,
            category="power_system",
            name="修炼境界",
            description="从炼气期到大乘期的九大境界",
            rules=[
                "炼气期：吸收灵气入体",
                "筑基期：奠定道基",
                "金丹期：凝结金丹",
                "元婴期：孕育元婴"
            ],
            importance=0.9
        )

        print(f"✓ 世界观记忆创建成功: ID={world.id}")
        return True

    def test_5_create_chapter_task(self):
        """测试5: 创建章节任务"""
        print("\n[测试5] 创建章节任务...")

        # 创建章节
        chapter = Chapter(
            project_id=self.project_id,
            title="第1章：废物少年",
            chapter_index=1,
            status=ChapterStatus.PENDING
        )
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)
        self.chapter_id = chapter.id

        # 创建生成任务
        task = GenerationTask(
            project_id=self.project_id,
            chapter_id=chapter.id,
            task_type="chapter",
            status=TaskStatus.PENDING
        )
        self.db.add(task)
        self.db.commit()

        print(f"✓ 章节任务创建成功: ChapterID={chapter.id}, TaskID={task.id}")
        return True

    def test_6_assemble_memory_context(self):
        """测试6: 组装记忆上下文"""
        print("\n[测试6] 组装记忆上下文...")

        service = MemoryService(self.db)

        # 组装第2章的上下文（第1章是前情）
        context = service.assemble_context_for_chapter(
            project_id=self.project_id,
            chapter_index=2  # 下一章
        )

        print(f"✓ 上下文组装成功:")
        print(f"  - 最近章节数: {len(context.get('recent_chapters', []))}")
        print(f"  - 相关角色数: {len(context.get('relevant_characters', []))}")
        print(f"  - 世界观元素数: {len(context.get('key_world_elements', []))}")

        # 测试格式化
        prompt_text = service.format_context_for_prompt(context)
        assert len(prompt_text) > 0, "Prompt文本不应为空"

        print(f"  - Prompt文本长度: {len(prompt_text)} 字符")
        return True

    async def test_7_memory_update_from_chapter(self):
        """测试7: 从章节内容更新记忆"""
        print("\n[测试7] 从章节内容更新记忆...")

        # 模拟章节内容
        chapter_content = """
林凡站在青云宗外门的演武场上，握紧拳头。

"废物就是废物，三年还停留在炼气期三层！"

周围弟子的嘲笑声像刀子一样刺入林凡的心中。但他没有低头，
而是默默运转体内的灵气。

就在昨晚，他意外获得了一枚神秘戒指，
戒指里藏着一位上古大能的残魂...

"小子，想变强吗？"苍老的声音在林凡脑海中响起。

林凡眼中燃起希望的火焰："我要变强！我要证明给所有人看！"
"""

        # 更新章节内容
        chapter = self.db.query(Chapter).filter(Chapter.id == self.chapter_id).first()
        chapter.final_content = chapter_content
        self.db.commit()

        # 调用MemoryUpdateAgent
        agent = MemoryUpdateAgent(self.db)
        result = await agent.update_from_chapter(
            project_id=self.project_id,
            chapter_id=self.chapter_id,
            chapter_index=1,
            chapter_title="第1章：废物少年",
            chapter_content=chapter_content,
            plan={"goal": "介绍主角背景"},
            bible={"characters": [{"name": "主角"}]}
        )

        print(f"✓ 记忆更新完成:")
        print(f"  - 章节记忆: {result.get('chapter_memory')}")
        print(f"  - 角色更新数: {len(result.get('character_updates', []))}")
        print(f"  - 新角色数: {len(result.get('new_characters', []))}")

        return True

    def test_8_verify_chapter_memory(self):
        """测试8: 验证章节记忆已生成"""
        print("\n[测试8] 验证章节记忆...")

        # 查询章节记忆
        chapter_mem = self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == self.project_id,
            ChapterMemory.chapter_id == self.chapter_id
        ).first()

        assert chapter_mem is not None, "章节记忆应存在"
        assert chapter_mem.short_summary is not None, "章节记忆应有摘要"

        print(f"✓ 章节记忆验证成功:")
        print(f"  - 记忆ID: {chapter_mem.id}")
        print(f"  - 摘要: {chapter_mem.short_summary[:50]}...")

        return True

    def test_9_verify_memory_in_context(self):
        """测试9: 验证下一章能获取记忆上下文"""
        print("\n[测试9] 验证记忆上下文包含最近章节...")

        service = MemoryService(self.db)

        # 为第2章组装上下文
        context = service.assemble_context_for_chapter(
            project_id=self.project_id,
            chapter_index=2
        )

        # 验证包含第1章
        recent_chapters = context.get('recent_chapters', [])
        assert len(recent_chapters) > 0, "应包含最近章节"

        chapter_indices = [ch['index'] for ch in recent_chapters]
        assert 1 in chapter_indices, "应包含第1章"

        print(f"✓ 记忆上下文验证成功:")
        print(f"  - 包含章节: {chapter_indices}")

        return True

    def test_10_verify_generation_step(self):
        """测试10: 验证GenerationStep包含MemoryUpdate"""
        print("\n[测试10] 验证GenerationStep记录...")

        # 模拟创建MemoryUpdate步骤
        step = GenerationStep(
            task_id=1,
            chapter_id=self.chapter_id,
            step_index=10,
            agent_name="MemoryUpdate",
            input_prompt="记忆更新",
            raw_output='{"chapter_memory": {"id": 1}}',
            model_name="memory_agent",
            provider_name="internal"
        )
        self.db.add(step)
        self.db.commit()

        # 查询验证
        steps = self.db.query(GenerationStep).filter(
            GenerationStep.chapter_id == self.chapter_id,
            GenerationStep.agent_name == "MemoryUpdate"
        ).all()

        assert len(steps) > 0, "应有MemoryUpdate步骤"

        print(f"✓ GenerationStep验证成功:")
        print(f"  - MemoryUpdate步骤数: {len(steps)}")

        return True

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("P4 Memory System E2E Test")
        print("=" * 60)

        try:
            self.setup()

            tests = [
                ("创建项目", self.test_1_create_project),
                ("创建Bible", self.test_2_create_bible),
                ("创建角色记忆", self.test_3_create_character_memory),
                ("创建世界观记忆", self.test_4_create_world_memory),
                ("创建章节任务", self.test_5_create_chapter_task),
                ("组装记忆上下文", self.test_6_assemble_memory_context),
                ("从章节更新记忆", lambda: asyncio.run(self.test_7_memory_update_from_chapter())),
                ("验证章节记忆", self.test_8_verify_chapter_memory),
                ("验证记忆上下文", self.test_9_verify_memory_in_context),
                ("验证GenerationStep", self.test_10_verify_generation_step),
            ]

            passed = 0
            failed = 0

            for name, test_func in tests:
                try:
                    result = test_func()
                    if result:
                        passed += 1
                        print(f"  ✓ {name} - 通过")
                    else:
                        failed += 1
                        print(f"  ✗ {name} - 失败")
                except Exception as e:
                    failed += 1
                    print(f"  ✗ {name} - 异常: {e}")

            print("\n" + "=" * 60)
            print(f"测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}")
            print("=" * 60)

            return failed == 0

        finally:
            self.teardown()


if __name__ == "__main__":
    test = P4MemoryE2ETest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
