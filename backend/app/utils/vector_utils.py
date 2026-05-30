"""
向量工具 (P4)
"""

import math
from typing import List


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """计算两个向量的余弦相似度，无效输入返回 0.0。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))
