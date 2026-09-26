import unittest

from logfmtkit.codec import LogfmtError, decode, encode


class EncodeTest(unittest.TestCase):
    def test_simple_pair(self):
        self.assertEqual(encode([("a", "1")]), "a=1")

    def test_two_pairs(self):
        self.assertEqual(encode([("a", "1"), ("b", "2")]), "a=1 b=2")

    def test_bare_key(self):
        self.assertEqual(encode([("flag", True)]), "flag")

    def test_empty(self):
        self.assertEqual(encode([]), "")


class DecodeTest(unittest.TestCase):
    def test_simple_line(self):
        self.assertEqual(decode("a=1 b=2"), [("a", "1"), ("b", "2")])

    def test_bare_key(self):
        self.assertEqual(decode("flag"), [("flag", True)])

    def test_empty_line(self):
        self.assertEqual(decode(""), [])

    def test_value_with_equals(self):
        self.assertEqual(decode("a=b=c"), [("a", "b=c")])

    def test_error_type_exists(self):
        self.assertTrue(issubclass(LogfmtError, Exception))
