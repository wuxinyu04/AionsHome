import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


class TavilySettingsUiTests(unittest.TestCase):
    def test_settings_page_exposes_and_saves_tavily_key(self):
        html = (ROOT / "static" / "settings.html").read_text(encoding="utf-8")

        self.assertIn('id="tavilyApiKeyInput"', html)
        self.assertIn("Tavily API Key", html)
        self.assertIn("s.tavily_api_key", html)
        self.assertIn('tavily_api_key: $("tavilyApiKeyInput").value.trim()', html)

    def test_personal_data_cleanup_mentions_tavily_key(self):
        cleanup_bat = (ROOT.parent / "清理个人数据.bat").read_text(encoding="utf-8")

        self.assertIn("Tavily", cleanup_bat)


if __name__ == "__main__":
    unittest.main()
