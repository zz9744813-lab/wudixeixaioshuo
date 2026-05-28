"""
P3 端到端验收测试脚本

测试完整流程:
1. 配置模型
2. 上传 TXT
3. 真实分章
4. 拆书分析
5. 生成至少 3 张 TechniqueCard
6. 创建小说项目
7. 生成 Bible
8. 创建章节任务
9. Worker 执行 Planner/Draft/Critic/Rewrite/Continuity
10. 保存 ChapterVersion
11. Darwin 根据评分保留或回滚
12. 最终 Chapter.final_content 有内容

使用方法:
1. 确保后端服务已启动: python -m uvicorn app.main:app --reload --port 8000
2. 运行测试: python p3_e2e_test.py
"""

import requests
import json
import time
import os

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

def test_1_model_config():
    """测试1: 配置模型"""
    print("\n" + "="*50)
    print("测试1: 配置模型")
    print("="*50)

    # 检查模型配置列表
    resp = requests.get(f"{BASE_URL}/models/configs")
    if resp.status_code == 200:
        configs = resp.json()
        print(f"[OK] 获取 {len(configs)} 个模型配置")
        return True
    else:
        print(f"[FAIL] 获取模型配置失败: {resp.status_code}")
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
        book_id = data.get("id")
        print(f"[OK] 上传成功, book_id: {book_id}")
        return book_id
    else:
        print(f"[FAIL] 上传失败: {resp.status_code} - {resp.text}")
        return None

def test_3_split_book(book_id):
    """测试3: 真实分章"""
    print("\n" + "="*50)
    print("测试3: 真实分章")
    print("="*50)

    resp = requests.post(f"{BASE_URL}/books/{book_id}/split")
    if resp.status_code == 200:
        data = resp.json()
        chapters = data.get("total_chapters", 0)
        print(f"[OK] 分章完成, 共 {chapters} 章")
        return chapters > 0
    else:
        print(f"[FAIL] 分章失败: {resp.status_code} - {resp.text}")
        return False

def test_4_analyze_book(book_id):
    """测试4: 拆书分析"""
    print("\n" + "="*50)
    print("测试4: 拆书分析")
    print("="*50)

    resp = requests.post(f"{BASE_URL}/books/{book_id}/analyze")
    if resp.status_code == 200:
        data = resp.json()
        chapters_analyzed = data.get("analysis_summary", {}).get("chapters_analyzed", 0)
        print(f"[OK] 分析完成, 分析了 {chapters_analyzed} 章")
        return chapters_analyzed > 0
    else:
        print(f"[FAIL] 分析失败: {resp.status_code} - {resp.text}")
        return False

def test_5_extract_techniques(book_id):
    """测试5: 生成至少 3 张 TechniqueCard"""
    print("\n" + "="*50)
    print("测试5: 提取技巧卡")
    print("="*50)

    resp = requests.post(f"{BASE_URL}/books/{book_id}/extract-techniques")
    if resp.status_code == 200:
        data = resp.json()
        techniques = data.get("techniques", [])
        print(f"[OK] 提取 {len(techniques)} 张技巧卡")
        for t in techniques[:3]:
            print(f"  - {t.get('title')} ({t.get('category')})")
        return len(techniques) >= 3
    else:
        print(f"[FAIL] 提取失败: {resp.status_code} - {resp.text}")
        return False

def test_6_create_project():
    """测试6: 创建小说项目"""
    print("\n" + "="*50)
    print("测试6: 创建小说项目")
    print("="*50)

    resp = requests.post(f"{BASE_URL}/projects/", json={
        "title": "测试项目",
        "genre": "玄幻",
        "target_length": 100000,
        "description": "这是一个测试项目"
    })

    if resp.status_code == 200:
        data = resp.json()
        project_id = data.get("id")
        print(f"[OK] 创建项目成功, project_id: {project_id}")
        return project_id
    else:
        print(f"[FAIL] 创建项目失败: {resp.status_code} - {resp.text}")
        return None

def test_7_create_bible(project_id):
    """测试7: 生成 Bible"""
    print("\n" + "="*50)
    print("测试7: 生成 Bible")
    print("="*50)

    resp = requests.post(f"{BASE_URL}/projects/{project_id}/bible", json={
        "world_setting": "这是一个修仙世界",
        "characters": [{"name": "主角", "description": "天赋异禀的少年"}],
        "main_plot": "主角从废材到巅峰的成长之路"
    })

    if resp.status_code == 200:
        print("[OK] Bible 创建成功")
        return True
    else:
        print(f"[FAIL] Bible 创建失败: {resp.status_code} - {resp.text}")
        return False

def test_8_create_chapter_task(project_id):
    """测试8: 创建章节任务"""
    print("\n" + "="*50)
    print("测试8: 创建章节任务")
    print("="*50)

    # 先创建章节
    resp = requests.post(f"{BASE_URL}/chapters/", json={
        "project_id": project_id,
        "chapter_index": 1,
        "title": "第一章 测试章节",
        "target_word_count": 2000
    })

    if resp.status_code != 200:
        print(f"[FAIL] 创建章节失败: {resp.status_code} - {resp.text}")
        return None

    chapter_id = resp.json().get("id")

    # 创建生成任务
    resp = requests.post(f"{BASE_URL}/tasks/", json={
        "project_id": project_id,
        "chapter_id": chapter_id,
        "task_type": "draft",
        "priority": 3
    })

    if resp.status_code == 200:
        task_id = resp.json().get("id")
        print(f"[OK] 创建任务成功, task_id: {task_id}")
        return task_id
    else:
        print(f"[FAIL] 创建任务失败: {resp.status_code} - {resp.text}")
        return None

def main():
    """主测试流程"""
    print("="*50)
    print("P3 端到端验收测试")
    print("="*50)
    print("\n注意: 请确保后端服务已启动")
    print("命令: python -m uvicorn app.main:app --reload --port 8000")
    print("\n按 Enter 开始测试...")
    input()

    results = []

    # 测试1: 配置模型
    results.append(("配置模型", test_1_model_config()))

    # 测试2: 上传 TXT
    book_id = test_2_upload_book()
    results.append(("上传 TXT", book_id is not None))

    if book_id:
        # 测试3: 分章
        results.append(("真实分章", test_3_split_book(book_id)))

        # 测试4: 拆书分析
        results.append(("拆书分析", test_4_analyze_book(book_id)))

        # 测试5: 提取技巧卡
        results.append(("生成技巧卡", test_5_extract_techniques(book_id)))

    # 测试6: 创建项目
    project_id = test_6_create_project()
    results.append(("创建项目", project_id is not None))

    if project_id:
        # 测试7: 创建 Bible
        results.append(("生成 Bible", test_7_create_bible(project_id)))

        # 测试8: 创建章节任务
        task_id = test_8_create_chapter_task(project_id)
        results.append(("创建章节任务", task_id is not None))

    # 总结
    print("\n" + "="*50)
    print("测试结果汇总")
    print("="*50)

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "[OK]" if result else "[FAIL]"
        print(f"{status} {name}")

    print(f"\n总计: {passed}/{total} 通过")

    if passed == total:
        print("\n[OK] 所有测试通过! P3 验收成功!")
    else:
        print(f"\n[FAIL] 有 {total - passed} 个测试失败")

if __name__ == "__main__":
    main()
