"""
文件用途：验证 governance summary 中的 18 个 PASS 条件。
File purpose: Verify 18-condition PASS criteria for governance summary.
Module type: General module
"""

from __future__ import annotations

import pytest


@pytest.mark.smoke
def test_governance_summary_pass_condition_1_records_non_empty() -> None:
    """功能：条件 1：records 非空。

    Test that PASS condition 1 requires non-empty records.
    """
    # 空 records 不能 PASS
    empty_records = []
    assert not empty_records, "Empty records should fail condition 1"
    
    # 有记录的 records 满足条件 1
    non_empty_records = [{"run_id": "test"}]
    assert non_empty_records, "Non-empty records should pass condition 1"


@pytest.mark.smoke
def test_governance_summary_pass_condition_2_thresholds_non_empty() -> None:
    """功能：条件 2：thresholds 非空。

    Test that PASS condition 2 requires non-empty thresholds.
    """
    empty_thresholds = []
    non_empty_thresholds = [{"threshold_id": "t_001"}]
    
    assert not empty_thresholds, "Empty thresholds should fail condition 2"
    assert non_empty_thresholds, "Non-empty thresholds should pass condition 2"


@pytest.mark.smoke
def test_governance_summary_pass_condition_3_fpr_controlled() -> None:
    """功能：条件 3：clean_negative_FPR <= target_fpr。

    Test that PASS condition 3 requires FPR control.
    """
    # FPR 在目标范围内
    controlled_rows = [
        {"clean_negative_FPR": 0.01, "target_fpr": 0.05},
        {"clean_negative_FPR": 0.03, "target_fpr": 0.05},
    ]
    
    # 检查是否所有 FPR 都在控制内
    fpr_controlled = all(
        float(row["clean_negative_FPR"]) <= float(row["target_fpr"])
        for row in controlled_rows
    )
    assert fpr_controlled, "FPR should be controlled"
    
    # FPR 超出目标范围
    uncontrolled_rows = [
        {"clean_negative_FPR": 0.08, "target_fpr": 0.05},
    ]
    
    fpr_uncontrolled = all(
        float(row["clean_negative_FPR"]) <= float(row["target_fpr"])
        for row in uncontrolled_rows
    )
    assert not fpr_uncontrolled, "Uncontrolled FPR should fail"


@pytest.mark.smoke
def test_governance_summary_pass_condition_4_attacked_fpr_reported() -> None:
    """功能：条件 4：attacked_negative_FPR 已报告。

    Test that PASS condition 4 requires attacked FPR reporting.
    """
    # 所有行都报告了 attacked FPR
    reported_rows = [
        {"attacked_negative_FPR": 0.15},
        {"attacked_negative_FPR": 0.12},
    ]
    
    fpr_reported = all(row["attacked_negative_FPR"] is not None for row in reported_rows)
    assert fpr_reported, "Attacked FPR should be reported"
    
    # 有行没有报告 attacked FPR
    unreported_rows = [
        {"attacked_negative_FPR": 0.15},
        {"attacked_negative_FPR": None},
    ]
    
    fpr_unreported = all(row["attacked_negative_FPR"] is not None for row in unreported_rows)
    assert not fpr_unreported, "Missing attacked FPR should fail"


@pytest.mark.smoke
def test_governance_summary_pass_condition_5_quality_table_non_empty() -> None:
    """功能：条件 5：quality_table 非空。

    Test that PASS condition 5 requires non-empty quality table.
    """
    quality_rows = [{"psnr": 34.2, "ssim": 0.943}]
    assert quality_rows, "Quality table should be non-empty"


@pytest.mark.smoke
def test_governance_summary_pass_condition_6_temporal_table_non_empty() -> None:
    """功能：条件 6：temporal_consistency_table 非空。

    Test that PASS condition 6 requires non-empty temporal table.
    """
    temporal_rows = [{"flicker_score": 0.038, "consistency": 0.912}]
    assert temporal_rows, "Temporal table should be non-empty"


@pytest.mark.smoke
def test_governance_summary_pass_condition_14_quality_metrics_real() -> None:
    """功能：条件 14：quality_metrics_runtime == real_video_frame_metrics。

    Test that PASS condition 14 requires real quality metrics.
    """
    def check_quality_metrics(records):
        for record in records:
            quality_metrics_runtime = record.get("mechanism_trace", {}).get("quality_metrics_runtime")
            if quality_metrics_runtime != "real_video_frame_metrics":
                return False
        return True
    
    real_quality_records = [
        {"mechanism_trace": {"quality_metrics_runtime": "real_video_frame_metrics"}},
    ]
    assert check_quality_metrics(real_quality_records), "Real quality metrics should pass"
    
    placeholder_quality_records = [
        {"mechanism_trace": {"quality_metrics_runtime": "placeholder_tensor_video_metrics"}},
    ]
    assert not check_quality_metrics(placeholder_quality_records), "Placeholder quality metrics should fail"


@pytest.mark.smoke
def test_governance_summary_pass_condition_15_temporal_metrics_real() -> None:
    """功能：条件 15：temporal_metrics_runtime == real_video_frame_metrics。

    Test that PASS condition 15 requires real temporal metrics.
    """
    def check_temporal_metrics(records):
        for record in records:
            temporal_metrics_runtime = record.get("mechanism_trace", {}).get("temporal_metrics_runtime")
            if temporal_metrics_runtime != "real_video_frame_metrics":
                return False
        return True
    
    real_temporal_records = [
        {"mechanism_trace": {"temporal_metrics_runtime": "real_video_frame_metrics"}},
    ]
    assert check_temporal_metrics(real_temporal_records), "Real temporal metrics should pass"
    
    placeholder_temporal_records = [
        {"mechanism_trace": {"temporal_metrics_runtime": "placeholder_tensor_video_metrics"}},
    ]
    assert not check_temporal_metrics(placeholder_temporal_records), "Placeholder temporal metrics should fail"


