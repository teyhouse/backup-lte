import unittest
from datetime import datetime, timezone

from data_fetcher import LteData, _parse_data, MOCK_DATA
from utils.formatter import (
    _usage_bar,
    _usage_color,
    _format_bytes,
    build_alert_embed,
    build_all_clear_embed,
    build_embed,
)
from utils.logger import JsonFormatter


class TestUsageBar(unittest.TestCase):
    def test_zero_percent(self):
        self.assertEqual(_usage_bar(0, 10), "░" * 10)

    def test_hundred_percent(self):
        self.assertEqual(_usage_bar(100, 10), "█" * 10)

    def test_fifty_percent(self):
        self.assertEqual(_usage_bar(50, 10), "█" * 5 + "░" * 5)

    def test_twelve_length_with_25_percent(self):
        bar = _usage_bar(25, 12)
        self.assertEqual(len(bar), 12)
        self.assertEqual(bar.count("█"), 3)


class TestUsageColor(unittest.TestCase):
    def test_green_below_80(self):
        self.assertEqual(_usage_color(0), 0x2ECC71)
        self.assertEqual(_usage_color(79, ), 0x2ECC71)

    def test_yellow_80_to_89(self):
        self.assertEqual(_usage_color(80), 0xF1C40F)
        self.assertEqual(_usage_color(85), 0xF1C40F)

    def test_red_90_and_above(self):
        self.assertEqual(_usage_color(90), 0xE74C3C)
        self.assertEqual(_usage_color(100), 0xE74C3C)


class TestFormatBytes(unittest.TestCase):
    def test_bytes(self):
        self.assertEqual(_format_bytes(500), "500 B")

    def test_kb(self):
        self.assertEqual(_format_bytes(2048), "2.0 KB")

    def test_mb(self):
        self.assertEqual(_format_bytes(1_048_576), "1.0 MB")

    def test_gb(self):
        self.assertEqual(_format_bytes(2_147_483_648), "2.0 GB")


class TestBuildEmbed(unittest.TestCase):
    def setUp(self):
        self.data = _parse_data(MOCK_DATA)

    def test_title(self):
        embed = build_embed(self.data)
        self.assertIn("MagentaMobil Prepaid M", embed.title)

    def test_color_green_for_25_percent(self):
        embed = build_embed(self.data)
        self.assertEqual(embed.color.value, 0x2ECC71)

    def test_fields_count(self):
        embed = build_embed(self.data)
        self.assertEqual(len(embed.fields), 3)

    def test_usage_field_shows_percent(self):
        embed = build_embed(self.data)
        usage = embed.fields[0]
        self.assertEqual(usage.name, "Usage")
        self.assertIn("25%", usage.value)

    def test_volume_field_shows_total(self):
        embed = build_embed(self.data)
        volume = embed.fields[1]
        self.assertEqual(volume.name, "Volume")
        self.assertIn("20 GB", volume.value)

    def test_time_field_shows_days(self):
        embed = build_embed(self.data)
        time_field = embed.fields[2]
        self.assertEqual(time_field.name, "Time")
        self.assertIn("27 days", time_field.value)


class TestAlertEmbed(unittest.TestCase):
    def setUp(self):
        self.data = _parse_data(MOCK_DATA)

    def test_title(self):
        embed = build_alert_embed(self.data)
        self.assertEqual(embed.title, "⚠️ Data Usage Alert")

    def test_color_red(self):
        embed = build_alert_embed(self.data)
        self.assertEqual(embed.color.value, 0xE74C3C)


class TestAllClearEmbed(unittest.TestCase):
    def test_title(self):
        embed = build_all_clear_embed(50.0, 10_737_418_240)
        self.assertEqual(embed.title, "✅ Usage Normalized")

    def test_color_green(self):
        embed = build_all_clear_embed(50.0, 10_737_418_240)
        self.assertEqual(embed.color.value, 0x2ECC71)

    def test_shows_formatted_bytes(self):
        embed = build_all_clear_embed(50.0, 10_737_418_240)
        self.assertIn("10.0 GB", embed.description)

    def test_shows_percent(self):
        embed = build_all_clear_embed(50.0, 10_737_418_240)
        self.assertIn("50%", embed.description)
