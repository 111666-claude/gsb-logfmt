"""logfmt：key=value 序列、引号与转义、裸键。只用标准库。

口径：
- 值里有空白、双引号、反斜杠或控制字符时必须加引号，内部 " 与 \\ 写成 \\" 与 \\\\；
- 没有 = 的 token 是裸键，值为 True；key= 的值是空串；值里的 = 属于值；
- 重复键按出现顺序全部保留；
- 未闭合引号、非法转义、键里含空白/控制字符都要报错并给出字符位置（从 0 计）；
- 单遍扫描，内存 O(一行)。
"""

_WHITESPACE = frozenset(" \t\n\r\v\f")
_QUOTE = '"'
_BACKSLASH = "\\"


class LogfmtError(Exception):
    """logfmt 不合法。position 是出错的字符下标（从 0 计），可能为 None。"""

    def __init__(self, message, position=None):
        self.position = position
        if position is not None:
            message = "%s（位置 %d）" % (message, position)
        super().__init__(message)
        self.message = message


def _is_control(ch):
    return ord(ch) < 0x20 or ord(ch) == 0x7F


def _validate_key(key):
    for offset, ch in enumerate(key):
        if ch in _WHITESPACE or _is_control(ch):
            raise LogfmtError("键 %r 含空白或控制字符" % key, offset)
        if ch == _QUOTE or ch == "=":
            raise LogfmtError("键 %r 含非法字符 %r" % (key, ch), offset)


def _needs_quote(value):
    for ch in value:
        if ch in _WHITESPACE or ch == _QUOTE or ch == _BACKSLASH or _is_control(ch):
            return True
    return False


def _escape(value):
    return value.replace(_BACKSLASH, _BACKSLASH * 2).replace(_QUOTE, _BACKSLASH + _QUOTE)


def encode(pairs):
    """把键值对编成一行 logfmt。值为 True 时是裸键，只写键名。"""
    parts = []
    for key, value in pairs:
        _validate_key(key)
        if value is True:
            parts.append(key)
            continue
        if not isinstance(value, str):
            value = str(value)
        if _needs_quote(value):
            parts.append('%s="%s"' % (key, _escape(value)))
        else:
            parts.append("%s=%s" % (key, value))
    return " ".join(parts)


def decode(line):
    """把一行 logfmt 解成键值对列表，重复键按出现顺序保留。"""
    pairs = []
    n = len(line)
    i = 0
    ws = _WHITESPACE
    while True:
        while i < n and line[i] in ws:
            i += 1
        if i >= n:
            return pairs
        start = i
        while i < n and line[i] not in ws and line[i] != "=":
            ch = line[i]
            if ch == _QUOTE:
                raise LogfmtError("键里不能有双引号", i)
            if _is_control(ch):
                raise LogfmtError("键里不能有控制字符", i)
            i += 1
        key = line[start:i]
        if i >= n or line[i] in ws:
            pairs.append((key, True))
            continue
        i += 1  # 跳过 =
        if i < n and line[i] == _QUOTE:
            quote_at = i
            i += 1
            buf = []
            closed = False
            while i < n:
                ch = line[i]
                if ch == _QUOTE:
                    closed = True
                    i += 1
                    break
                if ch == _BACKSLASH:
                    if i + 1 >= n:
                        break
                    nxt = line[i + 1]
                    if nxt != _QUOTE and nxt != _BACKSLASH:
                        raise LogfmtError("非法转义 \\%s" % nxt, i)
                    buf.append(nxt)
                    i += 2
                else:
                    buf.append(ch)
                    i += 1
            if not closed:
                raise LogfmtError("未闭合的引号", quote_at)
            if i < n and line[i] not in ws:
                raise LogfmtError("引号后必须是空白或行尾", i)
            pairs.append((key, "".join(buf)))
        else:
            start = i
            while i < n and line[i] not in ws:
                i += 1
            pairs.append((key, line[start:i]))


def decode_stream(lines):
    """逐行解码，单遍流式，内存 O(一行)。"""
    for line in lines:
        yield decode(line)


def encode_stream(rows):
    """逐行编码，单遍流式。"""
    for pairs in rows:
        yield encode(pairs)
