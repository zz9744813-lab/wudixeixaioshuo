"""
LLM Service - LLM 服务基类
"""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, Optional


class BaseLLMService(ABC):
    """LLM 服务基类"""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> Dict[str, Any]:
        """生成响应"""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式生成响应"""
        pass

    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        pass
