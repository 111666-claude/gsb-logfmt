"""codec 与逐字符状态机参考实现的逐字节对照测试。"""

import random
import unittest

from logfmtkit import codec, reference
from logfmtkit.codec import LogfmtError

_KEY_CHARS = "abcXYZ019_-./:\\"
_VALUE_CHARS = "ab =\"\\\n\t\x00\x7f你🎉"


def _random_pairs(rng):
    pairs = []
    for _ in range(rng.randrange(7)):
        key = "".join(rng.choice(_KEY_CHARS) for _ in range(rng.randrange(1, 8)))
        if rng.randrange(5) == 0:
            pairs.append((key, True))
            continue
        value = "".join(rng.choice(_VALUE_CHARS) for _ in range(rng.randrange(0, 12)))
        pairs.append((key, value))
    return pairs


def _outcome(func, *args):
    try:
        return ("ok", func(*args))
    except LogfmtError as error:
        return ("err", str(error), error.position)


class DifferentialTest(unittest.TestCase):
    def test_random_pairs_roundtrip_and_match_reference(self):
        rng = random.Random(20260928)
        for case in range(10000):
            pairs = _random_pairs(rng)
            with self.subTest(case=case, pairs=pairs):
                encoded = codec.encode(pairs)
                # 编码结果逐字节一致
                self.assertEqual(encoded, reference.encode(pairs))
                # 不变量：decode(encode(pairs)) == pairs
                self.assertEqual(codec.decode(encoded), pairs)
                # 解码结果与参考实现一致
                self.assertEqual(reference.decode(encoded), pairs)

    def test_random_mutations_match_reference_including_error_positions(self):
        rng = random.Random(20260929)
        for case in range(3000):
            line = codec.encode(_random_pairs(rng))
            for _ in range(rng.randrange(1, 4)):
                if not line:
                    break
                pos = rng.randrange(len(line) + 1)
                if rng.randrange(2) == 0 and pos < len(line):
                    line = line[:pos] + line[pos + 1:]  # 删一个字符
                else:
                    line = line[:pos] + rng.choice('"\\x= \x01') + line[pos:]
            with self.subTest(case=case, line=line):
                self.assertEqual(
                    _outcome(codec.decode, line),
                    _outcome(reference.decode, line),
                )

    def test_spec_examples_match_reference(self):
        lines = [
            "",
            "   ",
            "a=1 b=2",
            "flag",
            "key=",
            "a=b=c",
            'msg="hello world" x=1',
            'a="x\\"y\\\\z"',
            "a=1 a=2 a=3",
            'a="x',
            'a="x\\',
            'a="x\\y"',
            "a\x01b=1",
            'a"b=1',
            'a="b"c',
            "=",
            "=v",
        ]
        for line in lines:
            with self.subTest(line=line):
                self.assertEqual(
                    _outcome(codec.decode, line),
                    _outcome(reference.decode, line),
                )


if __name__ == "__main__":
    unittest.main()
