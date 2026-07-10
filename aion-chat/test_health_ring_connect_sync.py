import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def read_health_html() -> str:
    return (ROOT / "static" / "health.html").read_text(encoding="utf-8")


def extract_function(source: str, name: str) -> str:
    start = source.index(f"function {name}")
    brace = source.index("{", start)
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise AssertionError(f"Could not find end of function {name}")


class HealthRingConnectSyncTests(unittest.TestCase):
    def test_connect_initialization_syncs_history_without_immediate_heart_measurement(self):
        html = read_health_html()
        init = extract_function(html, "deviceInitHandshake")

        self.assertIn("deviceReady = true;", init)
        self.assertIn("await syncRingHistory(true);", init)
        self.assertIn("startHeartAutoLoop(false);", init)
        self.assertNotIn("startHeartAutoLoop(true)", init)

    def test_automatic_heart_loop_does_not_start_measurements(self):
        html = read_health_html()
        loop = extract_function(html, "startHeartAutoLoop")

        self.assertNotIn("runHeartAutoMeasurement('auto-connect')", loop)
        self.assertNotIn("runHeartAutoMeasurement('auto-10min')", loop)
        self.assertNotIn("setInterval", loop)

    def test_auto_history_sync_uses_comprehensive_snapshot(self):
        html = read_health_html()
        sync = extract_function(html, "syncRingHistory")

        self.assertIn("[[DT_HEALTH_ALL, '综合']]", sync)
        self.assertIn("api('POST', '/api/health/ring/latest', payload)", sync)
        self.assertNotIn("DT_HEALTH_HEART", sync)
        self.assertNotIn("uploadLatestHeartHistory", sync)

    def test_manual_measure_button_still_starts_manual_heart_measurement(self):
        html = read_health_html()
        manual = extract_function(html, "measureHeartRateNow")

        self.assertIn("startHeartMeasurement('manual')", manual)


if __name__ == "__main__":
    unittest.main()
