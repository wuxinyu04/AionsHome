import unittest

from web_search import (
    WEB_EXTRACT_CMD_PATTERN,
    WEB_SEARCH_CMD_PATTERN,
    clean_web_command_text,
    format_tavily_context,
)


class WebSearchCommandTests(unittest.TestCase):
    def test_clean_web_commands_removes_search_and_extract_tags(self):
        text = "我去查一下[WEB_SEARCH: Tavily API pricing][WEB_EXTRACT:https://example.com/a]等我。"

        self.assertEqual(clean_web_command_text(text), "我去查一下等我。")

    def test_command_patterns_accept_full_width_colons(self):
        self.assertEqual(WEB_SEARCH_CMD_PATTERN.findall("[WEB_SEARCH：OpenAI news]"), ["OpenAI news"])
        self.assertEqual(WEB_EXTRACT_CMD_PATTERN.findall("[WEB_EXTRACT：https://example.com]"), ["https://example.com"])


class TavilyContextFormattingTests(unittest.TestCase):
    def test_format_search_context_keeps_clean_short_sources(self):
        payload = {
            "query": "OpenAI web search",
            "answer": "A short answer from Tavily should be included when present.",
            "results": [
                {
                    "title": "OpenAI Web Search",
                    "url": "https://developers.openai.com/api/docs/guides/tools-web-search",
                    "content": "Useful summary " * 80,
                    "raw_content": "raw page content should not be included",
                    "published_date": "2026-07-01",
                    "score": 0.92,
                }
            ],
        }

        text = format_tavily_context(payload, kind="search", max_chars_per_item=180)

        self.assertIn("【联网搜索结果】", text)
        self.assertIn("查询：OpenAI web search", text)
        self.assertIn("1. OpenAI Web Search", text)
        self.assertIn("https://developers.openai.com/api/docs/guides/tools-web-search", text)
        self.assertIn("发布时间：2026-07-01", text)
        self.assertNotIn("raw page content", text)
        self.assertLess(len(text), 900)


if __name__ == "__main__":
    unittest.main()
