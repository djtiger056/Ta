import asyncio
import sys
from pathlib import Path

import pytest

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.mcp.bing_cn_search import BingCnSearchPlugin


class _MockResponse:
    def __init__(self, text: str, *, url: str = "https://cn.bing.com/search", content_type: str = "text/html"):
        self.text = text
        self.url = url
        self.status_code = 200
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self) -> None:
        return None


@pytest.mark.asyncio
async def test_bing_search_tool_parses_results(monkeypatch):
    html = """
    <html>
      <body>
        <span class="sb_count">约 12,345 条结果</span>
        <li class="b_algo">
          <h2><a href="https://example.com/a">示例标题A</a></h2>
          <div class="b_caption"><p>示例摘要A</p></div>
        </li>
        <li class="b_algo">
          <h2><a href="https://example.com/b">示例标题B</a></h2>
          <div class="b_caption"><p>示例摘要B</p></div>
        </li>
      </body>
    </html>
    """

    def _mock_get(*args, **kwargs):
        return _MockResponse(html)

    monkeypatch.setattr("backend.mcp.bing_cn_search.requests.get", _mock_get)
    plugin = BingCnSearchPlugin()

    result = await plugin.run_tool(
        "bing_search",
        {"query": "测试关键词", "count": 2, "offset": 0},
    )

    assert result["query"] == "测试关键词"
    assert result["total_results"] == 12345
    assert len(result["results"]) == 2
    assert result["results"][0]["title"] == "示例标题A"
    assert result["results"][0]["url"] == "https://example.com/a"


def test_crawl_webpage_blacklist_short_circuit():
    plugin = BingCnSearchPlugin()
    result = asyncio.run(
        plugin.run_tool("crawl_webpage", {"url": "https://www.zhihu.com/question/1"})
    )
    assert result["blacklisted"] is True
    assert "黑名单" in result["reason"]


@pytest.mark.asyncio
async def test_auto_context_trigger_and_cooldown(monkeypatch):
    plugin = BingCnSearchPlugin()
    plugin.auto_cooldown_seconds = 60

    async def _mock_run_tool(tool_name, params):
        assert tool_name == "bing_search"
        return {
            "results": [
                {
                    "title": "结果标题",
                    "snippet": "结果摘要",
                    "url": "https://example.com/result",
                }
            ]
        }

    monkeypatch.setattr(plugin, "run_tool", _mock_run_tool)

    first = await plugin.auto_context_block("帮我搜索 人工智能最新进展")
    second = await plugin.auto_context_block("帮我搜索 人工智能最新进展")

    assert first is not None
    assert "已用必应搜索" in first
    assert second is None
