"""参考实现：逐字符状态机。结构与 codec.py 不同，用于对照测试。

口径与 codec.py 完全一致（同样的错误、同样的 0 起始位置）。
"""

from .codec import LogfmtError

_BETWEEN = 0      # token 之间（跳过分隔符）
_KEY = 1          # 读键中
_AFTER_EQ = 2     # 刚读到 "="，决定值是引号串还是裸串
_UNQUOTED = 3     # 读裸值中
_QUOTED = 4       # 读引号值中
_ESCAPE = 5       # 引号值里刚读到反斜杠
_AFTER_QUOTE = 6  # 引号值刚闭合，只接受分隔符或行尾


def _check_key_char(ch, pos):
    if ch.isspace() or ch == '"' or ord(ch) < 0x20 or ord(ch) == 0x7F:
        raise LogfmtError("键含非法字符 %r（位置 %d）" % (ch, pos), position=pos)


def decode(line):
    if line.endswith("\n"):
        line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
    pairs = []
    state = _BETWEEN
    key_chars = []
    value_chars = []
    key_start = -1
    quote_pos = -1
    for pos, ch in enumerate(line):
        if state == _BETWEEN:
            if ch == " " or ch == "\t":
                continue
            key_start = pos
            if ch == "=":
                raise LogfmtError("空键（位置 %d）" % key_start, position=key_start)
            _check_key_char(ch, pos)
            key_chars = [ch]
            state = _KEY
        elif state == _KEY:
            if ch == " " or ch == "\t":
                pairs.append(("".join(key_chars), True))
                state = _BETWEEN
            elif ch == "=":
                state = _AFTER_EQ
            else:
                _check_key_char(ch, pos)
                key_chars.append(ch)
        elif state == _AFTER_EQ:
            if ch == '"':
                quote_pos = pos
                value_chars = []
                state = _QUOTED
            elif ch == " " or ch == "\t":
                pairs.append(("".join(key_chars), ""))
                state = _BETWEEN
            else:
                value_chars = [ch]
                state = _UNQUOTED
        elif state == _UNQUOTED:
            if ch == " " or ch == "\t":
                pairs.append(("".join(key_chars), "".join(value_chars)))
                state = _BETWEEN
            else:
                value_chars.append(ch)
        elif state == _QUOTED:
            if ch == '"':
                state = _AFTER_QUOTE
            elif ch == "\\":
                state = _ESCAPE
            else:
                value_chars.append(ch)
        elif state == _ESCAPE:
            if ch == '"' or ch == "\\":
                value_chars.append(ch)
                state = _QUOTED
            else:
                raise LogfmtError(
                    "非法转义 \\%s（位置 %d）" % (ch, pos - 1), position=pos - 1
                )
        else:  # _AFTER_QUOTE
            if ch == " " or ch == "\t":
                pairs.append(("".join(key_chars), "".join(value_chars)))
                state = _BETWEEN
            else:
                raise LogfmtError("引号后缺少分隔符（位置 %d）" % pos, position=pos)
    if state == _KEY:
        pairs.append(("".join(key_chars), True))
    elif state == _AFTER_EQ:
        pairs.append(("".join(key_chars), ""))
    elif state == _UNQUOTED:
        pairs.append(("".join(key_chars), "".join(value_chars)))
    elif state == _QUOTED or state == _ESCAPE:
        raise LogfmtError("未闭合的引号（起始位置 %d）" % quote_pos, position=quote_pos)
    elif state == _AFTER_QUOTE:
        pairs.append(("".join(key_chars), "".join(value_chars)))
    return pairs


def encode(pairs):
    parts = []
    for key, value in pairs:
        if not isinstance(key, str):
            raise TypeError("键必须是 str，得到 %r" % type(key).__name__)
        if not key:
            raise LogfmtError("键不能为空", position=0)
        for index, ch in enumerate(key):
            if ch.isspace() or ch in '"=' or ord(ch) < 0x20 or ord(ch) == 0x7F:
                raise LogfmtError(
                    "键 %r 含非法字符 %r（键内位置 %d）" % (key, ch, index),
                    position=index,
                )
        if value is True:
            parts.append(key)
            continue
        if not isinstance(value, str):
            raise TypeError("值必须是 str 或 True，得到 %r" % type(value).__name__)
        needs_quote = False
        for ch in value:
            if ch.isspace() or ch in '"\\=' or ord(ch) < 0x20 or ord(ch) == 0x7F:
                needs_quote = True
                break
        if not needs_quote:
            parts.append(key + "=" + value)
            continue
        buf = [key, '="']
        for ch in value:
            if ch == '"' or ch == "\\":
                buf.append("\\")
            buf.append(ch)
        buf.append('"')
        parts.append("".join(buf))
    return " ".join(parts)
