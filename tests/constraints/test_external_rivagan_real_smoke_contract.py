"""验证 external_rivagan 真实 smoke 入口的轻量契约。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.rivagan_adapter import (
    ADAPTER_VERSION,
    DEFAULT_RIVAGAN_WEIGHT_URL,
    SCORE_MAPPING_RULE,
    normalize_payload_bits,
)
from scripts.prepare_baselines.run_rivagan_real_smoke import build_run_id

pytestmark = [pytest.mark.constraint, pytest.mark.unit]

ROOT = Path(__file__).resolve().parents[2]


def test_rivagan_source_manifest_declares_real_smoke_entrypoint() -> None:
    """确认 RivaGAN source manifest 已从纯 skeleton 推进到真实 smoke 入口就绪。"""
    manifest = json.loads(
        (ROOT / "configs" / "baselines" / "external_rivagan_source.json").read_text(
            encoding="utf-8"
        )
    )

    assert manifest["adapter_status"] == "real_smoke_entrypoint_ready"
    assert manifest["score_mapping_rule"] == SCORE_MAPPING_RULE
    assert manifest["model_weight_sources"][0]["weight_url"] == DEFAULT_RIVAGAN_WEIGHT_URL


def test_rivagan_payload_normalization_matches_model_capacity() -> None:
    """确认短 payload 会被确定性扩展到 RivaGAN 的 32-bit 消息长度。"""
    normalized = normalize_payload_bits([0, 1, 1], expected_length=8)

    assert normalized == [0, 1, 1, 0, 1, 1, 0, 1]


def test_rivagan_real_smoke_run_id_uses_single_underscore_tokens() -> None:
    """确认 run_id 使用单下划线语义, 不使用双下划线结果身份。"""
    run_id = build_run_id(short_commit="abcdef0", timestamp_utc="20260611T070000Z")

    assert run_id == "external_rivagan_real_smoke_20260611T070000Z_abcdef0"
    assert "__" not in run_id
    assert ADAPTER_VERSION == "external_rivagan_real_smoke_adapter"
