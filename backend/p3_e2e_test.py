"""
P3 端到端验收测试脚本 - 修复版

完整测试流程:
1. 配置模型 (POST /api/models/quick-setup)
2. 上传 TXT
3. 真实分章
4. 拆书分析 (analyze 写回章节字段)
5. 提取技巧卡 (extract-techniques >=3张)
6. 创建小说项目 (name/total_word_goal)
7. 绑定技巧卡到项目 (POST /api/projects/{id}/playbook)
8. 生成 Bible
9. 创建章节任务
10. 启动 Worker 执行完整流水线
11. 轮询验证任务完成
12. 验证 ChapterVersion / final_content / Darwin记录

使用方法:
1. 确保后端服务已启动: python -m uvicorn app.main:app --reload --port 8000
2. 运行测试: python p3_e2e_test.py
"""

import requests
import json
import time
import os
import sys

BASE_URL = "http://localhost:8000/api"
TEST_TXT_CONTENT = """
第一章 初入江湖

李青云站在山门前，望着眼前云雾缭绕的群山，心中涌起一股豪情。

"终于来到天剑宗了！"他握紧拳头，眼中闪烁着坚定的光芒。

三年前，他还是一个小村庄的普通少年，直到那个血色的夜晚...

"小子，让开！"一个粗犷的声音打断了他的回忆。

李青云回头，只见一个身材魁梧的大汉正不耐烦地看着他。

"这位大哥，请问报名处在哪里？"李青云恭敬地问道。

大汉上下打量了他一眼，嗤笑道："就你也想加入天剑宗？别做梦了！"

李青云没有反驳，只是默默地记住了这个羞辱。

总有一天，我会让所有人刮目相看！

第二章 考核开始

天剑宗的考核分为三关：资质测试、心性考验、实战比试。

李青云站在资质测试的石碑前，深吸一口气，将手放了上去。

石碑发出淡淡的光芒...
"""

# 全局变量存储测试数据
test_data = {
    "provider_id": None,
    "book_id": None,
    "project_id": None,
    "chapter_id": None,
    "task_id": None,
    "technique_ids": [],
}


