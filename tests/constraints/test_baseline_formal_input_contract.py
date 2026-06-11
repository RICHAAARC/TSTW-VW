"""验证 baseline comparison 正式输入契约构建。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.baseline_comparison_gate.formal_input_contract import (
    build_formal_input_contract,
    write_formal_input_contract,
)

pytestmark = [pytest.mark.constraint, pytest.mark.unit]


def write_stage_two_records(root: Path, *, attacks: list[str] | None = None) -> Path:
    """写出最小阶段二 records, 用于验证输入契约。"""
    package_root = root / "real_video_vae_latent_probe_formal"
    records_dir = package_root / "records"
    records_dir.mkdir(parents=True)
    attacks = attacks or [
        "no_attack",
        "h264_compression",
        "h265_compression",
        "spatial_resize",
        "crop_resize",
        "blur",
        "gaussian_noise",
        "temporal_crop",
        "local_clip",
        "frame_dropping",
        "speed_change",
    ]
    rows = []
    for split in ("dev", "calibration", "test"):
        for method in ("frame_prc", "tubelet_only", "tubelet_sync"):
            for attack in attacks:
                rows.append(
                    {
                        "split": split,
                        "sample_role": "attacked_negative" if split == "calibration" else "attacked_positive",
                        "attack_name": attack,
                        "method_variant": method,
                        "target_fpr": 0.001,
                        "sample_id": f"sample_{split}_{method}_{attack}",
                    }
                )
    (records_dir / "event_scores.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return package_root


def write_config(path: Path) -> Path:
    """写出最小 baseline comparison 配置。"""
    config = {
        "input_stage_package": {"workflow_key": "real_video_vae_latent_probe_stage2_final_formal_audit"},
        "baselines": ["external_videoseal", "external_rivagan", "external_hidden_framewise"],
        "internal_method_variants": ["frame_prc", "tubelet_only", "tubelet_sync"],
        "splits": ["dev", "calibration", "test"],
        "formal_attack_names": [
            "no_attack",
            "h264_compression",
            "h265_compression",
            "spatial_resize",
            "crop_resize",
            "blur",
            "gaussian_noise",
            "temporal_crop",
            "local_clip",
            "frame_dropping",
            "speed_change",
        ],
        "attack_display_names": [{"attack_name": "no_attack", "display_name": "clean"}],
        "threshold_protocol": {
            "calibration_split": "calibration",
            "calibration_negative_roles": ["clean_negative", "attacked_negative"],
            "test_threshold_update_allowed": False,
            "target_fprs": [0.001],
        },
        "required_output_artifacts": ["tables/baseline_comparison_table.csv"],
    }
    path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
    return path


def write_smoke_summary(path: Path) -> Path:
    """写出最小真实 smoke 汇总。"""
    summary = {
        "package_ready_for_formal_planning": True,
        "entries": [
            {"baseline_name": "external_videoseal", "status": "real_smoke_passed"},
            {"baseline_name": "external_rivagan", "status": "real_smoke_passed"},
            {"baseline_name": "external_hidden_framewise", "status": "real_smoke_executed_negative"},
        ],
    }
    path.write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return path


def test_formal_input_contract_accepts_aligned_stage_two_records(tmp_path: Path) -> None:
    """确认阶段二 records 与阶段三配置完全一致时可进入正式 runner。"""
    package_root = write_stage_two_records(tmp_path)
    config_path = write_config(tmp_path / "baseline_config.json")
    smoke_path = write_smoke_summary(tmp_path / "smoke_summary.json")

    contract = build_formal_input_contract(
        stage_two_package_root=package_root,
        baseline_config_path=config_path,
        real_smoke_summary_path=smoke_path,
    )

    assert contract["ready_for_formal_baseline_runner"] is True
    assert contract["violations"] == []
    assert contract["real_smoke_status_by_baseline"]["external_hidden_framewise"] == "real_smoke_executed_negative"


def test_formal_input_contract_rejects_attack_name_mismatch(tmp_path: Path) -> None:
    """确认配置中的攻击矩阵必须与阶段二 records 的实际攻击名一致。"""
    package_root = write_stage_two_records(tmp_path, attacks=["no_attack"])
    config_path = write_config(tmp_path / "baseline_config.json")

    contract = build_formal_input_contract(
        stage_two_package_root=package_root,
        baseline_config_path=config_path,
    )

    assert contract["ready_for_formal_baseline_runner"] is False
    assert any(violation["field"] == "formal_attack_names" for violation in contract["violations"])


def test_write_formal_input_contract_outputs_manifest(tmp_path: Path) -> None:
    """确认输入契约会写入会话本地 run_root, 而不是写入 outputs 目录。"""
    package_root = write_stage_two_records(tmp_path)
    config_path = write_config(tmp_path / "baseline_config.json")
    contract = build_formal_input_contract(
        stage_two_package_root=package_root,
        baseline_config_path=config_path,
    )

    outputs = write_formal_input_contract(contract, tmp_path / "baseline_comparison_formal")

    assert Path(outputs["contract_path"]).exists()
    assert Path(outputs["manifest_path"]).exists()
    assert "outputs" not in outputs["contract_path"]
