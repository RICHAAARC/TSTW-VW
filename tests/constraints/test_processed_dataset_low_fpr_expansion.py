"""验证 processed real-video dataset 的论文级低 FPR 扩容契约。"""

from __future__ import annotations

import pytest

from scripts.prepare_datasets.build_processed_real_video_dataset import (
    RawSource,
    _build_processing_plan,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def test_processing_plan_expands_long_sources_with_temporal_windows() -> None:
    """确认长 DAVIS 序列可以切成多个 32 帧窗口。

    该测试不解压真实 DAVIS 数据, 只验证计划层语义: 当启用 `clip_stride_frames=8`
    时, 每个长序列会贡献多个 processed source video, 从而为 1% FPR 提供更多
    calibration/test negative 评估单元。
    """
    raw_sources = [
        RawSource(
            source_path=__file__,
            source_kind="frame_directory",
            source_key=f"davis/JPEGImages/480p/sequence_{index:03d}",
        )
        for index in range(9)
    ]
    source_frame_counts = {source.source_key: 64 for source in raw_sources}

    plan = _build_processing_plan(
        raw_sources,
        source_frame_counts=source_frame_counts,
        target_frame_count=32,
        clip_stride_frames=8,
        max_samples_per_split=12,
    )
    split_counts: dict[str, int] = {}
    for item in plan:
        split_counts[item.split_name] = split_counts.get(item.split_name, 0) + 1

    assert split_counts == {"dev": 12, "calibration": 12, "test": 12}
    assert all(item.clip_start_frame is not None for item in plan)