def test_1_model_config():
    """测试1: 配置模型 - 使用 quick-setup"""
    print("\n" + "="*50)
    print("测试1: 配置模型 (POST /api/models/quick-setup)")
    print("="*50)

    # 使用 quick-setup 一键配置
    resp = requests.post(f"{BASE_URL}/models/quick-setup", json={
        "name": "测试配置",
        "provider_type": "openai",
        "base_url": "https://api.openai.com/v1",
        "api_key": "sk-test-key",
        "default_model": "gpt-3.5-turbo"
    })

    if resp.status_code == 200:
        data = resp.json()
        test_data["provider_id"] = data.get("provider_id")
        print(f"[OK] 模型配置成功, provider_id: {test_data['provider_id']}")
        print(f"  配置了 {len(data.get('roles_configured', []))} 个角色")
        return True
    else:
        print(f"[FAIL] 模型配置失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_2_upload_book():
    """测试2: 上传 TXT"""
    print("\n" + "="*50)
    print("测试2: 上传 TXT")
    print("="*50)

    # 创建测试文件
    test_file = "test_book.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(TEST_TXT_CONTENT)

    # 上传
    with open(test_file, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/books/upload",
            files={"file": ("test_book.txt", f, "text/plain")},
            data={"title": "测试小说", "genre": "玄幻"}
        )

    # 删除测试文件
    os.remove(test_file)

    if resp.status_code == 200:
        data = resp.json()
        test_data["book_id"] = data.get("id")
        print(f"[OK] 上传成功, book_id: {test_data['book_id']}")
        return True
    else:
        print(f"[FAIL] 上传失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_3_split_book():
    """测试3: 真实分章"""
    print("\n" + "="*50)
    print("测试3: 真实分章")
    print("="*50)

    book_id = test_data.get("book_id")
    if not book_id:
        print("[SKIP] 没有 book_id")
        return False

    resp = requests.post(f"{BASE_URL}/books/{book_id}/split")
    if resp.status_code == 200:
        data = resp.json()
        chapters = data.get("total_chapters", 0)
        print(f"[OK] 分章完成, 共 {chapters} 章")
        return chapters > 0
    else:
        print(f"[FAIL] 分章失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_4_analyze_book():
    """测试4: 拆书分析 - 验证写回章节字段"""
    print("\n" + "="*50)
    print("测试4: 拆书分析 (analyze 写回章节字段)")
    print("="*50)

    book_id = test_data.get("book_id")
    if not book_id:
        print("[SKIP] 没有 book_id")
        return False

    resp = requests.post(f"{BASE_URL}/books/{book_id}/analyze")
    if resp.status_code == 200:
        data = resp.json()
        chapters_analyzed = data.get("analysis_summary", {}).get("chapters_analyzed", 0)
        print(f"[OK] 分析完成, 分析了 {chapters_analyzed} 章")

        # 验证章节字段
        resp2 = requests.get(f"{BASE_URL}/books/{book_id}")
        if resp2.status_code == 200:
            book_data = resp2.json()
            chapters = book_data.get("chapters", [])
            if chapters:
                ch = chapters[0]
                has_summary = ch.get("summary") is not None
                has_structure = ch.get("structure_analysis") is not None
                print(f"  - summary: {'有' if has_summary else '无'}")
                print(f"  - structure_analysis: {'有' if has_structure else '无'}")
                return chapters_analyzed > 0 and has_summary
        return chapters_analyzed > 0
    else:
        print(f"[FAIL] 分析失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_5_extract_techniques():
    """测试5: 提取技巧卡 - 必须生成 >=3 张"""
    print("\n" + "="*50)
    print("测试5: 提取技巧卡 (POST /api/books/{id}/extract-techniques)")
    print("="*50)

    book_id = test_data.get("book_id")
    if not book_id:
        print("[SKIP] 没有 book_id")
        return False

    resp = requests.post(f"{BASE_URL}/books/{book_id}/extract-techniques")
    if resp.status_code == 200:
        data = resp.json()
        techniques = data.get("techniques", [])
        print(f"[OK] 提取 {len(techniques)} 张技巧卡")
        for t in techniques[:3]:
            print(f"  - {t.get('title')} ({t.get('category')}, 置信度: {t.get('confidence')})")

        # 存储技巧卡ID用于后续绑定
        test_data["technique_ids"] = [t.get("id") for t in techniques if t.get("id")]

        return len(techniques) >= 3
    else:
        print(f"[FAIL] 提取失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_6_create_project():
    """测试6: 创建小说项目 - 使用正确字段"""
    print("\n" + "="*50)
    print("测试6: 创建小说项目 (name/total_word_goal)")
    print("="*50)

    resp = requests.post(f"{BASE_URL}/projects/", json={
        "name": "测试项目",
        "genre": "玄幻",
        "description": "这是一个测试项目",
        "total_word_goal": 100000,
        "daily_word_goal": 3000,
        "chapter_word_goal": 3000
    })

    if resp.status_code == 200:
        data = resp.json()
        test_data["project_id"] = data.get("id")
        print(f"[OK] 创建项目成功, project_id: {test_data['project_id']}")
        return True
    else:
        print(f"[FAIL] 创建项目失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_7_bind_playbook():
    """测试7: 绑定技巧卡到项目 (POST /api/projects/{id}/playbook)"""
    print("\n" + "="*50)
    print("测试7: 绑定技巧卡到项目 (POST /api/projects/{id}/playbook)")
    print("="*50)

    project_id = test_data.get("project_id")
    if not project_id:
        print("[SKIP] 没有 project_id")
        return False

    # 获取技巧卡列表
    resp = requests.get(f"{BASE_URL}/techniques/?limit=10")
    if resp.status_code != 200:
        print(f"[FAIL] 获取技巧卡失败: {resp.status_code}")
        return False

    techniques = resp.json()
    technique_ids = [t.get("id") for t in techniques[:5] if t.get("id")]

    if len(technique_ids) < 3:
        print(f"[FAIL] 技巧卡数量不足: {len(technique_ids)} < 3")
        return False

    # 绑定到项目
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/playbook", json={
        "source_techniques": technique_ids,
        "rules": [
            "使用悬念钩子吸引读者",
            "控制情绪节奏避免突兀",
            "人物对话要符合性格设定"
        ],
        "style_boundaries": "保持玄幻风格，避免现代用语",
        "tone_guidelines": "紧张刺激，有爽点"
    })

    if resp.status_code == 200:
        print(f"[OK] Playbook 绑定成功")
        print(f"  - 绑定了 {len(technique_ids)} 张技巧卡")
        return True
    else:
        print(f"[FAIL] Playbook 绑定失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_8_create_bible():
    """测试8: 生成 Bible"""
    print("\n" + "="*50)
    print("测试8: 生成 Bible")
    print("="*50)

    project_id = test_data.get("project_id")
    if not project_id:
        print("[SKIP] 没有 project_id")
        return False

    resp = requests.post(f"{BASE_URL}/projects/{project_id}/bible", json={
        "world_setting": "这是一个修仙世界，强者为尊",
        "world_rules": ["灵根决定修炼上限", "丹药可辅助突破"],
        "characters": [
            {"name": "李青云", "description": "天赋异禀的少年，性格坚毅"}
        ],
        "main_plot": "主角从废材到巅峰的成长之路",
        "style_boundaries": ["避免现代用语", "保持古风"],
        "forbidden_items": ["现代科技", "西方魔法"]
    })

    if resp.status_code == 200:
        print("[OK] Bible 创建成功")
        return True
    else:
        print(f"[FAIL] Bible 创建失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_9_create_chapter_task():
    """测试9: 创建章节任务"""
    print("\n" + "="*50)
    print("测试9: 创建章节任务")
    print("="*50)

    project_id = test_data.get("project_id")
    if not project_id:
        print("[SKIP] 没有 project_id")
        return False

    # 创建章节
    resp = requests.post(f"{BASE_URL}/chapters/", json={
        "project_id": project_id,
        "chapter_index": 1,
        "title": "第一章 初入江湖",
        "target_word_count": 3000
    })

    if resp.status_code != 200:
        print(f"[FAIL] 创建章节失败: {resp.status_code} - {resp.text[:200]}")
        return False

    test_data["chapter_id"] = resp.json().get("id")
    print(f"[OK] 创建章节成功, chapter_id: {test_data['chapter_id']}")

    # 创建生成任务
    resp = requests.post(f"{BASE_URL}/tasks/", json={
        "project_id": project_id,
        "chapter_id": test_data["chapter_id"],
        "task_type": "draft",
        "priority": 3
    })

    if resp.status_code == 200:
        test_data["task_id"] = resp.json().get("id")
        print(f"[OK] 创建任务成功, task_id: {test_data['task_id']}")
        return True
    else:
        print(f"[FAIL] 创建任务失败: {resp.status_code} - {resp.text[:200]}")
        return False


def test_10_run_worker():
    """测试10: 启动 Worker 执行完整流水线"""
    print("\n" + "="*50)
    print("测试10: Worker 执行完整流水线")
    print("="*50)

    task_id = test_data.get("task_id")
    if not task_id:
        print("[SKIP] 没有 task_id")
        return False

    print("  启动 Worker (单次执行模式)...")

    # 启动 Worker 执行一次
    try:
        import asyncio
        from app.database import SessionLocal
        from app.services.worker_service import WritingWorker
        from app.models.task import GenerationTask, TaskStatus

        async def run_worker_once():
            worker = WritingWorker()
            db = SessionLocal()
            try:
                # 查找任务
                gen_task = db.query(GenerationTask).filter(
                    GenerationTask.id == task_id
                ).first()

                if not gen_task:
                    print("  [FAIL] 任务不存在")
                    return False

                chapter = gen_task.chapter
                project = gen_task.project

                print(f"  执行任务: {gen_task.id}, 章节: {chapter.title}")

                # 执行任务
                result = await worker._execute_task(db, gen_task, chapter, project)

                if result.get("success"):
                    print(f"  [OK] Worker 执行完成")
                    print(f"    - 最终评分: {result.get('final_score')}")
                    print(f"    - 版本号: {result.get('version_number')}")
                    print(f"    - 字数: {result.get('word_count')}")
                    return True
                else:
                    print(f"  [FAIL] Worker 执行失败: {result.get('error')}")
                    return False
            finally:
                db.close()

        # 运行
        result = asyncio.run(run_worker_once())
        return result

    except Exception as e:
        print(f"  [FAIL] Worker 执行异常: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_11_verify_results():
    """测试11: 验证 ChapterVersion / final_content / Darwin记录"""
    print("\n" + "="*50)
    print("测试11: 验证执行结果")
    print("="*50)

    chapter_id = test_data.get("chapter_id")
    project_id = test_data.get("project_id")

    if not chapter_id or not project_id:
        print("[SKIP] 缺少 chapter_id 或 project_id")
        return False

    all_pass = True

    # 1. 验证 ChapterVersion
    print("  检查 ChapterVersion...")
    resp = requests.get(f"{BASE_URL}/chapters/{chapter_id}/versions")
    if resp.status_code == 200:
        versions = resp.json()
        if versions:
            print(f"    [OK] 有 {len(versions)} 个版本")
            latest = versions[0]
            has_draft = latest.get("draft_content") and len(latest.get("draft_content")) > 100
            has_final = latest.get("final_content") and len(latest.get("final_content")) > 100
            print(f"    - draft_content: {'有(' + str(len(latest.get('draft_content', ''))) + '字)' if has_draft else '无'}")
            print(f"    - final_content: {'有(' + str(len(latest.get('final_content', ''))) + '字)' if has_final else '无'}")
            print(f"    - total_score: {latest.get('total_score')}")
            if not has_draft or not has_final:
                all_pass = False
        else:
            print("    [FAIL] 没有版本记录")
            all_pass = False
    else:
        print(f"    [FAIL] 查询版本失败: {resp.status_code}")
        all_pass = False

    # 2. 验证 Chapter.final_content
    print("  检查 Chapter.final_content...")
    resp = requests.get(f"{BASE_URL}/chapters/{chapter_id}")
    if resp.status_code == 200:
        chapter = resp.json()
        final_content = chapter.get("final_content", "")
        total_score = chapter.get("total_score", 0)
        print(f"    - final_content: {len(final_content)} 字")
        print(f"    - total_score: {total_score}")
        if len(final_content) < 100:
            print("    [FAIL] final_content 内容不足")
            all_pass = False
        if total_score <= 0:
            print("    [FAIL] total_score 无效")
            all_pass = False
    else:
        print(f"    [FAIL] 查询章节失败: {resp.status_code}")
        all_pass = False

    # 3. 验证 FailurePattern
    print("  检查 FailurePattern...")
    resp = requests.get(f"{BASE_URL}/projects/{project_id}/failures")
    if resp.status_code == 200:
        failures = resp.json()
        print(f"    [OK] 有 {len(failures)} 条失败记录")
        for f in failures[:3]:
            print(f"      - {f.get('category')}: {f.get('occurrence_count')}次")
    else:
        print(f"    [INFO] 无失败记录或接口不存在")

    # 4. 验证 Playbook 更新
    print("  检查 Playbook...")
    resp = requests.get(f"{BASE_URL}/projects/{project_id}/playbook")
    if resp.status_code == 200:
        playbook = resp.json()
        rules = playbook.get("rules", [])
        print(f"    [OK] Playbook 有 {len(rules)} 条规则")
        for r in rules[:3]:
            print(f"      - {r}")
    else:
        print(f"    [INFO] Playbook 查询失败或接口不存在")

    return all_pass


def main():
    """主测试流程"""
    print("="*60)
    print("P3 端到端验收测试 - 修复版")
    print("="*60)
    print("\n注意: 请确保后端服务已启动")
    print("命令: python -m uvicorn app.main:app --reload --port 8000")
    print("\n按 Enter 开始测试...")
    input()

    results = []

    # P0-P1 测试
    results.append(("1. 配置模型", test_1_model_config()))
    results.append(("2. 上传 TXT", test_2_upload_book()))
    results.append(("3. 真实分章", test_3_split_book()))
    results.append(("4. 拆书分析", test_4_analyze_book()))
    results.append(("5. 提取技巧卡", test_5_extract_techniques()))
    results.append(("6. 创建项目", test_6_create_project()))
    results.append(("7. 绑定Playbook", test_7_bind_playbook()))
    results.append(("8. 生成Bible", test_8_create_bible()))
    results.append(("9. 创建章节任务", test_9_create_chapter_task()))
    results.append(("10. Worker执行", test_10_run_worker()))
    results.append(("11. 验证结果", test_11_verify_results()))

    # 总结
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n" + "="*60)
        print("[OK] 所有测试通过! P3 验收成功!")
        print("="*60)
        return 0
    else:
        print(f"\n[FAIL] 有 {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
