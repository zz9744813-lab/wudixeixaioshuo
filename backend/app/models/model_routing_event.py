"""
Model Routing Event Models - 调度决策事件记录
Phase 1 模型配置优化: 记录每次 resolve 的决策细节
"""

import json
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.utils.time_utils import utc_now


class ModelRoutingEvent(Base):
    """模型路由决策事件表 - 记录每次 Agent 调度的选择和理由"""
    __tablename__ = "model_routing_events"

    id = Column(Integer, primary_key=True, index=True)

    # 调用上下文
    role = Column(String(64), nullable=False, index=True)
    task_id = Column(String(64), nullable=True, index=True)
    project_id = Column(Integer, nullable=True, index=True)

    # 决策模式
    assignment_mode = Column(String(20), nullable=False, default="auto")

    # 实际选择
    selected_provider_id = Column(Integer, nullable=True)
    selected_provider_name = Column(String(128), nullable=True)
    selected_route_id = Column(Integer, nullable=True)  # provider_route_configs.id
    selected_model_name = Column(String(200), nullable=True)

    # 候选快照（JSON 字符串）
    candidates_json = Column(Text, nullable=True)
    score_breakdown_json = Column(Text, nullable=True)

    # 决策理由（人类可读）
    decision_reason = Column(String(500), nullable=True)

    # 回退情况
    fallback_used = Column(Boolean, default=False)
    fallback_chain_json = Column(Text, nullable=True)

    # 时间戳
    created_at = Column(DateTime, default=utc_now, index=True)

    # ---- 辅助方法 ----

    def set_candidates(self, items: List[Dict[str, Any]]) -> None:
        """写入候选列表"""
        self.candidates_json = json.dumps(items, ensure_ascii=False, default=str)

    def get_candidates(self) -> List[Dict[str, Any]]:
        """读取候选列表"""
        if not self.candidates_json:
            return []
        try:
            return json.loads(self.candidates_json)
        except (json.JSONDecodeError, TypeError):
            return []

    def set_score_breakdown(self, breakdown: Dict[str, Any]) -> None:
        """写入评分明细"""
        self.score_breakdown_json = json.dumps(breakdown, ensure_ascii=False, default=str)

    def get_score_breakdown(self) -> Dict[str, Any]:
        """读取评分明细"""
        if not self.score_breakdown_json:
            return {}
        try:
            return json.loads(self.score_breakdown_json)
        except (json.JSONDecodeError, TypeError):
            return {}

    def set_fallback_chain(self, chain: List[Dict[str, Any]]) -> None:
        self.fallback_chain_json = json.dumps(chain, ensure_ascii=False, default=str)

    def get_fallback_chain(self) -> List[Dict[str, Any]]:
        if not self.fallback_chain_json:
            return []
        try:
            return json.loads(self.fallback_chain_json)
        except (json.JSONDecodeError, TypeError):
            return []
