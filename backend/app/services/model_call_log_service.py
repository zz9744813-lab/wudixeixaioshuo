"""
Model Call Log Service - 记录 LLM 调用日志和成本统计
"""

from typing import Optional
from sqlalchemy.orm import Session
from app.models.model_config import ModelCallLog
from app.utils.time_utils import utc_now


class ModelCallLogService:
    def __init__(self, db: Session):
        self.db = db

    def create_log(
        self,
        *,
        provider_id: Optional[int] = None,
        role: str = "default",
        model_name: str = "",
        request_type: str = "chat_completion",
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost: float = 0.0,
        started_at=None,
        finished_at=None,
        duration_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
    ) -> ModelCallLog:
        if total_tokens <= 0:
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        if started_at and finished_at and duration_ms is None:
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        log = ModelCallLog(
            provider_id=provider_id,
            role=role,
            model_name=model_name,
            request_type=request_type,
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
            total_tokens=total_tokens or 0,
            estimated_cost=estimated_cost or 0.0,
            started_at=started_at,
            finished_at=finished_at,
            duration_ms=duration_ms,
            status=status,
            error_message=error_message,
            prompt_summary=(prompt or "")[:500],
            response_summary=(response or "")[:500],
            created_at=utc_now(),
        )
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log
