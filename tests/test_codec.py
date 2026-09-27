import unittest

from logfmtkit.codec import LogfmtError, decode, decode_stream, encode, encode_stream


class EncodeTest(unittest.TestCase):
    def test_simple_pair(self):
        self.assertEqual(encode([("a", "1")]), "a=1")

    def test_two_pairs(self):
        self.assertEqual(encode([("a", "1"), ("b", "2")]), "a=1 b=2")

    def test_bare_key(self):
        self.assertEqual(encode([("flag", True)]), "flag")

    def test_empty(self):
        self.assertEqual(encode([]), "")

    def test_value_with_space_is_quoted(self):
        self.assertEqual(encode([("msg", "hello world")]), 'msg="hello world"')

    def test_value_with_quote_is_escaped(self):
        self.assertEqual(encode([("a", 'say "hi"')]), 'a="say \\"hi\\""')

    def test_value_with_backslash_is_escaped(self):
        self.assertEqual(encode([("a", "x\\y")]), 'a="x\\\\y"')

    def test_value_with_equals_not_quoted(self):
        self.assertEqual(encode([("a", "b=c")]), "a=b=c")

    def test_empty_value_not_quoted(self):
        self.assertEqual(encode([("k", "")]), "k=")

    def test_value_with_control_char_is_quoted(self):
        self.assertEqual(encode([("a", "x\ny")]), 'a="x\ny"')
        self.assertEqual(encode([("a", "x\ty")]), 'a="x\ty"')

    def test_duplicate_keys_kept_in_order(self):
        self.assertEqual(encode([("a", "1"), ("a", "2")]), "a=1 a=2")

    def test_key_with_space_raises_with_position(self):
        with self.assertRaises(LogfmtError) as ctx:
            encode([("a b", "1")])
        self.assertEqual(ctx.exception.position, 1)

    def test_key_with_control_char_raises(self):
        with self.assertRaises(LogfmtError) as ctx:
            encode([("a\x01b", "1")])
        self.assertEqual(ctx.exception.position, 1)

    def test_key_with_equals_raises(self):
        with self.assertRaises(LogfmtError):
            encode([("a=b", "1")])

    def test_key_with_quote_raises(self):
        with self.assertRaises(LogfmtError):
            encode([('a"b', "1")])


class DecodeTest(unittest.TestCase):
    def test_simple_line(self):
        self.assertEqual(decode("a=1 b=2"), [("a", "1"), ("b", "2")])

    def test_bare_key(self):
        self.assertEqual(decode("flag"), [("flag", True)])

    def test_empty_line(self):
        self.assertEqual(decode(""), [])
        self.assertEqual(decode("   "), [])

    def test_value_with_equals(self):
        self.assertEqual(decode("a=b=c"), [("a", "b=c")])

    def test_empty_value(self):
        self.assertEqual(decode("key="), [("key", "")])

    def test_quoted_value_with_space(self):
        self.assertEqual(
            decode('msg="hello world" x=1'),
            [("msg", "hello world"), ("x", "1")],
        )

    def test_quoted_escapes(self):
        self.assertEqual(decode('a="x\\"y\\\\z"'), [("a", 'x"y\\z')])

    def test_quoted_empty_value(self):
        self.assertEqual(decode('a=""'), [("a", "")])

    def test_duplicate_keys_kept_in_order(self):
        self.assertEqual(decode("a=1 a=2 a=3"), [("a", "1"), ("a", "2"), ("a", "3")])

    def test_unterminated_quote_position(self):
        with self.assertRaises(LogfmtError) as ctx:
            decode('a="x')
        self.assertEqual(ctx.exception.position, 2)

    def test_unterminated_quote_after_escape_position(self):
        with self.assertRaises(LogfmtError) as ctx:
            decode('a="x\\')
        self.assertEqual(ctx.exception.position, 2)

    def test_illegal_escape_position(self):
        with self.assertRaises(LogfmtError) as ctx:
            decode('a="x\\y"')
        self.assertEqual(ctx.exception.position, 4)

    def test_control_char_in_key_position(self):
        with self.assertRaises(LogfmtError) as ctx:
            decode("a\x01b=1")
        self.assertEqual(ctx.exception.position, 1)

    def test_quote_in_key_position(self):
        with self.assertRaises(LogfmtError) as ctx:
            decode('a"b=1')
        self.assertEqual(ctx.exception.position, 1)

    def test_garbage_after_closing_quote(self):
        with self.assertRaises(LogfmtError) as ctx:
            decode('a="b"c')
        self.assertEqual(ctx.exception.position, 5)

    def test_error_type_exists(self):
        self.assertTrue(issubclass(LogfmtError, Exception))


class RoundTripTest(unittest.TestCase):
    CASES = [
        [],
        [("a", "1")],
        [("flag", True)],
        [("k", "")],
        [("msg", "hello world")],
        [("a", 'say "hi"')],
        [("a", "x\\y")],
        [("a", "b=c")],
        [("a", "\n\t\x00\x7f")],
        [("a", "1"), ("a", "2"), ("b", True), ("c", "")],
        [("path", "/tmp/a b/\"c\"\\d"), ("msg", "你好 世界")],
    ]

    def test_decode_encode_roundtrip(self):
        for pairs in self.CASES:
            with self.subTest(pairs=pairs):
                self.assertEqual(decode(encode(pairs)), pairs)

    def test_deterministic(self):
        for pairs in self.CASES:
            with self.subTest(pairs=pairs):
                self.assertEqual(encode(pairs), encode(pairs))
                line = encode(pairs)
                self.assertEqual(decode(line), decode(line))


class StreamTest(unittest.TestCase):
    def test_decode_stream_line_by_line(self):
        lines = ['a=1 msg="x y"', "b=2 flag", ""]
        self.assertEqual(
            list(decode_stream(iter(lines))),
            [[("a", "1"), ("msg", "x y")], [("b", "2"), ("flag", True)], []],
        )

    def test_encode_stream_roundtrip(self):
        rows = [[("a", "1"), ("m", "x y")], [("b", True)], []]
        lines = list(encode_stream(iter(rows)))
        self.assertEqual(list(decode_stream(iter(lines))), rows)

    def test_large_single_line_single_pass(self):
        pairs = [("k%d" % i, "v %d" % i) for i in range(100000)]
        line = encode(pairs)
        self.assertGreater(len(line), 1000000)
        self.assertEqual(decode(line), pairs)


if __name__ == "__main__":
    unittest.main()
