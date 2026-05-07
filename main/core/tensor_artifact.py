"""
文件用途：提供 stage-one synthetic tensor artifact 的最小读写工具。
File purpose: Provide minimal IO helpers for stage-one synthetic tensor artifacts.
Module type: General module
"""

from __future__ import annotations

import ast
from array import array
from dataclasses import dataclass
from pathlib import Path
import struct
import sys


NPY_MAGIC_PREFIX = b"\x93NUMPY"
NPY_VERSION = (1, 0)
NPY_DTYPE_DESCRIPTOR = "<f4"


@dataclass(frozen=True)
class FloatTensorArtifact:
    """功能：定义 float32 tensor artifact 的内存表示。

    In-memory representation of a float32 tensor artifact.

    Args:
        shape: Tensor shape in row-major order.
        values: Flattened float32 payload.

    Returns:
        None.
    """

    shape: tuple[int, ...]
    values: array


def compute_numel(shape: tuple[int, ...]) -> int:
    """功能：计算受治理 tensor shape 的元素数量。

    Compute the number of elements for a governed tensor shape.

    Args:
        shape: Tensor shape.

    Returns:
        The product of the shape dimensions.
    """
    if not isinstance(shape, tuple) or not shape:
        raise TypeError("shape must be a non-empty tuple")
    numel = 1
    for dimension in shape:
        if not isinstance(dimension, int) or dimension < 1:
            raise ValueError("shape dimensions must be positive integers")
        numel *= dimension
    return numel


def write_float_tensor_npy(
    file_path: str | Path,
    shape: tuple[int, ...],
    values: list[float] | array,
) -> None:
    """功能：将 float32 tensor 写入 `.npy` artifact。

    Write a float32 tensor artifact in the `.npy` format.

    Args:
        file_path: Target artifact path.
        shape: Tensor shape.
        values: Flattened tensor values.

    Returns:
        None.
    """
    output_path = Path(file_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    expected_numel = compute_numel(shape)

    if isinstance(values, array):
        tensor_values = array("f", values)
    else:
        tensor_values = array("f", [float(value) for value in values])

    if len(tensor_values) != expected_numel:
        raise ValueError("tensor value count does not match shape")

    header_text = str(
        {
            "descr": NPY_DTYPE_DESCRIPTOR,
            "fortran_order": False,
            "shape": shape,
        }
    )
    header_bytes = _build_npy_header_bytes(header_text)
    if sys.byteorder != "little":
        # 中文注释：`.npy` 这里固定使用 little-endian float32 编码。
        tensor_values.byteswap()
    output_path.write_bytes(
        NPY_MAGIC_PREFIX
        + bytes(NPY_VERSION)
        + struct.pack("<H", len(header_bytes))
        + header_bytes
        + tensor_values.tobytes()
    )


def read_float_tensor_npy(file_path: str | Path) -> FloatTensorArtifact:
    """功能：从 `.npy` artifact 读取 float32 tensor。

    Read a float32 tensor artifact from the `.npy` format.

    Args:
        file_path: Source artifact path.

    Returns:
        A `FloatTensorArtifact` instance.
    """
    input_path = Path(file_path)
    payload = input_path.read_bytes()
    if len(payload) < 10 or payload[:6] != NPY_MAGIC_PREFIX:
        raise ValueError("unsupported npy artifact header")

    major, minor = payload[6], payload[7]
    if (major, minor) != NPY_VERSION:
        raise ValueError("unsupported npy artifact version")

    header_length = struct.unpack("<H", payload[8:10])[0]
    header_end = 10 + header_length
    header_text = payload[10:header_end].decode("latin1").strip()
    header = ast.literal_eval(header_text)
    if header.get("descr") != NPY_DTYPE_DESCRIPTOR:
        raise ValueError("unsupported npy dtype descriptor")
    if header.get("fortran_order") is not False:
        raise ValueError("fortran-order npy artifacts are not supported")

    shape = tuple(int(dimension) for dimension in header.get("shape", ()))
    expected_numel = compute_numel(shape)
    tensor_values = array("f")
    tensor_values.frombytes(payload[header_end:])
    if sys.byteorder != "little":
        tensor_values.byteswap()
    if len(tensor_values) != expected_numel:
        raise ValueError("npy payload size does not match declared shape")
    return FloatTensorArtifact(shape=shape, values=tensor_values)


def _build_npy_header_bytes(header_text: str) -> bytes:
    encoded = header_text.encode("latin1")
    base_length = len(NPY_MAGIC_PREFIX) + 2 + 2
    padded_length = len(encoded) + 1
    padding = (16 - ((base_length + padded_length) % 16)) % 16
    return encoded + (b" " * padding) + b"\n"