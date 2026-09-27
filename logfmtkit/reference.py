"""逐字符状态机参考实现，只用于对照测试。语义必须与 codec 完全一致。"""

from .codec import LogfmtError

_WS = frozenset(" \t\n\r\v\f")

# 状态机的状态
_BETWEEN, _KEY, _VALUE_START, _BARE_VALUE, _QUOTED, _ESCAPE, _AFTER_QUOTE = range(7)


def encode(pairs):
    """逐字符编码：先校验键，再按需加引号并逐字符转义。"""
    out = []
    for key, value in pairs:
        buf = []
        for offset, ch in enumerate(key):
            code = ord(ch)
            if ch in _WS or code < 0x20 or code == 0x7F:
                raise LogfmtError("键 %r 含空白或控制字符" % key, offset)
            if ch == '"' or ch == "=":
                raise LogfmtError("键 %r 含非法字符 %r" % (key, ch), offset)
            buf.append(ch)
        text = "".join(buf)
        if value is True:
            out.append(text)
            continue
        if not isinstance(value, str):
            value = str(value)
        need_quote = False
        escaped = []
        for ch in value:
            code = ord(ch)
            if ch in _WS or ch == '"' or ch == "\\" or code < 0x20 or code == 0x7F:
                need_quote = True
            if ch == "\\":
                escaped.append("\\\\")
            elif ch == '"':
                escaped.append('\\"')
            else:
                escaped.append(ch)
        if need_quote:
            out.append('%s="%s"' % (text, "".join(escaped)))
        else:
            out.append("%s=%s" % (text, value))
    return " ".join(out)


def decode(line):
    """逐字符状态机解码，一次一个字符。"""
    pairs = []
    state = _BETWEEN
    key = []
    value = []
    quote_at = -1
    i = 0
    n = len(line)
    while i < n:
        ch = line[i]
        if state == _BETWEEN:
            if ch in _WS:
                i += 1
            elif ch == "=":
                key = []
                state = _VALUE_START
                i += 1
            elif ch == '"':
                raise LogfmtError("键里不能有双引号", i)
            elif ord(ch) < 0x20 or ord(ch) == 0x7F:
                raise LogfmtError("键里不能有控制字符", i)
            else:
                key = [ch]
                state = _KEY
                i += 1
        elif state == _KEY:
            if ch in _WS:
                pairs.append(("".join(key), True))
                state = _BETWEEN
                i += 1
            elif ch == "=":
                state = _VALUE_START
                i += 1
            elif ch == '"':
                raise LogfmtError("键里不能有双引号", i)
            elif ord(ch) < 0x20 or ord(ch) == 0x7F:
                raise LogfmtError("键里不能有控制字符", i)
            else:
                key.append(ch)
                i += 1
        elif state == _VALUE_START:
            if ch in _WS:
                pairs.append(("".join(key), ""))
                state = _BETWEEN
                i += 1
            elif ch == '"':
                quote_at = i
                value = []
                state = _QUOTED
                i += 1
            else:
                value = [ch]
                state = _BARE_VALUE
                i += 1
        elif state == _BARE_VALUE:
            if ch in _WS:
                pairs.append(("".join(key), "".join(value)))
                state = _BETWEEN
                i += 1
            else:
                value.append(ch)
                i += 1
        elif state == _QUOTED:
            if ch == '"':
                state = _AFTER_QUOTE
                i += 1
            elif ch == "\\":
                state = _ESCAPE
                i += 1
            else:
                value.append(ch)
                i += 1
        elif state == _ESCAPE:
            if ch != '"' and ch != "\\":
                raise LogfmtError("非法转义 \\%s" % ch, i - 1)
            value.append(ch)
            state = _QUOTED
            i += 1
        else:  # _AFTER_QUOTE
            if ch in _WS:
                pairs.append(("".join(key), "".join(value)))
                state = _BETWEEN
                i += 1
            else:
                raise LogfmtError("引号后必须是空白或行尾", i)
    if state == _KEY:
        pairs.append(("".join(key), True))
    elif state == _VALUE_START:
        pairs.append(("".join(key), ""))
    elif state == _BARE_VALUE:
        pairs.append(("".join(key), "".join(value)))
    elif state == _QUOTED or state == _ESCAPE:
        raise LogfmtError("未闭合的引号", quote_at)
    elif state == _AFTER_QUOTE:
        pairs.append(("".join(key), "".join(value)))
    return pairs
