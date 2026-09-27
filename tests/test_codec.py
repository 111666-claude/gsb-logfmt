import io
import json
import unittest
from contextlib import redirect_stderr, redirect_stdout

from logfmtkit.cli import main as cli_main
from logfmtkit.codec import (
    LogfmtError,
    decode,
    decode_lines,
    encode,
    encode_lines,
)


class EncodeTest(unittest.TestCase):
    def test_simple_pair(self):
        self.assertEqual(encode([("a", "1")]), "a=1")

    def test_two_pairs(self):
        self.assertEqual(encode([("a", "1"), ("b", "2")]), "a=1 b=2")

    def test_bare_key(self):
        self.assertEqual(encode([("flag", True)]), "flag")

    def test_empty(self):
        self.assertEqual(encode([]), "")

    def test_empty_value(self):
        self.assertEqual(encode([("key", "")]), "key=")

    def test_value_with_space_is_quoted(self):
        self.assertEqual(encode([("msg", "hello world")]), 'msg="hello world"')

    def test_value_with_tab_is_quoted(self):
        self.assertEqual(encode([("a", "x\ty")]), 'a="x\ty"')

    def test_quote_and_backslash_are_escaped(self):
        self.assertEqual(encode([("a", 'say "hi"')]), 'a="say \\"hi\\""')
        self.assertEqual(encode([("a", "x\\y")]), 'a="x\\\\y"')
        self.assertEqual(encode([("a", '\\"')]), 'a="\\\\\\""')

    def test_value_with_equals_is_quoted(self):
        self.assertEqual(encode([("a", "b=c")]), 'a="b=c"')

    def test_value_with_control_char_is_quoted(self):
        self.assertEqual(encode([("a", "x\x01y")]), 'a="x\x01y"')

    def test_duplicate_keys_kept_in_order(self):
        self.assertEqual(encode([("a", "1"), ("a", "2"), ("a", "3")]), "a=1 a=2 a=3")

    def test_key_with_space_rejected(self):
        with self.assertRaises(LogfmtError):
            encode([("a b", "1")])

    def test_key_with_equals_rejected(self):
        with self.assertRaises(LogfmtError):
            encode([("a=b", "1")])

    def test_key_with_control_char_rejected(self):
        with self.assertRaises(LogfmtError):
            encode([("a\x00b", "1")])

    def test_empty_key_rejected(self):
        with self.assertRaises(LogfmtError):
            encode([("", "1")])


class DecodeTest(unittest.TestCase):
    def test_simple_line(self):
        self.assertEqual(decode("a=1 b=2"), [("a", "1"), ("b", "2")])

    def test_bare_key(self):
        self.assertEqual(decode("flag"), [("flag", True)])

    def test_empty_line(self):
        self.assertEqual(decode(""), [])

    def test_blank_line(self):
        self.assertEqual(decode("   \t "), [])

    def test_trailing_newline_tolerated(self):
        self.assertEqual(decode("a=1\n"), [("a", "1")])
        self.assertEqual(decode("a=1\r\n"), [("a", "1")])

    def test_quoted_value_with_space(self):
        self.assertEqual(
            decode('msg="hello world" x=1'),
            [("msg", "hello world"), ("x", "1")],
        )

    def test_quoted_escapes(self):
        self.assertEqual(decode('a="say \\"hi\\""'), [("a", 'say "hi"')])
        self.assertEqual(decode('a="x\\\\y"'), [("a", "x\\y")])

    def test_quoted_empty_value(self):
        self.assertEqual(decode('a=""'), [("a", "")])

    def test_empty_value(self):
        self.assertEqual(decode("key="), [("key", "")])
        self.assertEqual(decode("key= next=1"), [("key", ""), ("next", "1")])

    def test_value_with_equals(self):
        self.assertEqual(decode("a=b=c"), [("a", "b=c")])

    def test_quoted_value_with_equals(self):
        self.assertEqual(decode('a="b=c"'), [("a", "b=c")])

    def test_duplicate_keys_kept_in_order(self):
        self.assertEqual(
            decode("a=1 a=2 a=3"), [("a", "1"), ("a", "2"), ("a", "3")]
        )

    def test_mixed_bare_and_valued(self):
        self.assertEqual(
            decode("flag x=1 other"), [("flag", True), ("x", "1"), ("other", True)]
        )

    def test_tab_separator(self):
        self.assertEqual(decode("a=1\tb=2"), [("a", "1"), ("b", "2")])


