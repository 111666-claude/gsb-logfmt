import contextlib
import io
import unittest

from logfmtkit.cli import main


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class CliTest(unittest.TestCase):
    def test_encode_quotes_value_with_space(self):
        code, out, _ = run(["--encode", "msg=hello world"])
        self.assertEqual(code, 0)
        self.assertEqual(out, 'msg="hello world"\n')

    def test_encode_bare_key(self):
        code, out, _ = run(["--encode", "flag"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "flag\n")

    def test_encode_repeated(self):
        code, out, _ = run(["--encode", "a=1", "--encode", "a=2"])
        self.assertEqual(code, 0)
        self.assertEqual(out, "a=1 a=2\n")

    def test_decode_quote_aware(self):
        code, out, _ = run(["--decode", 'msg="hello world" x=1'])
        self.assertEqual(code, 0)
        self.assertEqual(out, '[["msg", "hello world"], ["x", "1"]]\n')

    def test_decode_duplicate_keys_kept(self):
        code, out, _ = run(["--decode", "a=1 a=2"])
        self.assertEqual(code, 0)
        self.assertEqual(out, '[["a", "1"], ["a", "2"]]\n')

    def test_decode_flatten_takes_last(self):
        code, out, _ = run(["--decode", "a=1 a=2", "--flatten"])
        self.assertEqual(code, 0)
        self.assertEqual(out, '{"a": "2"}\n')

    def test_decode_error_reports_position(self):
        code, _, err = run(["--decode", 'a="x'])
        self.assertEqual(code, 1)
        self.assertIn("位置 2", err)

    def test_no_args(self):
        code, _, err = run([])
        self.assertEqual(code, 2)
        self.assertIn("错误", err)


if __name__ == "__main__":
    unittest.main()
