import asyncio
import html
import os
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .manager import MCPPlugin


class BingCnSearchPlugin(MCPPlugin):
    """Bing 中文联网搜索插件。"""

    name = "bing_cn_search"
    description = "使用必应中文搜索实时检索网页信息，并支持网页正文抓取。"
    auto_context = True

    _BLACKLIST_DOMAINS = {
        "zhihu.com",
        "xiaohongshu.com",
        "weibo.com",
        "weixin.qq.com",
        "douyin.com",
        "tiktok.com",
        "bilibili.com",
        "csdn.net",
    }

    def __init__(self) -> None:
        self.search_url = os.getenv("BING_MCP_SEARCH_URL", "https://cn.bing.com/search")
        self.timeout_seconds = float(os.getenv("BING_MCP_TIMEOUT", "12"))
        self.auto_count = max(1, min(10, int(os.getenv("BING_MCP_AUTO_COUNT", "3"))))
        self.auto_cooldown_seconds = max(5, int(os.getenv("BING_MCP_AUTO_COOLDOWN", "15")))
        self._last_auto_query: str = ""
        self._last_auto_at: float = 0.0
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "bing_search",
                "description": "使用必应中文搜索网络信息。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "搜索关键词"},
                        "count": {
                            "type": "integer",
                            "description": "返回结果条数，默认 10，最大 50",
                        },
                        "offset": {
                            "type": "integer",
                            "description": "结果偏移量（从 0 开始），用于翻页",
                        },
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "crawl_webpage",
                "description": "抓取网页正文（自动跳过部分受限站点）。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "网页地址"},
                        "max_chars": {
                            "type": "integer",
                            "description": "正文最大返回长度，默认 8000",
                        },
                    },
                    "required": ["url"],
                },
            },
        ]

    async def run_tool(self, tool_name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        payload = params or {}

        if tool_name == "bing_search":
            query = str(payload.get("query", "")).strip()
            if not query:
                raise ValueError("bing_search 缺少 query 参数")
            count = self._safe_int(payload.get("count", 10), default=10, minimum=1, maximum=50)
            offset = self._safe_int(payload.get("offset", 0), default=0, minimum=0, maximum=10_000)
            return await asyncio.to_thread(self._bing_search, query, count, offset)

        if tool_name == "crawl_webpage":
            url = str(payload.get("url", "")).strip()
            if not url:
                raise ValueError("crawl_webpage 缺少 url 参数")
            max_chars = self._safe_int(payload.get("max_chars", 8000), default=8000, minimum=500, maximum=50_000)
            return await asyncio.to_thread(self._crawl_webpage, url, max_chars)

        raise ValueError(f"bing_cn_search 不支持的工具: {tool_name}")

    async def auto_context_block(self, user_message: str) -> Optional[str]:
        query = self._extract_search_query(user_message or "")
        if not query:
            return None

        now = time.time()
        if query == self._last_auto_query and now - self._last_auto_at < self.auto_cooldown_seconds:
            return None

        self._last_auto_query = query
        self._last_auto_at = now

        try:
            result = await self.run_tool(
                "bing_search",
                {"query": query, "count": self.auto_count, "offset": 0},
            )
        except Exception as exc:
            return f"已尝试联网搜索“{query}”，但请求失败：{exc}"

        items = result.get("results", [])
        if not items:
            return f"已尝试联网搜索“{query}”，暂未获取到有效结果。"

        lines = [f"已用必应搜索“{query}”，供回答时参考："]
        for idx, item in enumerate(items[: self.auto_count], start=1):
            title = self._truncate(item.get("title", ""), 60)
            snippet = self._truncate(item.get("snippet", ""), 100)
            url = item.get("url", "")
            lines.append(f"{idx}. {title} | {snippet} | {url}")
        return "\n".join(lines)

    def _bing_search(self, query: str, count: int, offset: int) -> Dict[str, Any]:
        params = {
            "q": query,
            "count": count,
            "first": offset + 1,
            "setlang": "zh-Hans",
            "mkt": "zh-CN",
        }
        response = requests.get(
            self.search_url,
            params=params,
            headers=self._headers,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        html_text = response.text or ""
        results = self._parse_bing_results(html_text, max_results=count)
        total_results = self._parse_total_results(html_text)

        return {
            "query": query,
            "count": count,
            "offset": offset,
            "total_results": total_results,
            "results": results,
            "formatted": self._format_search_result_text(query, total_results, results),
        }

    def _crawl_webpage(self, url: str, max_chars: int) -> Dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("仅支持 http/https 网页地址")

        domain = (parsed.hostname or "").lower()
        if self._is_blacklisted(domain):
            return {
                "url": url,
                "title": "",
                "content": "",
                "blacklisted": True,
                "reason": f"域名在黑名单中: {domain}",
            }

        response = requests.get(
            url,
            headers=self._headers,
            timeout=self.timeout_seconds,
            allow_redirects=True,
        )
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" not in content_type and "text" not in content_type:
            return {
                "url": response.url,
                "title": "",
                "content": "",
                "blacklisted": False,
                "unsupported_content_type": content_type,
            }

        page = response.text or ""
        title = self._extract_title(page)
        content = self._extract_main_text(page)

        truncated = len(content) > max_chars
        if truncated:
            content = content[:max_chars].rstrip()

        return {
            "url": response.url,
            "title": title,
            "content": content,
            "content_length": len(content),
            "truncated": truncated,
            "blacklisted": False,
        }

    def _parse_bing_results(self, html_text: str, max_results: int) -> List[Dict[str, str]]:
        blocks = re.findall(
            r"<li\b[^>]*class=\"[^\"]*\bb_algo\b[^\"]*\"[^>]*>(.*?)</li>",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        results: List[Dict[str, str]] = []
        for block in blocks:
            link_match = re.search(
                r"<h2[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>",
                block,
                flags=re.IGNORECASE | re.DOTALL,
            )
            if not link_match:
                continue

            url = html.unescape(link_match.group(1).strip())
            title = self._clean_html(link_match.group(2))

            snippet_match = re.search(
                r"<p[^>]*>(.*?)</p>",
                block,
                flags=re.IGNORECASE | re.DOTALL,
            )
            snippet = self._clean_html(snippet_match.group(1)) if snippet_match else ""

            results.append(
                {
                    "title": title or url,
                    "url": url,
                    "snippet": snippet,
                }
            )
            if len(results) >= max_results:
                break
        return results

    def _parse_total_results(self, html_text: str) -> Optional[int]:
        count_match = re.search(
            r"class=\"[^\"]*\bsb_count\b[^\"]*\"[^>]*>(.*?)</span>",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not count_match:
            return None

        text = self._clean_html(count_match.group(1))
        num_match = re.search(r"(\d[\d,\.]*)", text)
        if not num_match:
            return None

        number = re.sub(r"[^\d]", "", num_match.group(1))
        if not number:
            return None

        try:
            return int(number)
        except ValueError:
            return None

    def _extract_title(self, html_text: str) -> str:
        title_match = re.search(
            r"<title[^>]*>(.*?)</title>",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not title_match:
            return ""
        return self._clean_html(title_match.group(1))

    def _extract_main_text(self, html_text: str) -> str:
        cleaned = re.sub(
            r"<(script|style|noscript|svg|form|iframe)[^>]*>.*?</\1>",
            " ",
            html_text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        article_blocks = re.findall(
            r"<(article|main)\b[^>]*>(.*?)</\1>",
            cleaned,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if article_blocks:
            source = max((content for _, content in article_blocks), key=len, default=cleaned)
        else:
            source = cleaned

        text = re.sub(r"<[^>]+>", " ", source)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _clean_html(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value or "")
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _is_blacklisted(self, domain: str) -> bool:
        for blocked in self._BLACKLIST_DOMAINS:
            if domain == blocked or domain.endswith(f".{blocked}"):
                return True
        return False

    def _extract_search_query(self, message: str) -> str:
        text = (message or "").strip()
        if not text:
            return ""

        patterns = [
            r"(?:帮我|请|麻烦)?(?:用必应|联网|上网)?(?:搜索|搜一下|搜一搜|查一下|查一查|查查)\s*(?P<q>.+)$",
            r"(?:帮我|请|麻烦)?(?:在网上|联网|上网)(?:搜|查)\s*(?P<q>.+)$",
            r"(?:帮我|请)?(?:查找|查询)\s*(?P<q>.+)$",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return self._normalize_query(match.group("q"))

        if any(key in text for key in ("最新进展", "最新消息", "最新动态")):
            return self._normalize_query(text)

        return ""

    def _normalize_query(self, query: str) -> str:
        normalized = (query or "").strip().strip("。？！!?,，：:；;\"'“”‘’")
        normalized = re.sub(r"\s+", " ", normalized)
        if len(normalized) > 120:
            normalized = normalized[:120].rstrip()
        return normalized

    def _format_search_result_text(
        self, query: str, total_results: Optional[int], results: List[Dict[str, str]]
    ) -> str:
        total_text = f"{total_results}" if isinstance(total_results, int) else "未知"
        lines = [f"搜索关键词: {query}", f"搜索结果总量(估计): {total_text}", ""]
        for index, item in enumerate(results, start=1):
            lines.append(f"[{index}] {item.get('title', '')}")
            lines.append(f"链接: {item.get('url', '')}")
            lines.append(f"摘要: {item.get('snippet', '')}")
            lines.append("")
        return "\n".join(lines).strip()

    def _safe_int(self, value: Any, default: int, minimum: int, maximum: int) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        return max(minimum, min(maximum, parsed))

    def _truncate(self, text: str, limit: int) -> str:
        text = (text or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."
