import unittest
from datetime import datetime

from data_fetcher import LteData, _parse_data, MOCK_DATA, _parse_ms_timestamp


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
        self.assertEqual(data.validity_period_weeks, 4)
        self.assertEqual(data.subscriptions, ["tns", "xtraSpeed"])
        self.assertIsInstance(data.used_at, datetime)

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
