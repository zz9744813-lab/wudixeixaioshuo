"""
OpenAI-compatible LLM Service - OpenAI 兼容的 LLM 服务
支持任何兼容 OpenAI API 格式的服务（OpenAI, Azure, DeepSeek, 本地模型等）
"""

import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.services.llm_service import BaseLLMService


class OpenAILLMService(BaseLLMService):
    """
    OpenAI 兼容的 LLM 服务
    支持标准 OpenAI API 格式，可用于多种提供商
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model_name: str,
        timeout: int = 120,
        retry_times: int = 3,
        provider_id: int = None,
        provider_name: str = None,
    ):
        """
        初始化 OpenAI LLM 服务

        Args:
            base_url: API 基础 URL，如 https://api.openai.com/v1
            api_key: API Key
            model_name: 默认模型名称，如 gpt-3.5-turbo
            timeout: 请求超时时间（秒）
            retry_times: 重试次数
            provider_id: 提供商ID（用于日志记录）
            provider_name: 提供商名称（用于日志记录）
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model_name = model_name
        self.timeout = timeout
        self.retry_times = retry_times
        self.provider_id = provider_id
        self.provider_name = provider_name

        # 初始化 HTTP 客户端
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )

        # 模型价格表（每 1K tokens，单位：美元）
        self.pricing = {
            # OpenAI 模型
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.0005, "output": 0.0015},
            "gpt-3.5-turbo-0125": {"input": 0.0005, "output": 0.0015},
            # DeepSeek 模型
            "deepseek-chat": {"input": 0.00014, "output": 0.00028},
            "deepseek-coder": {"input": 0.00014, "output": 0.00028},
            # 默认价格
            "default": {"input": 0.001, "output": 0.002},
        }

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        生成响应

        Args:
            prompt: 用户提示词
            model: 模型名称，默认使用初始化时的 model_name
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Returns:
            包含响应内容的字典
        """
        model = model or self.model_name
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # 添加其他可选参数
        if "top_p" in kwargs:
            payload["top_p"] = kwargs["top_p"]
        if "stop" in kwargs:
            payload["stop"] = kwargs["stop"]

        start_time = time.time()
        last_error = None

        # 重试机制
        for attempt in range(self.retry_times):
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()

                duration = time.time() - start_time

                # 提取响应内容
                choice = data["choices"][0]
                content = choice["message"]["content"]

                # 获取 token 统计
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", 0)
                output_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)

                # 计算成本
                cost = self._calculate_cost(model, input_tokens, output_tokens)

                return {
                    "content": content,
                    "model": model,
                    "provider": self.provider_name or "openai-compatible",
                    "provider_id": self.provider_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": total_tokens,
                    "cost": cost,
                    "duration_seconds": duration,
                    "finish_reason": choice.get("finish_reason"),
                }

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text}"
                if e.response.status_code == 429:  # Rate limit
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue
                elif e.response.status_code >= 500:  # Server error, retry
                    if attempt < self.retry_times - 1:
                        await asyncio.sleep(1)
                        continue
                raise Exception(f"API 请求失败: {last_error}")

            except httpx.TimeoutException:
                last_error = "请求超时"
                if attempt < self.retry_times - 1:
                    await asyncio.sleep(1)
                    continue
                raise Exception(f"API 请求超时，已重试 {self.retry_times} 次")

            except Exception as e:
                raise Exception(f"API 请求异常: {str(e)}")

        raise Exception(f"API 请求失败: {last_error}")

    async def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        流式生成响应

        Args:
            prompt: 用户提示词
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大生成 token 数
            system_prompt: 系统提示词
            **kwargs: 其他参数

        Yields:
            生成的文本片段
        """
        model = model or self.model_name
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }

        try:
            async with self.client.stream(
                "POST",
                "/chat/completions",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 移除 "data: " 前缀

                        if data == "[DONE]":
                            break

                        try:
                            import json
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"]
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue

        except httpx.HTTPStatusError as e:
            raise Exception(f"流式 API 请求失败: HTTP {e.response.status_code}")
        except Exception as e:
            raise Exception(f"流式 API 请求异常: {str(e)}")

    async def health_check(self) -> Dict[str, Any]:
        """
        健康检查

        Returns:
            健康状态字典
        """
        try:
            # 尝试调用 models 端点或发送一个简单的请求
            response = await self.client.get("/models", timeout=10)

            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "provider": "openai-compatible",
                    "base_url": self.base_url,
                    "model": self.model_name,
                    "message": "连接正常",
                }
            else:
                return {
                    "status": "unhealthy",
                    "provider": "openai-compatible",
                    "base_url": self.base_url,
                    "model": self.model_name,
                    "message": f"API 返回状态码 {response.status_code}",
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": "openai-compatible",
                "base_url": self.base_url,
                "model": self.model_name,
                "message": f"连接失败: {str(e)}",
            }

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """
        计算调用成本

        Args:
            model: 模型名称
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数

        Returns:
            预估成本（美元）
        """
        # 获取模型价格，如果没有则使用默认价格
        price = self.pricing.get(model, self.pricing["default"])

        input_cost = (input_tokens / 1000) * price["input"]
        output_cost = (output_tokens / 1000) * price["output"]

        return round(input_cost + output_cost, 6)

    async def close(self):
        """关闭 HTTP 客户端"""
        await self.client.aclose()


