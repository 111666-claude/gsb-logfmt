"""命令行入口：编解码 logfmt。"""

import argparse
import json
import sys

from .codec import LogfmtError, decode, encode


def build_parser():
    parser = argparse.ArgumentParser(prog="logfmt", description="logfmt 编解码")
    parser.add_argument("--encode", action="append", default=[], help="key=value，可重复")
    parser.add_argument("--decode", help="要解码的 logfmt 行")
    parser.add_argument("--flatten", action="store_true", help="重复键按最后一次取值（对照用）")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.encode:
            pairs = []
            for item in args.encode:
                if "=" not in item:
                    pairs.append((item, True))
                    continue
                key, value = item.split("=", 1)
                pairs.append((key, value))
            print(encode(pairs))
            return 0
        if args.decode is not None:
            pairs = decode(args.decode)
            if args.flatten:
                print(json.dumps(dict(pairs), ensure_ascii=False))
            else:
                print(json.dumps(pairs, ensure_ascii=False))
            return 0
    except LogfmtError as error:
        print("错误：%s" % error, file=sys.stderr)
        return 1
    print("错误：需要 --encode 或 --decode", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
