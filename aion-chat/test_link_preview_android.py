import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LinkPreviewAndroidTests(unittest.TestCase):
    def test_android_webview_handles_blank_link_preview_targets(self):
        src = (
            ROOT
            / "AionApp"
            / "app"
            / "src"
            / "main"
            / "java"
            / "com"
            / "aion"
            / "chat"
            / "WebViewActivity.java"
        ).read_text(encoding="utf-8")

        self.assertIn("setSupportMultipleWindows(true)", src)
        self.assertIn("setJavaScriptCanOpenWindowsAutomatically(true)", src)
        self.assertIn("onCreateWindow", src)
        self.assertIn("AionExternal", src)


if __name__ == "__main__":
    unittest.main()
