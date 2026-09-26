"""logfmt：key=value 序列。只用标准库。"""


class LogfmtError(Exception):
    """logfmt 不合法。缺陷：不带位置。"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


def encode(pairs):
    """编码。缺陷：值里有空格也不加引号，也不做转义。"""
    parts = []
    for key, value in pairs:
        if value is True:
            parts.append(key)
            continue
        parts.append("%s=%s" % (key, value))
    return " ".join(parts)


def decode(line):
    """解码。缺陷：按空白切分（引号里的空格会被切断），重复键直接覆盖。"""
    pairs = []
    for token in line.split():
        if "=" not in token:
            pairs.append((token, True))
            continue
        key, value = token.split("=", 1)
        pairs.append((key, value.strip('"')))
    return pairs
