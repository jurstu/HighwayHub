"""An original camera JPEG plus its negotiated dimensions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class JpegFrame:
    data: bytes
    width: int
    height: int
