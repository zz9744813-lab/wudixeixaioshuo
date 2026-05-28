"""
验收测试脚本 - P4 验收标准验证
"""

import sys
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_health():
    """测试健康检查"""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        print(f"✅ Health check: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_dashboard():
    """测试仪表盘"""
    try:
        r = requests.get(f"{BASE_URL}/dashboard", timeout=5)
        print(f"✅ Dashboard: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Dashboard failed: {e}")
        return False

def test_llm_providers():
    """测试 LLM 提供商接口"""
    try:
        r = requests.get(f"{BASE_URL}/models/providers", timeout=5)
        print(f"✅ LLM Providers: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ LLM Providers failed: {e}")
        return False

def test_worker_status():
    """测试 Worker 状态"""
    try:
        r = requests.get(f"{BASE_URL}/worker/status", timeout=5)
        print(f"✅ Worker Status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Worker Status failed: {e}")
        return False

def test_projects():
    """测试项目列表"""
    try:
        r = requests.get(f"{BASE_URL}/projects", timeout=5)
        print(f"✅ Projects: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Projects failed: {e}")
        return False

def test_books():
    """测试书籍列表"""
    try:
        r = requests.get(f"{BASE_URL}/books", timeout=5)
        print(f"✅ Books: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Books failed: {e}")
        return False

def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("P4 验收标准测试")
    print("=" * 50)

    tests = [
        ("Health Check", test_health),
        ("Dashboard", test_dashboard),
        ("LLM Providers", test_llm_providers),
        ("Worker Status", test_worker_status),
        ("Projects", test_projects),
        ("Books", test_books),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        print(f"\nTesting {name}...")
        if test_func():
            passed += 1
        else:
            failed += 1

    print("\n" + "=" * 50)
    print(f"结果: {passed} 通过, {failed} 失败")
    print("=" * 50)

    return failed == 0

if __name__ == "__main__":
    if run_all_tests():
        print("\n✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("\n❌ 部分测试失败")
        sys.exit(1)
