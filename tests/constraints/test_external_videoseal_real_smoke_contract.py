"""验证 external_videoseal 真实 smoke 入口的轻量契约。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.videoseal_adapter import (
    ADAPTER_VERSION,
    SCORE_MAPPING_RULE,
    ensure_videoseal_package_config_paths,
    normalize_payload_bits,
)
from scripts.prepare_baselines.run_videoseal_real_smoke import build_run_id

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]


def test_videoseal_source_manifest_declares_real_smoke_entrypoint() -> None:
    """确认 VideoSeal source manifest 已从纯 skeleton 推进到真实 smoke 入口就绪。"""
    manifest = json.loads(
        (ROOT / "configs" / "baselines" / "external_videoseal_source.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["adapter_status"] == "real_smoke_entrypoint_ready"
    assert manifest["score_mapping_rule"] == SCORE_MAPPING_RULE


def test_videoseal_payload_normalization_matches_model_capacity() -> None:
    """确认短 payload 会被确定性扩展到 VideoSeal 模型消息长度。"""
    normalized = normalize_payload_bits([0, 1, 1], expected_length=8)

    assert normalized == [0, 1, 1, 0, 1, 1, 0, 1]


def test_videoseal_real_smoke_run_id_uses_single_underscore_tokens() -> None:
    """确认 run_id 使用单下划线语义, 不使用双下划线结果身份。"""
    run_id = build_run_id(short_commit="abcdef0", timestamp_utc="20260611T060000Z")

    assert run_id == "external_videoseal_real_smoke_20260611T060000Z_abcdef0"
    assert "__" not in run_id
    assert ADAPTER_VERSION == "external_videoseal_real_smoke_adapter"


def test_videoseal_config_path_repair_copies_root_configs(tmp_path: Path) -> None:
    """确认上游根目录 configs 会复制到 videoseal 包内 configs。"""
    source_config_dir = tmp_path / "configs"
    source_config_dir.mkdir(parents=True)
    for filename in ("attenuation.yaml", "embedder.yaml", "extractor.yaml"):
        (source_config_dir / filename).write_text("model: smoke\n", encoding="utf-8")

    repair = ensure_videoseal_package_config_paths(tmp_path)

    assert repair["repair_name"] == "copy_root_configs_into_videoseal_package_configs"
    for filename in ("attenuation.yaml", "embedder.yaml", "extractor.yaml"):
        assert (tmp_path / "videoseal" / "configs" / filename).exists()
