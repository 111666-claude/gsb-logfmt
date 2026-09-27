"""logfmt：key=value 序列的编解码与转义。只用标准库。

口径：
- 值里有空白、双引号、反斜杠、等号或控制字符时，编码必须加引号；
  引号内部的 " 与 \\ 分别写成 \\" 与 \\\\。
- 裸键（值为 True）只写键名；key= 的值是空串；值里的 = 属于值。
- 重复键按出现顺序全部保留。
- 错误都带 0 起始的字符位置（LogfmtError.position）。
"""

_ASCII_DEL = 0x7F


class LogfmtError(Exception):
    """logfmt 不合法。position 是 0 起始的字符位置，无位置信息时为 None。"""

    def __init__(self, message, position=None):
        super().__init__(message)
        self.message = message
        self.position = position


def _is_separator(ch):
    return ch == " " or ch == "\t"


def _is_control(ch):
    return ord(ch) < 0x20 or ord(ch) == _ASCII_DEL


def _check_key(key):
    """编码侧的键校验：空白、双引号、等号、控制字符都非法。"""
    for index, ch in enumerate(key):
        if ch.isspace() or ch in '"=' or _is_control(ch):
            raise LogfmtError(
                "键 %r 含非法字符 %r（键内位置 %d）" % (key, ch, index),
                position=index,
            )


def _needs_quote(value):
    for ch in value:
        if ch.isspace() or ch in '"\\=' or _is_control(ch):
            return True
    return False


def encode(pairs):
    """把 [(key, value), ...] 编成一行 logfmt。value 为 True 时是裸键。"""
    parts = []
    append = parts.append
    for key, value in pairs:
        if not isinstance(key, str):
            raise TypeError("键必须是 str，得到 %r" % type(key).__name__)
        if not key:
            raise LogfmtError("键不能为空", position=0)
        _check_key(key)
        if value is True:
            append(key)
            continue
        if not isinstance(value, str):
            raise TypeError("值必须是 str 或 True，得到 %r" % type(value).__name__)
        if _needs_quote(value):
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            append('%s="%s"' % (key, escaped))
        else:
            append("%s=%s" % (key, value))
    return " ".join(parts)


def decode(line):
    """把一行 logfmt 解成 [(key, value), ...]，重复键全部保留。"""
    if line.endswith("\n"):
        line = line[:-1]
        if line.endswith("\r"):
            line = line[:-1]
    pairs = []
    n = len(line)
    i = 0
    while True:
        while i < n and _is_separator(line[i]):
            i += 1
        if i >= n:
            return pairs
        key_start = i
        while i < n and not _is_separator(line[i]) and line[i] != "=":
            i += 1
        key = line[key_start:i]
        if not key:
            raise LogfmtError("空键（位置 %d）" % key_start, position=key_start)
        for offset, ch in enumerate(key):
            if ch.isspace() or ch == '"' or _is_control(ch):
                raise LogfmtError(
                    "键含非法字符 %r（位置 %d）" % (ch, key_start + offset),
                    position=key_start + offset,
                )
        if i >= n or _is_separator(line[i]):
            pairs.append((key, True))
            continue
        i += 1  # 跳过 "="
        if i < n and line[i] == '"':
            quote_pos = i
            i += 1
            chars = []
            while True:
                if i >= n:
                    raise LogfmtError(
                        "未闭合的引号（起始位置 %d）" % quote_pos, position=quote_pos
                    )
                ch = line[i]
                if ch == '"':
                    i += 1
                    break
                if ch == "\\":
                    if i + 1 >= n:
                        raise LogfmtError(
                            "未闭合的引号（起始位置 %d）" % quote_pos,
                            position=quote_pos,
                        )
                    nxt = line[i + 1]
                    if nxt != '"' and nxt != "\\":
                        raise LogfmtError(
                            "非法转义 \\%s（位置 %d）" % (nxt, i), position=i
                        )
                    chars.append(nxt)
                    i += 2
                else:
                    chars.append(ch)
                    i += 1
            if i < n and not _is_separator(line[i]):
                raise LogfmtError("引号后缺少分隔符（位置 %d）" % i, position=i)
            pairs.append((key, "".join(chars)))
        else:
            value_start = i
            while i < n and not _is_separator(line[i]):
                i += 1
            pairs.append((key, line[value_start:i]))


def encode_lines(groups, out):
    """流式编码：groups 是“每行一组键值对”的可迭代对象，逐行写出。

    单遍、内存 O(一行)，不把整份输入读进内存。
    """
    for pairs in groups:
        out.write(encode(pairs))
        out.write("\n")


def decode_lines(lines):
    """流式解码：lines 是逐行可迭代对象（如文件），逐行产出键值对列表。"""
    for line in lines:
        yield decode(line)
