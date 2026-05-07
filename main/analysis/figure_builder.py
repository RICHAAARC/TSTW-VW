"""
文件用途：生成 stage-one sync peak example figure。
File purpose: Generate the stage-one sync peak example figure artifact.
Module type: General module
"""

from __future__ import annotations

import binascii
from pathlib import Path
import struct
from typing import Any
import zlib

from main.core.records import build_output_paths


FIGURE_WIDTH = 640
FIGURE_HEIGHT = 360
BACKGROUND_COLOR = (248, 250, 252)
AXIS_COLOR = (51, 65, 85)
RANK_BAR_COLOR = (37, 99, 235)
ERROR_BAR_COLOR = (234, 88, 12)
GRID_COLOR = (203, 213, 225)


class FigureBuilder:
    """功能：构建 stage-one figure 产物。

    Builder for governed stage-one figure artifacts.

    Args:
        None.

    Returns:
        None.
    """

    def build_figures(
        self,
        event_score_records: list[dict[str, Any]],
        threshold_records: list[dict[str, Any]],
        output_root: str | Path,
    ) -> dict[str, Path]:
        """功能：从 governed records 构建 sync peak examples figure。

        Build the sync peak example figure from governed records.

        Args:
            event_score_records: Event score record list.
            threshold_records: Threshold record list.
            output_root: Run root path.

        Returns:
            A dictionary containing the written figure path.
        """
        if not isinstance(event_score_records, list):
            raise TypeError("event_score_records must be a list")
        if not isinstance(threshold_records, list):
            raise TypeError("threshold_records must be a list")
        del threshold_records

        output_paths = build_output_paths(output_root)
        output_paths.sync_peak_examples_path.parent.mkdir(parents=True, exist_ok=True)
        examples = _collect_sync_peak_examples(event_score_records)
        pixels = _build_sync_peak_canvas(examples)
        _write_rgb_png(
            output_paths.sync_peak_examples_path,
            FIGURE_WIDTH,
            FIGURE_HEIGHT,
            pixels,
        )
        return {"sync_peak_examples_path": output_paths.sync_peak_examples_path}


def _collect_sync_peak_examples(
    event_score_records: list[dict[str, Any]],
) -> list[dict[str, float | str]]:
    if not isinstance(event_score_records, list):
        raise TypeError("event_score_records must be a list")
    grouped_examples: dict[str, list[dict[str, float]]] = {}
    for event_score_record in event_score_records:
        mechanism_trace = event_score_record.get("mechanism_trace", {})
        if event_score_record.get("method_variant") != "tubelet_sync":
            continue
        if event_score_record.get("split") != "test":
            continue
        if event_score_record.get("sample_role") != "attacked_positive":
            continue
        if mechanism_trace.get("sync_peak_rank") is None:
            continue
        attack_name = str(event_score_record.get("attack_name", "unknown_attack"))
        grouped_examples.setdefault(attack_name, []).append(
            {
                "sync_peak_rank": float(mechanism_trace.get("sync_peak_rank") or 0.0),
                "sync_alignment_error": float(
                    mechanism_trace.get("sync_alignment_error") or 0.0
                ),
            }
        )

    examples: list[dict[str, float | str]] = []
    for attack_name in sorted(grouped_examples):
        records = grouped_examples[attack_name]
        examples.append(
            {
                "attack_name": attack_name,
                "sync_peak_rank": round(
                    sum(record["sync_peak_rank"] for record in records) / len(records),
                    6,
                ),
                "sync_alignment_error": round(
                    sum(record["sync_alignment_error"] for record in records) / len(records),
                    6,
                ),
            }
        )
    return examples


