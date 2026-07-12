import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from routes import chatroom as chatroom_routes


class ConnorCodexUsageForwardingTests(unittest.IsolatedAsyncioTestCase):
    async def test_connor_codex_stream_passes_usage_meta_to_cli_call(self):
        seen = {}

        async def fake_stream_connor_cli(*, messages, meta=None):
            seen["messages"] = messages
            seen["meta"] = meta
            if meta is not None:
                meta["prompt_tokens"] = 3
            yield "ok"

        messages = [{"role": "user", "content": "hello"}]
        meta = {}

        with (
            patch("routes.chatroom._resolve_connor_model", return_value="Codex"),
            patch("routes.chatroom.stream_connor_cli", new=fake_stream_connor_cli),
        ):
            chunks = [
                chunk
                async for chunk in chatroom_routes._stream_connor_model(messages, "Codex", meta)
            ]

        self.assertEqual(chunks, ["ok"])
        self.assertIs(seen["messages"], messages)
        self.assertIs(seen["meta"], meta)
        self.assertEqual(meta["prompt_tokens"], 3)


if __name__ == "__main__":
    unittest.main()