class DecodeErrorTest(unittest.TestCase):
    def assert_error_at(self, line, position):
        with self.assertRaises(LogfmtError) as caught:
            decode(line)
        self.assertEqual(caught.exception.position, position)
        self.assertIn(str(position), str(caught.exception))

    def test_unclosed_quote(self):
        self.assert_error_at('a="unclosed', 2)

    def test_unclosed_quote_after_pairs(self):
        self.assert_error_at('x=1 msg="hello', 8)

    def test_unclosed_quote_trailing_backslash(self):
        self.assert_error_at('a="x\\', 2)

    def test_illegal_escape(self):
        self.assert_error_at('a="x\\qy"', 4)

    def test_illegal_escape_at_start(self):
        self.assert_error_at('a="\\n"', 3)

    def test_garbage_after_closing_quote(self):
        self.assert_error_at('a="x"y', 5)

    def test_key_with_control_char(self):
        self.assert_error_at("a\x01=1", 1)

    def test_key_with_quote(self):
        self.assert_error_at('a"b=1', 1)

    def test_empty_key(self):
        self.assert_error_at("=v", 0)


class InvariantTest(unittest.TestCase):
    CASES = [
        [],
        [("a", "1")],
        [("flag", True)],
        [("key", "")],
        [("msg", "hello world")],
        [("a", 'quote " inside')],
        [("a", "back\\slash")],
        [("a", 'mix "\\" ed')],
        [("a", "b=c")],
        [("a", "=leading"), ("b", "trailing=")],
        [("a", "1"), ("a", "2"), ("a", "3")],
        [("k", "tab\there"), ("u", "中文值"), ("e", "é")],
        [("x", True), ("x", ""), ("x", " ")],
    ]

    def test_roundtrip(self):
        for pairs in self.CASES:
            with self.subTest(pairs=pairs):
                self.assertEqual(decode(encode(pairs)), pairs)

    def test_deterministic(self):
        for pairs in self.CASES:
            with self.subTest(pairs=pairs):
                first = encode(pairs)
                self.assertEqual(encode(pairs), first)
                self.assertEqual(decode(first), decode(first))


class StreamingTest(unittest.TestCase):
    def test_decode_lines_is_lazy(self):
        produced = []

        def infinite():
            n = 0
            while True:
                n += 1
                produced.append(n)
                yield "k%d=v%d" % (n, n)

        stream = decode_lines(infinite())
        self.assertEqual(produced, [])
        self.assertEqual(next(stream), [("k1", "v1")])
        self.assertEqual(next(stream), [("k2", "v2")])
        self.assertEqual(produced, [1, 2])

    def test_encode_lines_writes_incrementally(self):
        writes = []

        class Out:
            def write(self, text):
                writes.append(text)

        def groups():
            yield [("a", "1")]
            yield [("b", "x y")]

        encode_lines(groups(), Out())
        self.assertEqual("".join(writes), 'a=1\nb="x y"\n')

    def test_stream_roundtrip_volume(self):
        groups = [
            [("i", str(i)), ("msg", "hello world %d" % i), ("flag", True)]
            for i in range(20000)
        ]
        out = io.StringIO()
        encode_lines(iter(groups), out)
        out.seek(0)
        decoded = list(decode_lines(out))
        self.assertEqual(decoded, groups)


class CliTest(unittest.TestCase):
    def run_cli(self, argv):
        out = io.StringIO()
        err = io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli_main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_encode_quotes_value_with_space(self):
        code, out, _ = self.run_cli(["--encode", "msg=hello world"])
        self.assertEqual(code, 0)
        self.assertEqual(out, 'msg="hello world"\n')

    def test_encode_repeated_and_bare(self):
        code, out, _ = self.run_cli(
            ["--encode", "a=1", "--encode", "flag", "--encode", "a=2"]
        )
        self.assertEqual(code, 0)
        self.assertEqual(out, "a=1 flag a=2\n")

    def test_decode_quote_aware(self):
        code, out, _ = self.run_cli(["--decode", 'msg="hello world" x=1'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [["msg", "hello world"], ["x", "1"]])

    def test_decode_keeps_duplicate_keys(self):
        code, out, _ = self.run_cli(["--decode", "a=1 a=2"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [["a", "1"], ["a", "2"]])

    def test_decode_flatten_takes_last(self):
        code, out, _ = self.run_cli(["--decode", "a=1 a=2", "--flatten"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"a": "2"})

    def test_decode_error_reports_position(self):
        code, _, err = self.run_cli(["--decode", 'msg="hello'])
        self.assertEqual(code, 1)
        self.assertIn("4", err)

    def test_no_args(self):
        code, _, err = self.run_cli([])
        self.assertEqual(code, 2)
        self.assertIn("错误", err)


if __name__ == "__main__":
    unittest.main()
