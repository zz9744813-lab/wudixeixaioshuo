"""
Test Configuration
测试配置
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "app"))

# 测试数据库路径
TEST_DB_PATH = PROJECT_ROOT / "data" / "test_novel_agent.db"
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

# 测试环境变量
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["APP_API_KEY"] = "test-api-key-for-ci"
os.environ["APP_SECRET_KEY"] = "test-secret-key"
os.environ["APP_ENV"] = "test"
