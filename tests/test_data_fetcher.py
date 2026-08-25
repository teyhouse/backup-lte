import random
import unittest
from datetime import UTC, datetime

from data_fetcher import (
    MOCK_DATA,
    _build_browser_profile,
    _build_headers,
    _parse_data,
    _parse_ms_timestamp,
)


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


class TestBrowserProfile(unittest.TestCase):
    def test_always_looks_like_a_browser(self):
        for _ in range(100):
            profile = _build_browser_profile()
            self.assertTrue(profile["ua"].startswith("Mozilla/5.0"))
            self.assertIn("AppleWebKit", profile["ua"])
            self.assertIn(profile["platform"], ("android", "ios"))

    def test_android_variant_shape(self):
        random.seed(1)
        android_profile = None
        for _ in range(200):
            profile = _build_browser_profile()
            if profile["platform"] == "android":
                android_profile = profile
                break
        self.assertIsNotNone(android_profile)
        self.assertIn("Linux; Android", android_profile["ua"])
        major = android_profile["chrome_major"]
        self.assertRegex(android_profile["ua"], rf"Chrome/{major}\.0\.0\.0 Mobile Safari/537\.36")

    def test_ios_variant_shape(self):
        random.seed(2)
        ios_profile = None
        for _ in range(200):
            profile = _build_browser_profile()
            if profile["platform"] == "ios":
                ios_profile = profile
                break
        self.assertIsNotNone(ios_profile)
        self.assertIsNone(ios_profile["chrome_major"])
        self.assertIn("CPU iPhone OS", ios_profile["ua"])
        self.assertIn("Safari/604.1", ios_profile["ua"])

    def test_varies_between_calls(self):
        random.seed(3)
        agents = {_build_browser_profile()["ua"] for _ in range(50)}
        self.assertGreater(len(agents), 1)


class TestRequestHeaders(unittest.TestCase):
    def test_common_headers_present(self):
        for _ in range(100):
            headers = _build_headers(_build_browser_profile())
            self.assertIn("de", headers["Accept-Language"])
            self.assertTrue(headers["Accept"].startswith("text/html"))
            self.assertEqual(headers["Accept-Encoding"], "gzip, deflate, br")
            self.assertEqual(headers["Connection"], "keep-alive")

    def test_chrome_client_hints_match_ua_version(self):
        random.seed(4)
        checked = False
        for _ in range(200):
            profile = _build_browser_profile()
            if profile["platform"] != "android":
                continue
            headers = _build_headers(profile)
            major = str(profile["chrome_major"])
            self.assertIn(f'"Google Chrome";v="{major}"', headers["Sec-CH-UA"])
            self.assertEqual(headers["Sec-CH-UA-Mobile"], "?1")
            self.assertEqual(headers["Sec-CH-UA-Platform"], '"Android"')
            self.assertEqual(headers["Sec-Fetch-Site"], "none")
            self.assertIn("Upgrade-Insecure-Requests", headers)
            checked = True
            break
        self.assertTrue(checked)

    def test_ios_has_no_client_hints(self):
        random.seed(5)
        checked = False
        for _ in range(200):
            profile = _build_browser_profile()
            if profile["platform"] != "ios":
                continue
            headers = _build_headers(profile)
            for name in headers:
                self.assertFalse(name.startswith("Sec-"), name)
            self.assertNotIn("Upgrade-Insecure-Requests", headers)
            self.assertIn("iPhone", headers["User-Agent"])
            checked = True
            break
        self.assertTrue(checked)

    def test_headers_vary_between_calls(self):
        random.seed(6)
        combos = {
            (
                _build_headers(_build_browser_profile()).get("DNT"),
                _build_headers(_build_browser_profile())["Accept-Language"],
            )
            for _ in range(50)
        }
        self.assertGreater(len(combos), 1)
