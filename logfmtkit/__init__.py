"""logfmt 编解码。"""

from .codec import LogfmtError, decode, decode_lines, encode, encode_lines

__all__ = ["LogfmtError", "decode", "decode_lines", "encode", "encode_lines"]
