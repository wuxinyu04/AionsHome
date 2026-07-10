import unittest

from ai_providers import build_gemini_contents, build_multimodal_messages, _messages_have_images
from link_preview import link_preview_fallback


class LinkPreviewAiContextTests(unittest.TestCase):
    def test_link_preview_attachments_are_not_treated_as_media_files(self):
        card = link_preview_fallback("https://example.com/articles/heavy-caliber")
        history = [{"role": "user", "content": "see this https://example.com/articles/heavy-caliber", "attachments": [card]}]

        self.assertFalse(_messages_have_images(history))
        self.assertEqual(
            build_multimodal_messages(history),
            [{"role": "user", "content": "see this https://example.com/articles/heavy-caliber"}],
        )
        self.assertEqual(
            build_gemini_contents(history),
            [{"role": "user", "parts": [{"text": "see this https://example.com/articles/heavy-caliber"}]}],
        )


if __name__ == "__main__":
    unittest.main()
