"""NovelForge AI - Custom errors"""
from typing import Any


class NovelForgeError(Exception):
    def __init__(self, code: str, message: str, status: int = 400, details: dict[str, Any] | None = None):
        self.code = code
        self.message = message
        self.status = status
        self.details = details or {}


class NotFoundError(NovelForgeError):
    def __init__(self, resource: str, id: int | str):
        super().__init__(
            code="not_found",
            message=f"{resource} not found",
            status=404,
            details={"resource": resource, "id": str(id)},
        )


class ExternalServiceError(NovelForgeError):
    def __init__(self, service: str, reason: str):
        super().__init__(
            code="external_service_error",
            message=f"{service} error: {reason}",
            status=502,
            details={"service": service, "reason": reason},
        )


class QueueError(NovelForgeError):
    def __init__(self, message: str):
        super().__init__(code="queue_error", message=message, status=500)


class AuthError(NovelForgeError):
    def __init__(self):
        super().__init__(code="unauthorized", message="Unauthorized", status=401)


class ValidationError(NovelForgeError):
    def __init__(self, field: str, reason: str):
        super().__init__(
            code="validation_error",
            message=f"{field}: {reason}",
            status=422,
            details={"field": field},
        )
