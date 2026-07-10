import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from chatroom import _parse_digest_result
from diary import parse_diary_payload
from gift import judge_and_send_gift
from memory import _parse_json_response


class MemoryDigestJsonExtractionTests(unittest.TestCase):
    def test_main_memory_digest_parser_ignores_prose_around_json(self):
        raw = (
            "Okay, I will start summarizing memory.\n"
            '{"memories":[{"content":"2026-07-05, user likes tea","type":"daily"}],'
            '"discard_summary":"none"}'
            "\nDone."
        )

        parsed = _parse_json_response(raw)

        self.assertIsInstance(parsed, dict)
        self.assertEqual(parsed["memories"][0]["content"], "2026-07-05, user likes tea")

    def test_chatroom_digest_parser_skips_non_json_braces_before_json(self):
        raw = (
            "Okay {not JSON}, I will start summarizing memory.\n"
            '{"memories":[{"content":"2026-07-05, group note","type":"daily"}],'
            '"discard_summary":"none"}'
        )

        parsed = _parse_digest_result(raw)

        self.assertIsInstance(parsed, dict)
        self.assertIn("memories", parsed)
        self.assertEqual(parsed["memories"][0]["content"], "2026-07-05, group note")


class DigestFollowupJsonExtractionTests(unittest.TestCase):
    def test_diary_payload_keeps_moment_and_gift_decision_when_wrapped_in_prose(self):
        raw = (
            "Okay {not JSON}, here is the diary payload.\n"
            '{"diary":{"title":"Today","content":"Wrote a note","mood":"calm"},'
            '"post_moment":true,'
            '"moment":{"content":"A tiny update","expect_reply":true},'
            '"givegift":true,'
            '"gift":{"image_prompt":"warm watercolor bookmark","message":"For you"}}'
            "\nFinished."
        )

        payload = parse_diary_payload(raw)

        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["diary"]["content"], "Wrote a note")
        self.assertTrue(payload["post_moment"])
        self.assertEqual(payload["moment"]["content"], "A tiny update")
        self.assertTrue(payload["givegift"])
        self.assertEqual(payload["gift"]["image_prompt"], "warm watercolor bookmark")


class GiftDecisionJsonExtractionTests(unittest.IsolatedAsyncioTestCase):
    async def test_judge_and_send_gift_ignores_prose_around_json(self):
        async def fake_call(messages, model_key, temperature=None, *, trace_label=""):
            return (
                "Okay, I will judge whether to send a gift.\n"
                '{"givegift":false,"image_prompt":"","message":""}'
                "\nNo gift this time."
            )

        send_gift = AsyncMock()
        with patch("ai_providers.simple_ai_call", new=fake_call), patch(
            "gift.send_gift_from_decision", new=send_gift
        ):
            await judge_and_send_gift(
                ["2026-07-05, user mentioned tea"],
                [],
                "",
                "AI",
                "User",
                "model-key",
                "conv-id",
            )

        send_gift.assert_awaited_once()
        decision = send_gift.await_args.args[0]
        self.assertEqual(decision["givegift"], False)


if __name__ == "__main__":
    unittest.main()