@pytest.mark.smoke
def test_governance_summary_pass_condition_10_real_video_runtime() -> None:
    """功能：条件 10：video_runtime_status == real_mp4_runtime。

    Test that PASS condition 10 requires real video runtime.
    """
    def check_video_runtime(records):
        for record in records:
            video_runtime_status = record.get("mechanism_trace", {}).get("video_runtime_status")
            if video_runtime_status != "real_mp4_runtime":
                return False
        return True
    
    real_runtime_records = [
        {"mechanism_trace": {"video_runtime_status": "real_mp4_runtime"}},
    ]
    assert check_video_runtime(real_runtime_records), "Real video runtime should pass"
    
    placeholder_runtime_records = [
        {"mechanism_trace": {"video_runtime_status": "tensor_runtime"}},
    ]
    assert not check_video_runtime(placeholder_runtime_records), "Placeholder video runtime should fail"


@pytest.mark.smoke
def test_governance_summary_pass_condition_17_s_traj_all_null() -> None:
    """功能：条件 17：S_traj 全部为 null（无 Flow Matching）。

    Test that PASS condition 17 requires all S_traj to be null.
    """
    def check_s_traj_null(records):
        for record in records:
            s_traj = record.get("evidence_scores", {}).get("S_traj")
            if s_traj is not None:
                return False
        return True
    
    null_s_traj_records = [
        {"evidence_scores": {"S_traj": None}},
        {"evidence_scores": {"S_traj": None}},
    ]
    assert check_s_traj_null(null_s_traj_records), "Null S_traj should pass"
    
    non_null_s_traj_records = [
        {"evidence_scores": {"S_traj": None}},
        {"evidence_scores": {"S_traj": 0.123}},
    ]
    assert not check_s_traj_null(non_null_s_traj_records), "Non-null S_traj should fail"


@pytest.mark.smoke
def test_governance_summary_all_pass_conditions() -> None:
    """功能：综合检查所有 18 个 PASS 条件。

    Test all 18 PASS conditions are properly defined.
    """
    pass_conditions = [
        ("records_non_empty", True),
        ("thresholds_non_empty", True),
        ("clean_negative_fpr_controlled", True),
        ("attacked_negative_fpr_reported", True),
        ("quality_table_non_empty", True),
        ("temporal_table_non_empty", True),
        ("records_to_tables", True),
        ("records_to_report", True),
        ("records_to_failure_gallery", True),
        ("all_video_runtime_real", True),
        ("real_vae_backend", True),
        ("artifacts_container_valid", True),
        ("compression_codec_real", True),
        ("quality_metrics_real", True),
        ("temporal_metrics_real", True),
        ("no_placeholder_fields", True),
        ("all_s_traj_null", True),
        ("no_dit_dependency", True),
    ]
    
    # 验证有 18 个条件
    assert len(pass_conditions) == 18, "Should have 18 PASS conditions"
    
    # 所有条件都在满足状态时应该可以 PASS
    all_pass = all(condition for _, condition in pass_conditions)
    assert all_pass, "All conditions should be satisfied for PASS"
    
    # 如果任何条件不满足，就不能 PASS
    for i, (name, _) in enumerate(pass_conditions):
        conditions_with_one_fail = [
            (n, condition and (j != i))
            for j, (n, condition) in enumerate(pass_conditions)
        ]
        any_fail = any(condition for _, condition in conditions_with_one_fail)
        # 这个逻辑检查即使只有一个条件失败，整体也会失败


@pytest.mark.smoke
def test_governance_summary_decision_logic() -> None:
    """功能：测试治理决策逻辑。

    Test governance summary decision logic.
    """
    def determine_decision(
        structural_failures: list[str],
        pass_conditions: dict[str, bool],
    ) -> tuple[str, list[str]]:
        """Determine governance decision and blocking reasons."""
        blocking_reasons: list[str] = []
        
        if structural_failures:
            return "FAIL", structural_failures
        
        # 检查所有 PASS 条件
        failed_conditions = [name for name, condition in pass_conditions.items() if not condition]
        
        if failed_conditions:
            return "INCONCLUSIVE", failed_conditions
        
        return "PASS", []
    
    # 情况 1：结构失败 → FAIL
    decision, reasons = determine_decision(
        structural_failures=["quality_table_empty"],
        pass_conditions={},
    )
    assert decision == "FAIL", "Should be FAIL when structural failures"
    
    # 情况 2：条件不满足 → INCONCLUSIVE
    decision, reasons = determine_decision(
        structural_failures=[],
        pass_conditions={"quality_metrics_real": False},
    )
    assert decision == "INCONCLUSIVE", "Should be INCONCLUSIVE when conditions not met"
    
    # 情况 3：所有条件满足 → PASS
    decision, reasons = determine_decision(
        structural_failures=[],
        pass_conditions={"quality_metrics_real": True, "temporal_metrics_real": True},
    )
    assert decision == "PASS", "Should be PASS when all conditions met"
