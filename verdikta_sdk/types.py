"""Shared type aliases used by the Verdikta SDK."""

from pathlib import Path
from typing import BinaryIO, Tuple, Union

FileInput = Union[
    str,
    Path,
    Tuple[str, BinaryIO],
    Tuple[str, BinaryIO, str],
]
