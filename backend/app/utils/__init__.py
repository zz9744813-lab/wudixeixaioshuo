"""
Time utilities - 时间工具函数
统一处理 UTC 时间，兼容 Python 3.12+
"""
from datetime import datetime, timezone


def utc_now() -> datetime:
    """获取当前 UTC 时间（兼容 Python 3.12+）"""
    return datetime.now(timezone.utc)


def utc_now_str() -> str:
    """获取当前 UTC 时间的 ISO 格式字符串"""
    return utc_now().isoformat()
