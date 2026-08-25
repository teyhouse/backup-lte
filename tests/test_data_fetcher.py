import random
import unittest
from datetime import UTC, datetime

from data_fetcher import MOCK_DATA, _build_user_agent, _parse_data, _parse_ms_timestamp


class TestParseData(unittest.TestCase):
    def test_mock_data_fields(self):
        data = _parse_data(MOCK_DATA)
        self.assertEqual(data.pass_name, "MagentaMobil Prepaid M")
        self.assertEqual(data.pass_type, 103)
        self.assertEqual(data.pass_stage, 1)
        self.assertEqual(data.session_state, 0)
        self.assertEqual(data.total_bytes, 21474836480)
        self.assertEqual(data.total_bytes_str, "20 GB")
        self.assertEqual(data.used_bytes, 5368709120)
        self.assertEqual(data.used_bytes_str, "5 GB")
        self.assertEqual(data.used_percent, 25.0)
        self.assertEqual(data.remaining_seconds, 2332800)
        self.assertEqual(data.next_update_seconds, 10800)
        self.assertEqual(data.subscriptions, ["tns", "xtraSpeed"])
        self.assertEqual(data.valid_until, datetime(2026, 8, 24, tzinfo=UTC))
        self.assertIsInstance(data.last_update, datetime)

    def test_properties(self):
        data = _parse_data(MOCK_DATA)
        self.assertEqual(data.remaining_bytes, 16106127360)
        self.assertEqual(data.remaining_days, 27)
        self.assertEqual(data.status, "active")

    def test_zero_usage(self):
        raw = dict(MOCK_DATA, usedVolume=0, usedVolumeStr="0 kB", usedPercentage=0.0)
        data = _parse_data(raw)
        self.assertEqual(data.used_bytes, 0)
        self.assertEqual(data.used_percent, 0.0)
        self.assertEqual(data.remaining_bytes, data.total_bytes)

    def test_full_usage(self):
        raw = dict(
            MOCK_DATA,
            usedVolume=21474836480,
            usedVolumeStr="20 GB",
            usedPercentage=100.0,
        )
        data = _parse_data(raw)
        self.assertEqual(data.used_percent, 100.0)
        self.assertEqual(data.remaining_bytes, 0)

    def test_inactive_state(self):
        raw = dict(MOCK_DATA, sessionState=1)
        data = _parse_data(raw)
        self.assertEqual(data.status, "inactive")


class TestTimestampParsing(unittest.TestCase):
    def test_ms_timestamp(self):
        dt = _parse_ms_timestamp(1782835472000)
        self.assertIsInstance(dt, datetime)
        self.assertEqual(dt.year, 2026)


class TestUserAgent(unittest.TestCase):
    def test_always_looks_like_a_browser(self):
        for _ in range(100):
            ua = _build_user_agent()
            self.assertTrue(ua.startswith("Mozilla/5.0"))
            self.assertIn("AppleWebKit", ua)

    def test_android_variant_shape(self):
        random.seed(1)
        android_ua = None
        for _ in range(200):
            ua = _build_user_agent()
            if "Android" in ua:
                android_ua = ua
                break
        self.assertIsNotNone(android_ua)
        self.assertIn("Linux; Android", android_ua)
        self.assertRegex(android_ua, r"Chrome/\d+\.0\.0\.0 Mobile Safari/537\.36")

    def test_ios_variant_shape(self):
        random.seed(2)
        ios_ua = None
        for _ in range(200):
            ua = _build_user_agent()
            if "iPhone" in ua:
                ios_ua = ua
                break
        self.assertIsNotNone(ios_ua)
        self.assertIn("CPU iPhone OS", ios_ua)
        self.assertIn("Safari/604.1", ios_ua)

    def test_varies_between_calls(self):
        random.seed(3)
        agents = {_build_user_agent() for _ in range(50)}
        self.assertGreater(len(agents), 1)