def _build_sync_peak_canvas(
    examples: list[dict[str, float | str]],
) -> bytearray:
    if not isinstance(examples, list):
        raise TypeError("examples must be a list")
    pixels = bytearray(BACKGROUND_COLOR * (FIGURE_WIDTH * FIGURE_HEIGHT))
    _draw_rect(pixels, 64, 44, FIGURE_WIDTH - 36, 48, GRID_COLOR)
    _draw_rect(pixels, 64, FIGURE_HEIGHT - 64, FIGURE_WIDTH - 36, FIGURE_HEIGHT - 60, AXIS_COLOR)
    _draw_rect(pixels, 64, 44, 68, FIGURE_HEIGHT - 60, AXIS_COLOR)

    if not examples:
        _draw_rect(pixels, 120, 140, FIGURE_WIDTH - 120, 220, GRID_COLOR)
        return pixels

    max_rank = max(1.0, max(float(example["sync_peak_rank"]) for example in examples))
    max_error = max(1.0, max(float(example["sync_alignment_error"]) for example in examples))
    chart_left = 88
    chart_top = 64
    chart_bottom = FIGURE_HEIGHT - 80
    chart_width = FIGURE_WIDTH - 140
    group_width = max(24, chart_width // max(1, len(examples)))

    for row_index in range(1, 5):
        y = chart_bottom - int((chart_bottom - chart_top) * row_index / 4)
        _draw_rect(pixels, 68, y, FIGURE_WIDTH - 36, y + 1, GRID_COLOR)

    for example_index, example in enumerate(examples):
        group_left = chart_left + (example_index * group_width)
        rank_height = int(
            (chart_bottom - chart_top)
            * (float(example["sync_peak_rank"]) / max_rank)
        )
        error_height = int(
            (chart_bottom - chart_top)
            * (float(example["sync_alignment_error"]) / max_error)
        )
        bar_width = max(6, min(24, group_width // 4))
        rank_left = group_left + max(2, group_width // 5)
        error_left = rank_left + bar_width + 4
        _draw_rect(
            pixels,
            rank_left,
            chart_bottom - rank_height,
            rank_left + bar_width,
            chart_bottom,
            RANK_BAR_COLOR,
        )
        _draw_rect(
            pixels,
            error_left,
            chart_bottom - error_height,
            error_left + bar_width,
            chart_bottom,
            ERROR_BAR_COLOR,
        )
    return pixels


def _draw_rect(
    pixels: bytearray,
    left: int,
    top: int,
    right: int,
    bottom: int,
    color: tuple[int, int, int],
) -> None:
    if not isinstance(pixels, bytearray):
        raise TypeError("pixels must be a bytearray")
    if not isinstance(color, tuple) or len(color) != 3:
        raise ValueError("color must be an RGB tuple")
    clamped_left = max(0, min(FIGURE_WIDTH, int(left)))
    clamped_right = max(0, min(FIGURE_WIDTH, int(right)))
    clamped_top = max(0, min(FIGURE_HEIGHT, int(top)))
    clamped_bottom = max(0, min(FIGURE_HEIGHT, int(bottom)))
    for y in range(clamped_top, clamped_bottom):
        for x in range(clamped_left, clamped_right):
            pixel_offset = ((y * FIGURE_WIDTH) + x) * 3
            pixels[pixel_offset : pixel_offset + 3] = bytes(color)


def _write_rgb_png(
    file_path: Path,
    width: int,
    height: int,
    pixels: bytearray,
) -> None:
    if not isinstance(file_path, Path):
        raise TypeError("file_path must be a Path")
    if not isinstance(width, int) or not isinstance(height, int):
        raise TypeError("width and height must be integers")
    if width < 1 or height < 1:
        raise ValueError("width and height must be positive")
    if not isinstance(pixels, bytearray):
        raise TypeError("pixels must be a bytearray")
    expected_size = width * height * 3
    if len(pixels) != expected_size:
        raise ValueError("pixels length does not match RGB image dimensions")
    scanlines = bytearray()
    row_size = width * 3
    for row_index in range(height):
        scanlines.append(0)
        start = row_index * row_size
        scanlines.extend(pixels[start : start + row_size])

    file_path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + _build_png_chunk(
            b"IHDR",
            struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
        )
        + _build_png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9))
        + _build_png_chunk(b"IEND", b"")
    )


def _build_png_chunk(chunk_type: bytes, chunk_data: bytes) -> bytes:
    if not isinstance(chunk_type, bytes) or len(chunk_type) != 4:
        raise ValueError("chunk_type must contain four bytes")
    if not isinstance(chunk_data, bytes):
        raise TypeError("chunk_data must be bytes")
    return (
        struct.pack(">I", len(chunk_data))
        + chunk_type
        + chunk_data
        + struct.pack(">I", binascii.crc32(chunk_type + chunk_data) & 0xFFFFFFFF)
    )
