"""主实现（logfmtkit.codec）与逐字符状态机参考实现（logfmtkit.reference）对照。

对样例与随机生成的 1 万组键值对逐字节比对编码结果与解码结果，
并对非法输入比对错误位置。
"""

import random
import unittest

from logfmtkit import codec, reference
from logfmtkit.codec import LogfmtError

SAMPLE_LINES = [
    "",
    "   ",
    "a=1",
    "a=1 b=2",
    "flag",
    "flag x=1 other",
    "key=",
    "key= next=1",
    "a=b=c",
    "a==",
    "msg=hello world",
    'msg="hello world" x=1',
    'a=""',
    'a="b=c"',
    'a="say \\"hi\\""',
    'a="x\\\\y"',
    'a="\\"\\""',
    "a=1 a=2 a=3",
    "a=1\tb=2",
    "  padded=1  ",
    "k=中文值",
    'a="unclosed',
    'x=1 msg="hello',
    'a="x\\',
    'a="x\\qy"',
    'a="\\n"',
    'a="x"y',
    "a\x01=1",
    'a"b=1',
    "=v",
    "a=1 =v",
]

SAMPLE_PAIRS = [
    [],
    [("a", "1")],
    [("a", "1"), ("b", "2")],
    [("flag", True)],
    [("key", "")],
    [("msg", "hello world")],
    [("a", 'say "hi"')],
    [("a", "x\\y")],
    [("a", '\\"')],
    [("a", "b=c")],
    [("a", "1"), ("a", "2")],
    [("k", "tab\there"), ("u", "中文值")],
]

KEY_ALPHABET = "abcxyz019_./\\-é中"
VALUE_ALPHABET = "ab1 \t\"\\=_-é中\x01\x1f\n"


def random_key(rng):
    return "".join(rng.choice(KEY_ALPHABET) for _ in range(rng.randint(1, 8)))


def random_value(rng):
    return "".join(rng.choice(VALUE_ALPHABET) for _ in range(rng.randint(0, 12)))


def random_pairs(rng):
    pairs = []
    for _ in range(rng.randint(1, 5)):
        if rng.random() < 0.15:
            pairs.append((random_key(rng), True))
        else:
            pairs.append((random_key(rng), random_value(rng)))
    return pairs


def decode_outcome(module, line):
    """返回 ("ok", pairs) 或 ("error", position, message)，便于两实现比对。"""
    try:
        return ("ok", module.decode(line))
    except LogfmtError as error:
        return ("error", error.position, str(error))


class SampleCompareTest(unittest.TestCase):
    def test_sample_lines_decode_identical(self):
        for line in SAMPLE_LINES:
            with self.subTest(line=line):
                self.assertEqual(
                    decode_outcome(codec, line), decode_outcome(reference, line)
                )

    def test_sample_pairs_encode_identical_and_roundtrip(self):
        for pairs in SAMPLE_PAIRS:
            with self.subTest(pairs=pairs):
                encoded_main = codec.encode(pairs)
                self.assertEqual(encoded_main, reference.encode(pairs))
                self.assertEqual(codec.decode(encoded_main), pairs)
                self.assertEqual(reference.decode(encoded_main), pairs)


class RandomCompareTest(unittest.TestCase):
    def test_random_pairs_encode_decode_identical(self):
        rng = random.Random(0xC0DE)
        for _ in range(10000):
            pairs = random_pairs(rng)
            encoded_main = codec.encode(pairs)
            encoded_ref = reference.encode(pairs)
            self.assertEqual(encoded_main, encoded_ref)
            self.assertEqual(codec.decode(encoded_main), pairs)
            self.assertEqual(reference.decode(encoded_main), pairs)

    def test_random_lines_decode_and_error_positions_identical(self):
        rng = random.Random(0xBAD)
        alphabet = "ab= \"\\c\td\x01é"
        for _ in range(20000):
            line = "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 24)))
            self.assertEqual(
                decode_outcome(codec, line),
                decode_outcome(reference, line),
                msg="line=%r" % line,
            )

    def test_random_invalid_keys_both_reject(self):
        rng = random.Random(0xE11)
        bad = ["a b", "a=b", "a\x00b", 'a"b', "", "a\tb"]
        for _ in range(2000):
            key = rng.choice(bad)
            value = random_value(rng)
            for module in (codec, reference):
                with self.assertRaises(LogfmtError):
                    module.encode([(key, value)])


if __name__ == "__main__":
    unittest.main()