class LLMServiceManager:
    """
    LLM 服务管理器
    管理不同角色的 LLM 服务实例，支持动态切换
    """

    # 支持的角色列表
    SUPPORTED_ROLES = [
        "planner",      # 规划 Agent
        "draft",        # 起草 Agent
        "critic",       # 审稿 Agent
        "rewrite",      # 改写 Agent
        "continuity",   # 连续性检查 Agent
        "learning",     # 学习 Agent
        "study",        # 学习/分析 Agent
        "split",        # 分章 Agent
        "analyze",      # 分析 Agent
        # P4新增角色
        "memory_update",    # 记忆更新 Agent
        "memory_retrieval", # 记忆检索 Agent
        "foreshadow",       # 伏笔管理 Agent
        "logic_critic",     # 逻辑评审 Agent
        "style_critic",     # 文风评审 Agent
        "commercial_critic", # 商业性评审 Agent
        "default",      # 默认角色
    ]

    def __init__(self):
        self._services: Dict[str, OpenAILLMService] = {}
        self._mock_service = None
        self._db = None
        self._initialized = False
        self._config_signature = None

    def _build_config_signature(self, providers, roles) -> str:
        """构建配置签名，用于检测配置是否变化"""
        import hashlib
        import json

        config = {
            "providers": [
                {
                    "id": p.id,
                    "base_url": p.base_url,
                    "api_key_encrypted": p.api_key_encrypted,
                    "default_model": p.default_model,
                    "timeout_seconds": p.timeout_seconds,
                    "retry_times": p.retry_times,
                }
                for p in providers
            ],
            "roles": [
                {
                    "role": r.role,
                    "provider_id": r.provider_id,
                    "model_name": r.model_name,
                }
                for r in roles
            ]
        }
        return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:32]

    async def init_from_db(self, db_session, force: bool = False):
        """
        从数据库初始化服务配置

        Args:
            db_session: 数据库会话
            force: 是否强制重新初始化
        """
        from app.models.model_config import ModelProvider, ModelRole
        from app.services.secret_service import decrypt_api_key

        self._db = db_session

        # 获取启用的提供商
        providers = db_session.query(ModelProvider).filter(
            ModelProvider.is_enabled == 1
        ).all()

        # 获取角色映射 - 避免空列表传入filter
        if providers:
            roles = db_session.query(ModelRole).filter(
                ModelRole.provider_id.in_([p.id for p in providers])
            ).all()
        else:
            roles = []

        # 构建配置签名
        signature = self._build_config_signature(providers, roles)

        # 检查是否需要重新初始化
        if self._initialized and not force and signature == self._config_signature:
            return

        # 关闭现有连接
        await self.close_all()

        if not providers:
            # 没有配置，使用 Mock 服务
            self._initialized = True
            self._config_signature = signature
            return

        # 获取默认提供商
        default_provider = next(
            (p for p in providers if p.is_default == 1),
            providers[0]  # 如果没有默认，使用第一个
        )

        # 创建服务实例
        for role in self.SUPPORTED_ROLES:
            # 查找角色的特定配置
            role_config = next(
                (r for r in roles if r.role == role),
                None
            )

            if role_config:
                provider = role_config.provider
                self._services[role] = OpenAILLMService(
                    base_url=provider.base_url,
                    api_key=decrypt_api_key(provider.api_key_encrypted),
                    model_name=role_config.model_name,
                    timeout=provider.timeout_seconds or 120,
                    retry_times=provider.retry_times or 3,
                    provider_id=provider.id,
                    provider_name=provider.name,
                )
            elif default_provider:
                # 使用默认提供商
                self._services[role] = OpenAILLMService(
                    base_url=default_provider.base_url,
                    api_key=decrypt_api_key(default_provider.api_key_encrypted),
                    model_name=default_provider.default_model,
                    timeout=default_provider.timeout_seconds or 120,
                    retry_times=default_provider.retry_times or 3,
                    provider_id=default_provider.id,
                    provider_name=default_provider.name,
                )

        self._initialized = True
        self._config_signature = signature

    def get_service(self, role: str = "default") -> BaseLLMService:
        """
        获取指定角色的 LLM 服务

        Args:
            role: 角色名称

        Returns:
            LLM 服务实例（真实服务或 Mock 服务）
        """
        # 检查是否有真实服务配置
        if role in self._services:
            return self._services[role]

        # 使用默认服务
        if "default" in self._services:
            return self._services["default"]

        # 回退到 Mock 服务
        if self._mock_service is None:
            from app.services.mock_llm_service import MockLLMService
            self._mock_service = MockLLMService()

        return self._mock_service

    async def generate(
        self,
        prompt: str,
        role: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 4000,
        db=None,
        request_type: str = "chat_completion",
        project_id: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        使用指定角色生成响应 (P2-4: 日志独立提交版)

        P2-4 关键改进：
        - LLM 调用日志使用独立 session 提交
        - 不跟随业务事务 rollback
        - 成功和失败都记录
        - 即使章节生成失败并回滚，调用日志仍然存在

        Args:
            prompt: 提示词
            role: 角色名称
            temperature: 温度参数
            max_tokens: 最大 token 数
            db: 数据库会话（仅用于读取，日志独立提交）
            request_type: 请求类型
            project_id: 项目ID
            **kwargs: 其他参数

        Returns:
            生成结果
        """
        from app.utils.time_utils import utc_now
        from app.services.model_call_log_service import ModelCallLogService

        started_at = utc_now()
        service = self.get_service(role)

        # P2-4: 创建独立的日志服务（不依赖业务 db session）
        log_service = ModelCallLogService()

        try:
            response = await service.generate(
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            finished_at = utc_now()

            # P2-4: 独立提交日志（不跟随业务事务）
            log_service.create_log(
                provider_id=response.get("provider_id"),
                project_id=project_id,
                role=role,
                model_name=response.get("model", ""),
                request_type=request_type,
                input_tokens=response.get("input_tokens", 0),
                output_tokens=response.get("output_tokens", 0),
                total_tokens=response.get("total_tokens", 0),
                estimated_cost=response.get("cost", 0.0),
                started_at=started_at,
                finished_at=finished_at,
                status="success",
                prompt=prompt,
                response=response.get("content", ""),
            )

            return response

        except Exception as e:
            finished_at = utc_now()

            # P2-4: 失败也独立记录日志
            log_service.create_log(
                provider_id=getattr(service, "provider_id", None),
                project_id=project_id,
                role=role,
                model_name=getattr(service, "model_name", "unknown"),
                request_type=request_type,
                started_at=started_at,
                finished_at=finished_at,
                status="failed",
                error_message=str(e)[:1000],
                prompt=prompt,
            )

            raise

    async def health_check(self, role: str = "default") -> Dict[str, Any]:
        """
        健康检查

        Args:
            role: 角色名称

        Returns:
            健康状态
        """
        service = self.get_service(role)
        return await service.health_check()

    async def close_all(self):
        """关闭所有服务连接"""
        for service in self._services.values():
            await service.close()
        self._services.clear()


# 全局服务管理器实例
llm_manager = LLMServiceManager()
