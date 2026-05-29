"""
P4 Memory Worker E2E Test - 真实闭环验收
验证 Worker 真实生成章节 → 记忆系统自动更新 → 下一章能读取上一章记忆
"""

import asyncio
import sys
import os

# 设置UTF-8编码
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.project import Project, NovelBible
from app.models.chapter import Chapter, ChapterStatus
from app.models.task import GenerationTask, TaskStatus, GenerationStep
from app.models.memory import CharacterMemory, WorldMemory, ChapterMemory
from app.services.memory_service import MemoryService
from app.services.worker_service import WritingWorker

# 使用内存数据库进行测试
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class MockLLMService:
    """Mock LLM 服务 - 用于无 API Key 测试"""

    async def generate(self, prompt: str, role: str = "default", temperature: float = 0.7, **kwargs):
        """模拟 LLM 生成"""
        # 根据角色返回不同的模拟响应
        if role == "planner":
            return {
                "content": '{"goal": "测试章节目标", "plot_points": ["情节点1", "情节点2"], "key_scenes": ["场景1"]}',
                "model": "mock",
                "provider": "mock",
                "input_tokens": 100,
                "output_tokens": 50,
                "duration_seconds": 0.1
            }
        elif role == "draft":
            return {
                "content": '''林凡站在演武场上，握紧拳头。

"废物就是废物！"

周围弟子的嘲笑声不断。但林凡没有低头，
而是默默握紧手中突然出现的神秘戒指。

"小子，想变强吗？"苍老的声音响起。

林凡眼中燃起火焰："我要变强！"''',
                "model": "mock",
                "provider": "mock",
                "input_tokens": 200,
                "output_tokens": 150,
                "duration_seconds": 0.2
            }
        elif role == "critic":
            return {
                "content": '{"score": 85, "breakdown": {"plot": 85, "character": 80}, "suggestions": ["建议1"]}',
                "model": "mock",
                "provider": "mock",
                "input_tokens": 300,
                "output_tokens": 100,
                "duration_seconds": 0.1
            }
        elif role == "continuity":
            return {
                "content": '{"score": 90, "issues": [], "report": "连续性检查通过"}',
                "model": "mock",
                "provider": "mock",
                "input_tokens": 400,
                "output_tokens": 50,
                "duration_seconds": 0.1
            }
        elif role == "learning":
            return {
                "content": '{"techniques": ["技巧1"], "patterns": ["模式1"]}',
                "model": "mock",
                "provider": "mock",
                "input_tokens": 500,
                "output_tokens": 50,
                "duration_seconds": 0.1
            }
        elif role == "memory_update":
            return {
                "content": '''{"short_summary": "林凡获得神秘戒指，决心变强",
"detailed_summary": "林凡在演武场被嘲笑，但意外获得神秘戒指，戒指中藏着上古大能残魂",
"key_events": ["获得神秘戒指", "遇到残魂"],
"character_changes": [{"name": "林凡", "change": "获得神秘戒指"}],
"world_updates": [],
"relationship_changes": [],
"unresolved_questions": ["戒指的来历"],
"foreshadow_updates": []}''',
                "model": "mock",
                "provider": "mock",
                "input_tokens": 600,
                "output_tokens": 100,
                "duration_seconds": 0.1
            }
        else:
            return {
                "content": "Mock response",
                "model": "mock",
                "provider": "mock",
                "input_tokens": 50,
                "output_tokens": 20,
                "duration_seconds": 0.1
            }


