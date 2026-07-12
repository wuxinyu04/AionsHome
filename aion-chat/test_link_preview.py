import unittest

from link_preview import extract_urls, link_preview_from_html, link_preview_fallback


class LinkPreviewTests(unittest.TestCase):
    def test_extract_urls_strips_trailing_punctuation_and_dedupes(self):
        text = "看看 http://hyena-home.com/，还有 https://example.com/path?q=1。重复：https://example.com/path?q=1"

        self.assertEqual(
            extract_urls(text),
            ["http://hyena-home.com/", "https://example.com/path?q=1"],
        )

    def test_link_preview_from_html_reads_common_metadata(self):
        html = """
        <html>
          <head>
            <meta property="og:title" content="Hyena Home">
            <meta property="og:description" content="A small page for testing.">
            <meta property="og:image" content="/cover.png">
            <meta property="og:site_name" content="Hyena">
            <link rel="shortcut icon" href="/favicon.ico">
          </head>
        </html>
        """

        card = link_preview_from_html("http://hyena-home.com/post", html)

        self.assertEqual(card["type"], "link_preview")
        self.assertEqual(card["url"], "http://hyena-home.com/post")
        self.assertEqual(card["title"], "Hyena Home")
        self.assertEqual(card["description"], "A small page for testing.")
        self.assertEqual(card["site_name"], "Hyena")
        self.assertEqual(card["image"], "http://hyena-home.com/cover.png")
        self.assertEqual(card["favicon"], "http://hyena-home.com/favicon.ico")

    def test_fallback_uses_hostname_when_metadata_is_unavailable(self):
        card = link_preview_fallback("https://example.com/articles/hello")

        self.assertEqual(card["type"], "link_preview")
        self.assertEqual(card["title"], "example.com")
        self.assertEqual(card["site_name"], "example.com")
        self.assertEqual(card["url"], "https://example.com/articles/hello")


if __name__ == "__main__":
    unittest.main()
