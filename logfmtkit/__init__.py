"""logfmt 编解码。"""

from .codec import LogfmtError, decode, decode_stream, encode, encode_stream

__all__ = ["LogfmtError", "decode", "decode_stream", "encode", "encode_stream"]
