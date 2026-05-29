"""
Time utilities - 时间工具函数
统一处理 UTC 时间，兼容 Python 3.12+
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """获取当前 UTC 时间（兼容 Python 3.12+，替代已弃用的 datetime.utcnow）"""
    return datetime.now(timezone.utc)
