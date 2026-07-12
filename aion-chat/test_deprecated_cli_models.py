import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import ai_providers
import config
from routes import date_theater as date_theater_routes
from routes import settings


async def fake_siliconflow(*args, **kwargs):
    yield "safe-model"


async def fake_gemini_cli(*args, **kwargs):
    yield "deprecated-cli"


class DeprecatedCliModelTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_list_shows_antigravity_but_hides_gemini_cli(self):
        # gemini_cli 线路被 Google 关闭已停用；antigravity_cli (agy) 重新启用，应可见。
        with patch.dict(
            config.MODELS,
            {
                "AGY-3.1pro": {
                    "provider": "antigravity_cli",
                    "model": "gemini-3.1-pro-preview",
                    "vision": True,
                }
            },
            clear=False,
        ):
            rows = await settings.list_models()

        providers = {row["provider"] for row in rows}
        keys = {row["key"] for row in rows}
        self.assertNotIn("gemini_cli", providers)
        self.assertIn("antigravity_cli", providers)
        self.assertNotIn("CLI-3.1pro", keys)
        self.assertIn("AGY-3.1pro", keys)

    async def test_date_theater_model_rows_show_antigravity_but_hide_gemini_cli(self):
        with patch.dict(
            date_theater_routes.MODELS,
            {
                "AGY-3.1pro": {
                    "provider": "antigravity_cli",
                    "model": "gemini-3.1-pro-preview",
                    "vision": True,
                }
            },
            clear=False,
        ):
            rows = date_theater_routes._model_rows()

        providers = {row["provider"] for row in rows}
        keys = {row["key"] for row in rows}
        self.assertNotIn("gemini_cli", providers)
        self.assertIn("antigravity_cli", providers)
        self.assertNotIn("CLI-3.1pro", keys)
        self.assertIn("AGY-3.1pro", keys)

    async def test_date_theater_resolves_deprecated_locked_model_to_visible_model(self):
        with patch.dict(
            date_theater_routes.MODELS,
            {
                "Visible": {"provider": "siliconflow", "model": "safe", "vision": False},
                "CLI-3.1pro": {"provider": "gemini_cli", "model": "old", "vision": True},
            },
            clear=True,
        ), patch("routes.date_theater.load_chatroom_config", return_value={"aion_model": ""}):
            resolved = date_theater_routes._resolve_model("", {"model_locked": True, "model": "CLI-3.1pro"})

        self.assertEqual(resolved, "Visible")

    async def test_stream_ai_falls_back_instead_of_calling_gemini_cli(self):
        # CLI-3.1pro 是已停用的 gemini_cli 线路。stream_ai 不应真的去调 call_gemini_cli。
        # 实际行为由 resolve_model_key 在入口处理：把 CLI-3.1pro 重定向到一个非停用的 visible model。
        # 测试用 sentinel 记录"被调用次数"——call_gemini_cli 应该是 0 次。
        called = {"gemini_cli": 0, "siliconflow": 0, "gemini": 0}

        async def tracking_gemini_cli(*args, **kwargs):
            called["gemini_cli"] += 1
            yield "deprecated-cli"

        async def tracking_siliconflow(*args, **kwargs):
            called["siliconflow"] += 1
            yield "safe-model"

        async def tracking_gemini(*args, **kwargs):
            called["gemini"] += 1
            yield "real-gemini"

        with (
            patch("ai_providers.call_siliconflow", new=tracking_siliconflow),
            patch("ai_providers.call_gemini_cli", new=tracking_gemini_cli),
            patch("ai_providers.call_gemini", new=tracking_gemini),
        ):
            chunks = [
                chunk
                async for chunk in ai_providers.stream_ai(
                    [{"role": "user", "content": "hello"}],
                    "CLI-3.1pro",
                )
            ]

        # 关键断言：已停用的 gemini_cli 线路不能被调用
        self.assertEqual(called["gemini_cli"], 0, "stopped gemini_cli was invoked")
        # 同时要给一个非空结果（说明被 fallback 到了某个 visible model）
        self.assertTrue(len(chunks) > 0, "no fallback produced")


class ModelResolutionTests(unittest.TestCase):
    def test_codex_defaults_to_gpt_5_5_with_gpt_5_6_tiers_disabled(self):
        self.assertEqual(config.BUILTIN_MODELS["Codex"]["provider"], "codex_cli")
        self.assertEqual(config.BUILTIN_MODELS["Codex"]["model"], "gpt-5.5")
        self.assertNotIn("Codex-Sol", config.BUILTIN_MODELS)
        self.assertNotIn("Codex-Luna", config.BUILTIN_MODELS)

    def test_deprecated_cli_model_resolves_to_visible_model(self):
        resolved = config.resolve_model_key("CLI-3.1pro")
        self.assertNotEqual(resolved, "CLI-3.1pro")
        self.assertFalse(config.is_model_deprecated(resolved))


if __name__ == "__main__":
    unittest.main()
