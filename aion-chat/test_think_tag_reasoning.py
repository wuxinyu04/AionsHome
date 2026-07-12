import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai_providers import ThinkTagReasoningFilter, _apply_codex_usage_meta, extract_think_tag_reasoning


class ThinkTagReasoningTests(unittest.TestCase):
    def test_moves_standard_think_block_out_of_visible_content(self):
        visible, reasoning = extract_think_tag_reasoning(
            "<think>\ninternal plan\n</think>\n\nVisible reply.",
            "",
        )

        self.assertEqual(visible, "Visible reply.")
        self.assertEqual(reasoning, "internal plan")

    def test_appends_multiple_think_blocks_to_existing_reasoning(self):
        visible, reasoning = extract_think_tag_reasoning(
            "Lead.\n<think>first</think>\nMiddle.\n<think>\nsecond\n</think>\nTail.",
            "native reasoning",
        )

        self.assertEqual(visible, "Lead.\n\nMiddle.\n\nTail.")
        self.assertEqual(reasoning, "native reasoning\n\nfirst\n\nsecond")

    def test_leaves_text_without_standard_think_tags_unchanged(self):
        visible, reasoning = extract_think_tag_reasoning(
            "Visible <thought>not this helper</thought> reply.",
            "native reasoning",
        )

        self.assertEqual(visible, "Visible <thought>not this helper</thought> reply.")
        self.assertEqual(reasoning, "native reasoning")

    def test_stream_filter_handles_tags_split_across_chunks(self):
        meta = {}
        filt = ThinkTagReasoningFilter(meta)

        visible = "".join([
            filt.feed("Hi <thi"),
            filt.feed("nk>secret</thi"),
            filt.feed("nk> there"),
            filt.flush(),
        ])

        self.assertEqual(visible, "Hi  there")
        self.assertEqual(meta.get("reasoning_content"), "secret")


class CodexUsageMetaTests(unittest.TestCase):
    def test_maps_codex_cli_usage_to_system_log_token_shape(self):
        meta = {}

        _apply_codex_usage_meta(
            meta,
            {
                "input_tokens": 100,
                "cached_input_tokens": 40,
                "output_tokens": 25,
                "reasoning_output_tokens": 7,
            },
        )

        self.assertEqual(meta["prompt_tokens"], 100)
        self.assertEqual(meta["completion_tokens"], 25)
        self.assertEqual(meta["total_tokens"], 125)
        self.assertEqual(meta["raw"]["prompt_tokens_details"]["cached_tokens"], 40)
        self.assertEqual(meta["raw"]["completion_tokens_details"]["reasoning_tokens"], 7)


if __name__ == "__main__":
    unittest.main()
