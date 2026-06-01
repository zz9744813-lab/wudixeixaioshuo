"""NovelForge AI - Setup schemas"""
from pydantic import BaseModel


class SetupCheckOut(BaseModel):
    key: str
    label: str
    status: str
    message: str


class SetupStatusOut(BaseModel):
    ok: bool
    checks: list[SetupCheckOut]
    next_action: dict | None = None
