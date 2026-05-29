"""
Model Call Log Service - 记录 LLM 调用日志和成本统计 (P2-4: 独立提交版)

关键要求：
- LLM 调用日志使用独立短 session 提交
- 不跟随章节生成大事务 rollback
- 成功和失败都记录
- 即使业务事务失败，调用日志也不能丢
"""

from typing import Optional
from sqlalchemy.orm import Session, sessionmaker
from app.database import engine
from app.models.model_config import ModelCallLog
from app.utils.time_utils import utc_now


class ModelCallLogService:
    """LLM 调用日志服务 - 独立提交，不跟随业务事务"""

    def __init__(self, db: Optional[Session] = None):
        """
        初始化服务

        Args:
            db: 可选的业务数据库 session（仅用于读取，日志仍独立提交）
        """
        self.db = db
        # 创建独立的 session maker
        self._Session = sessionmaker(bind=engine)

    def create_log(
        self,
        *,
        provider_id: Optional[int] = None,
        project_id: Optional[int] = None,
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
    ) -> Optional[ModelCallLog]:
        """
        创建调用日志 - 使用独立 session 立即提交

        P2-4 关键行为：
        - 使用独立 session 立即 commit
        - 即使业务事务失败并 rollback，此日志也不会丢失
        - 成功和失败都会记录

        Returns:
            ModelCallLog 或 None（如果记录失败）
        """
        if total_tokens <= 0:
            total_tokens = (input_tokens or 0) + (output_tokens or 0)

        if started_at and finished_at and duration_ms is None:
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

        # 使用独立 session，不跟随业务事务
        db = self._Session()
        try:
            log = ModelCallLog(
                provider_id=provider_id,
                project_id=project_id,
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
            db.add(log)
            db.commit()
            db.refresh(log)

            # 关闭 session
            db.close()

            return log

        except Exception as e:
            # 记录失败不影响业务
            try:
                db.rollback()
                db.close()
            except:
                pass
            return None

    def create_log_sync(
        self,
        *,
        provider_id: Optional[int] = None,
        project_id: Optional[int] = None,
        role: str = "default",
        model_name: str = "",
        request_type: str = "chat_completion",
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost: float = 0.0,
        started_at=None,
        finished_at=None,
        status: str = "success",
        error_message: Optional[str] = None,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
    ) -> Optional[ModelCallLog]:
        """
        同步创建调用日志

        用于在 async 上下文中需要同步记录的场景
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在 event loop 中，直接调用
                return self.create_log(
                    provider_id=provider_id,
                    project_id=project_id,
                    role=role,
                    model_name=model_name,
                    request_type=request_type,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    estimated_cost=estimated_cost,
                    started_at=started_at,
                    finished_at=finished_at,
                    status=status,
                    error_message=error_message,
                    prompt=prompt,
                    response=response,
                )
        except RuntimeError:
            pass

        # 否则创建新 session
        return self.create_log(
            provider_id=provider_id,
            project_id=project_id,
            role=role,
            model_name=model_name,
            request_type=request_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost=estimated_cost,
            started_at=started_at,
            finished_at=finished_at,
            status=status,
            error_message=error_message,
            prompt=prompt,
            response=response,
        )
