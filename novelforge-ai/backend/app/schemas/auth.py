"""NovelForge AI - Auth schemas"""
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserSelfResponse(BaseModel):
    id: str
    username: str
