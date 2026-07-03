import json
import logging
import unittest

from utils.logger import JsonFormatter


class TestJsonFormatter(unittest.TestCase):
    def setUp(self):
        self.fmt = JsonFormatter()

    def test_format_basic(self):
        record = logging.LogRecord(
            name="lte_bot.test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        result = self.fmt.format(record)
        data = json.loads(result)
        self.assertEqual(data["l"], "INFO")
        self.assertEqual(data["n"], "lte_bot.test")
        self.assertEqual(data["m"], "hello world")
        self.assertIn("t", data)

    def test_format_with_exception(self):
        try:
            1 / 0
        except ZeroDivisionError:
            import sys

            exc_info = sys.exc_info()
            record = logging.LogRecord(
                name="lte_bot.test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=1,
                msg="oops",
                args=(),
                exc_info=exc_info,
            )
        result = self.fmt.format(record)
        data = json.loads(result)
        self.assertEqual(data["l"], "ERROR")
        self.assertEqual(data["m"], "oops")
        self.assertIn("exc", data)
        self.assertIn("ZeroDivisionError", data["exc"])