class P4MemoryWorkerE2ETest:
    """P4 Memory Worker 真实闭环 E2E 测试"""

    def __init__(self):
        self.db = None
        self.project_id = None
        self.chapter_id = None
        self.task_id = None
        self.use_mock = os.environ.get("MOCK_LLM", "") in ("1", "true", "True", "TRUE")

    def setup(self):
        """测试准备"""
        # 创建所有表
        Base.metadata.create_all(bind=engine)
        self.db = TestingSessionLocal()

        # 如果是 Mock 模式，替换 LLM 服务
        if self.use_mock:
            from app.services import openai_llm_service
            self._original_llm_manager = openai_llm_service.llm_manager
            openai_llm_service.llm_manager = MockLLMService()
            print("✓ Mock LLM 模式已启用")

        print("✓ 数据库初始化完成")

    def teardown(self):
        """测试清理"""
        if self.use_mock:
            from app.services import openai_llm_service
            openai_llm_service.llm_manager = self._original_llm_manager

        if self.db:
            self.db.close()
        Base.metadata.drop_all(bind=engine)
        print("✓ 测试环境清理完成")

    def test_1_create_project(self):
        """1. 创建 Project"""
        print("\n[1] 创建 Project...")

        project = Project(
            name="P4 Worker E2E 测试项目",
            description="真实Worker闭环测试",
            genre="玄幻"
        )
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)

        self.project_id = project.id
        print(f"✓ Project 创建成功: ID={project.id}")
        return True

    def test_2_create_bible(self):
        """2. 创建 NovelBible"""
        print("\n[2] 创建 NovelBible...")

        bible = NovelBible(
            project_id=self.project_id,
            world_setting="这是一个修仙世界，有九大境界...",
            world_rules=["修炼需要吸收天地灵气", "境界突破需要渡劫"],
            characters=[
                {"name": "林凡", "role": "主角", "traits": "坚毅、不屈"},
                {"name": "神秘老者", "role": "导师", "traits": "上古大能残魂"}
            ],
            main_plot="废材少年获得神秘传承，踏上修仙之路",
            chapter_outline=["第1章：获得传承", "第2章：修炼开始"]
        )
        self.db.add(bible)
        self.db.commit()

        print(f"✓ Bible 创建成功")
        return True

    def test_3_create_character_memory(self):
        """3. 创建 CharacterMemory"""
        print("\n[3] 创建 CharacterMemory...")

        service = MemoryService(self.db)

        char1 = service.create_character_memory(
            project_id=self.project_id,
            name="林凡",
            role_type="protagonist",
            stable_profile={"name": "林凡", "traits": "坚毅、不屈"},
            first_chapter=1,
            importance=1.0
        )

        char2 = service.create_character_memory(
            project_id=self.project_id,
            name="神秘老者",
            role_type="mentor",
            stable_profile={"name": "神秘老者", "traits": "上古大能残魂"},
            first_chapter=1,
            importance=0.9
        )

        print(f"✓ CharacterMemory 创建成功: 林凡(ID={char1.id}), 老者(ID={char2.id})")
        return True

    def test_4_create_world_memory(self):
        """4. 创建 WorldMemory"""
        print("\n[4] 创建 WorldMemory...")

        service = MemoryService(self.db)

        world_mem = service.create_world_memory(
            project_id=self.project_id,
            category="realm",
            name="修炼境界",
            description="修仙世界的九大境界体系",
            rules=["炼气", "筑基", "金丹", "元婴", "化神", "渡劫", "大乘", "真仙", "金仙"],
            importance=1.0
        )

        print(f"✓ WorldMemory 创建成功: ID={world_mem.id}")
        return True

    async def test_5_run_worker_execute_task(self):
        """5. 运行真实 Worker _execute_task"""
        print("\n[5] 运行真实 Worker _execute_task...")

        # 创建第 1 章
        chapter = Chapter(
            project_id=self.project_id,
            title="第1章：神秘戒指",
            chapter_index=1,
            status=ChapterStatus.PLANNED
        )
        self.db.add(chapter)
        self.db.commit()
        self.db.refresh(chapter)
        self.chapter_id = chapter.id

        # 创建 GenerationTask
        task = GenerationTask(
            project_id=self.project_id,
            chapter_id=chapter.id,
            task_type="chapter",
            status=TaskStatus.PENDING
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        self.task_id = task.id

        print(f"✓ 第1章和任务创建成功: ChapterID={chapter.id}, TaskID={task.id}")

        # 获取 Project
        project = self.db.query(Project).filter(Project.id == self.project_id).first()

        # 实例化 WritingWorker
        worker = WritingWorker()
        print(f"✓ WritingWorker 实例化成功")

        try:
            # 调用真实的 _execute_task
            result = await worker._execute_task(self.db, task, chapter, project)

            print(f"✓ Worker 执行完成")
            print(f"  - success: {result.get('success')}")
            print(f"  - final_content length: {len(result.get('final_content', ''))}")
            print(f"  - tokens_used: {result.get('tokens_used')}")

            # 验证结果
            assert result.get("success") == True, "Worker 执行应成功"
            assert len(result.get("final_content", "")) > 0, "final_content 不应为空"

            return True
        except Exception as e:
            print(f"✗ Worker 执行失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def test_6_verify_generation_steps(self):
        """6. 验证 GenerationStep 包含所有步骤"""
        print("\n[6] 验证 GenerationStep...")

        steps = self.db.query(GenerationStep).filter(
            GenerationStep.chapter_id == self.chapter_id
        ).order_by(GenerationStep.step_index).all()

        agent_names = [s.agent_name for s in steps]
        print(f"✓ GenerationStep 列表: {agent_names}")

        # 验证必须包含的步骤
        required_steps = ["Planner", "Draft", "Critic", "Continuity", "Learning", "MemoryUpdate"]
        for step_name in required_steps:
            assert step_name in agent_names, f"应有 {step_name} 步骤"
            print(f"  ✓ 包含 {step_name}")

        return True

    def test_7_verify_chapter_memory_created(self):
        """7. 验证 ChapterMemory 自动生成"""
        print("\n[7] 验证 ChapterMemory...")

        chapter_mem = self.db.query(ChapterMemory).filter(
            ChapterMemory.project_id == self.project_id,
            ChapterMemory.chapter_id == self.chapter_id
        ).first()

        assert chapter_mem is not None, "ChapterMemory 应自动生成"

        print(f"✓ ChapterMemory 生成成功:")
        print(f"  - ID: {chapter_mem.id}")
        print(f"  - 摘要: {chapter_mem.short_summary[:100] if chapter_mem.short_summary else '无'}...")
        print(f"  - 关键事件数: {len(chapter_mem.key_events) if chapter_mem.key_events else 0}")

        return True

    def test_8_verify_next_chapter_context(self):
        """8. 验证第 2 章能读取第 1 章记忆"""
        print("\n[8] 验证下一章 Context 包含上一章记忆...")

        memory_service = MemoryService(self.db)
        context = memory_service.assemble_context_for_chapter(
            project_id=self.project_id,
            chapter_index=2
        )

        recent_chapters = context.get("recent_chapters", [])
        print(f"✓ Context 组装成功:")
        print(f"  - 最近章节数: {len(recent_chapters)}")

        # 必须 assert 非空
        assert len(recent_chapters) > 0, "下一章 Context 必须包含上一章记忆"

        chapter_indices = [ch["index"] for ch in recent_chapters]
        print(f"  - 包含章节: {chapter_indices}")
        assert 1 in chapter_indices, "Context 应包含第 1 章"
        assert recent_chapters[0]["index"] == 1, "第 1 章应是最新的章节"

        return True

    def test_9_verify_planner_prompt_has_memory(self):
        """9. 验证 Planner Prompt 包含记忆上下文"""
        print("\n[9] 验证 Planner Prompt 包含记忆上下文...")

        planner_step = self.db.query(GenerationStep).filter(
            GenerationStep.chapter_id == self.chapter_id,
            GenerationStep.agent_name == "Planner"
        ).first()

        assert planner_step is not None, "Planner 步骤应存在"

        prompt = planner_step.input_prompt or ""

        # 验证包含记忆上下文
        has_memory_context = "相关记忆上下文" in prompt
        not_unavailable = "记忆系统暂不可用" not in prompt

        print(f"✓ Planner Prompt 验证:")
        print(f"  - 包含'相关记忆上下文': {has_memory_context}")
        print(f"  - 不含'记忆系统暂不可用': {not_unavailable}")

        # 必须 assert
        assert has_memory_context, "Planner Prompt 必须包含相关记忆上下文"
        assert not_unavailable, "Planner Prompt 不应包含记忆系统暂不可用"

        # 验证包含其他必要元素
        has_bible = "世界观" in prompt or "Bible" in prompt
        print(f"  - 包含世界观/Bible: {has_bible}")

        return True

    def test_10_verify_draft_prompt_has_memory(self):
        """10. 验证 Draft Prompt 包含记忆上下文"""
        print("\n[10] 验证 Draft Prompt 包含记忆上下文...")

        draft_step = self.db.query(GenerationStep).filter(
            GenerationStep.chapter_id == self.chapter_id,
            GenerationStep.agent_name == "Draft"
        ).first()

        assert draft_step is not None, "Draft 步骤应存在"

        prompt = draft_step.input_prompt or ""

        # 验证包含记忆上下文
        has_memory_context = "相关记忆上下文" in prompt
        not_unavailable = "记忆系统暂不可用" not in prompt

        print(f"✓ Draft Prompt 验证:")
        print(f"  - 包含'相关记忆上下文': {has_memory_context}")
        print(f"  - 不含'记忆系统暂不可用': {not_unavailable}")

        # 必须 assert
        assert has_memory_context, "Draft Prompt 必须包含相关记忆上下文"
        assert not_unavailable, "Draft Prompt 不应包含记忆系统暂不可用"

        # 验证包含其他必要元素
        has_plan = "章节规划" in prompt or "plan" in prompt.lower()
        print(f"  - 包含章节规划: {has_plan}")

        # 必须 assert
        assert has_plan, "Draft Prompt 必须包含章节规划"

        return True

    async def test_11_verify_chapter_memory_no_duplicate(self):
        """11. 验证 ChapterMemory 不会重复创建"""
        print("\n[11] 验证 ChapterMemory 不重复...")

        # 查询同一 chapter_id 的 ChapterMemory 数量
        memories = self.db.query(ChapterMemory).filter(
            ChapterMemory.chapter_id == self.chapter_id
        ).all()

        print(f"✓ 首次查询 ChapterMemory 数量: {len(memories)}")
        assert len(memories) == 1, f"同一章节应只有 1 条 ChapterMemory，实际有 {len(memories)} 条"

        # 再次调用 MemoryUpdateAgent.update_from_chapter
        print("✓ 再次调用 MemoryUpdateAgent...")
        from app.services.memory_update_agent import MemoryUpdateAgent
        agent = MemoryUpdateAgent(self.db)

        chapter = self.db.query(Chapter).filter(Chapter.id == self.chapter_id).first()
        await agent.update_from_chapter(
            project_id=self.project_id,
            chapter_id=self.chapter_id,
            chapter_index=1,
            chapter_title="第1章：神秘戒指",
            chapter_content=chapter.final_content or "",
            plan={"goal": "测试重复更新"},
            bible={"characters": [{"name": "林凡"}]}
        )

        # 再次查询，应该还是只有 1 条
        memories = self.db.query(ChapterMemory).filter(
            ChapterMemory.chapter_id == self.chapter_id
        ).all()

        print(f"✓ 再次查询 ChapterMemory 数量: {len(memories)}")
        assert len(memories) == 1, f"重复调用后仍应只有 1 条 ChapterMemory，实际有 {len(memories)} 条"

        return True

    def test_12_verify_continuity_prompt_has_memory(self):
        """12. 验证 Continuity Prompt 包含记忆上下文"""
        print("\n[12] 验证 Continuity Prompt 包含记忆上下文...")

        continuity_step = self.db.query(GenerationStep).filter(
            GenerationStep.chapter_id == self.chapter_id,
            GenerationStep.agent_name == "Continuity"
        ).first()

        assert continuity_step is not None, "Continuity 步骤应存在"

        prompt = continuity_step.input_prompt or ""

        # 验证包含记忆上下文
        has_memory_context = "相关记忆上下文" in prompt
        not_unavailable = "记忆系统暂不可用" not in prompt

        print(f"✓ Continuity Prompt 验证:")
        print(f"  - 包含'相关记忆上下文': {has_memory_context}")
        print(f"  - 不含'记忆系统暂不可用': {not_unavailable}")

        # 必须 assert
        assert has_memory_context, "Continuity Prompt 必须包含相关记忆上下文"
        assert not_unavailable, "Continuity Prompt 不应包含记忆系统暂不可用"

        return True

    def run_all_tests(self):
        """运行所有测试"""
        print("=" * 60)
        print("P4 Memory Worker E2E Test - 真实闭环验收")
        print("=" * 60)
        print(f"Mode: {'MOCK' if self.use_mock else 'REAL'}")

        try:
            self.setup()

            tests = [
                ("创建 Project", self.test_1_create_project),
                ("创建 Bible", self.test_2_create_bible),
                ("创建 CharacterMemory", self.test_3_create_character_memory),
                ("创建 WorldMemory", self.test_4_create_world_memory),
                ("Worker 执行章节生成", lambda: asyncio.run(self.test_5_run_worker_execute_task())),
                ("验证 GenerationStep", self.test_6_verify_generation_steps),
                ("验证 ChapterMemory", self.test_7_verify_chapter_memory_created),
                ("验证下一章 Context", self.test_8_verify_next_chapter_context),
                ("验证 Planner Prompt", self.test_9_verify_planner_prompt_has_memory),
                ("验证 Draft Prompt", self.test_10_verify_draft_prompt_has_memory),
                ("验证不重复创建", lambda: asyncio.run(self.test_11_verify_chapter_memory_no_duplicate())),
                ("验证 Continuity Prompt", self.test_12_verify_continuity_prompt_has_memory),
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
                    import traceback
                    traceback.print_exc()

            print("\n" + "=" * 60)
            if failed == 0:
                print(f"🎉 P4 Memory Worker E2E 全部通过! ({passed}/{len(tests)})")
            else:
                print(f"⚠️ 测试结果: 通过 {passed}/{len(tests)}, 失败 {failed}")
            print("=" * 60)

            return failed == 0

        finally:
            self.teardown()


if __name__ == "__main__":
    test = P4MemoryWorkerE2ETest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
