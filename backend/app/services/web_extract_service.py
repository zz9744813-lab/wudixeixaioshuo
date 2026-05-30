"""Web Extract Service - 网页正文提取服务。

抓取网页标题、正文摘要、发布时间。
限制最大字符数，不保存全文，只把临时文本交给 LLM 抽取。
"""

import hashlib
from dataclasses import dataclass
from typing import Optional

MAX_PAGE_CHARS = 20000
MAX_EXCERPT_CHARS = 500


@dataclass
class ExtractedPage:
    """提取后的网页内容"""
    url: str
    title: str
    excerpt: str
    text_hash: str
    published_at: Optional[str] = None
    error: Optional[str] = None


class WebExtractService:
    """网页正文提取服务。"""

    async def extract(self, url: str) -> ExtractedPage:
        """抓取网页标题、正文摘要。

        Returns:
            ExtractedPage: 提取结果，包含标题、短摘录和文本哈希。
        """
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "NovelAgentBot/1.0"})
                resp.raise_for_status()
                html = resp.text[:MAX_PAGE_CHARS]

            title = self._extract_title(html)
            text = self._extract_text(html)
            excerpt = text[:MAX_EXCERPT_CHARS]
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

            return ExtractedPage(
                url=url,
                title=title,
                excerpt=excerpt,
                text_hash=text_hash,
            )
        except Exception as exc:
            return ExtractedPage(
                url=url,
                title="",
                excerpt="",
                text_hash="",
                error=str(exc),
            )

    def _extract_title(self, html: str) -> str:
        """从 HTML 中提取标题。"""
        import re

        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:200]
        match = re.search(r'<h1[^>]*>(.*?)</h1>', html, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()[:200]
        return ""

    def _extract_text(self, html: str) -> str:
        """从 HTML 中提取纯文本摘要。"""
        import re

        # 简单 HTML 标签移除
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:MAX_PAGE_CHARS]
