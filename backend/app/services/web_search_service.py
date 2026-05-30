"""Web Search Service - 联网搜索适配层。

支持多种搜索后端（Tavily / Bing / SerpAPI），无配置时返回明确错误。
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class SearchResult:
    """单条搜索结果"""
    title: str
    url: str
    snippet: str
    source_type: str = "search_result"
    trust_score: float = 0.5


class WebSearchService:
    """联网搜索服务，根据环境变量选择搜索后端。"""

    def __init__(self):
        self.provider = os.getenv("SEARCH_PROVIDER", "").lower()
        self.api_key = os.getenv("SEARCH_API_KEY", "")
        self.max_results = int(os.getenv("SEARCH_MAX_RESULTS", "10"))

    @property
    def is_configured(self) -> bool:
        return bool(self.provider and self.api_key)

    async def search(self, query: str, limit: Optional[int] = None) -> List[SearchResult]:
        """执行搜索，返回结果列表。

        Raises:
            RuntimeError: 未配置搜索 API 时抛出明确错误。
        """
        if not self.is_configured:
            raise RuntimeError(
                "未配置联网搜索 API。请在 .env 中设置 SEARCH_PROVIDER 和 SEARCH_API_KEY。"
                "支持的 provider: tavily, bing, serpapi。"
            )

        limit = limit or self.max_results

        if self.provider == "tavily":
            return await self._search_tavily(query, limit)
        elif self.provider == "bing":
            return await self._search_bing(query, limit)
        elif self.provider == "serpapi":
            return await self._search_serpapi(query, limit)
        else:
            raise RuntimeError(f"不支持的搜索 provider: {self.provider}")

    async def _search_tavily(self, query: str, limit: int) -> List[SearchResult]:
        """通过 Tavily API 搜索。"""
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": limit,
                    "include_answer": False,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("results", []):
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", "")[:500],
                source_type="search_result",
                trust_score=min(1.0, max(0.0, item.get("score", 0.5))),
            ))
        return results

    async def _search_bing(self, query: str, limit: int) -> List[SearchResult]:
        """通过 Bing Web Search API 搜索。"""
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.bing.microsoft.com/v7.0/search",
                headers={"Ocp-Apim-Subscription-Key": self.api_key},
                params={"q": query, "count": limit, "mkt": "zh-CN"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("webPages", {}).get("value", []):
            results.append(SearchResult(
                title=item.get("name", ""),
                url=item.get("url", ""),
                snippet=item.get("snippet", "")[:500],
                source_type="search_result",
                trust_score=0.6,
            ))
        return results

    async def _search_serpapi(self, query: str, limit: int) -> List[SearchResult]:
        """通过 SerpAPI 搜索。"""
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={"q": query, "api_key": self.api_key, "engine": "google", "num": limit},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic_results", [])[:limit]:
            results.append(SearchResult(
                title=item.get("title", ""),
                url=item.get("link", ""),
                snippet=item.get("snippet", "")[:500],
                source_type="search_result",
                trust_score=0.6,
            ))
        return results
