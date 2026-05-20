import os
import sys
from pathlib import Path
from dataclasses import replace
import json

# Ensure we can import from the current directory
sys.path.append(os.getcwd())

from main.attacks.temporal import TemporalAttackPlaceholder
from experiments.synthetic_tubelet_sync_probe.synthetic_video_latent import (
    SyntheticVideoLatentPlaceholder,
)
from main.methods.temporal_tubelet_watermark.method import build_method_from_config

TUBELET_SYNC_CONFIG = {
    "method_family": "temporal_tubelet_watermark",
    "method_variant": "tubelet_sync",
    "method_status": "formal_synthetic_probe",
    "enable_frame_prc": False,
    "enable_tubelet": True,
    "enable_sync": True,
    "enable_trajectory": False,
    "tubelet_length": 4,
    "score_calibration": {
        "embedding_projection_support_weight": 0.45,
    },
    "sync_search": {
        "offset_search_min": -16,
        "offset_search_max": 16,
        "enable_scale_search": True,
        "scale_candidates": [0.8, 1.0, 1.25],
        "scale_search_snap_radius": 3,
        "coverage_penalty_enabled": True,
    },
    "lambda_sync": 0.1,
    "fusion_rule": "sync_rescue_fusion",
}

def run_test():
    tmp_path = Path("tmp_test_dir")
    tmp_path.mkdir(exist_ok=True)
    
    backend = SyntheticVideoLatentPlaceholder(latent_shape=(32, 4, 16, 16))
    backend.set_output_root(tmp_path)
    base_sample = backend.build_sample(
        "sample_test_watermarked_positive_local_clip_cov_test",
        "test",
        "watermarked_positive",
    )
    
    # Use the default config (coverage_penalty_enabled=True)
    watermark_method_a = build_method_from_config(TUBELET_SYNC_CONFIG)
    watermarked_sample = watermark_method_a.embed(base_sample, {})
    
    seeded_sample = replace(
        watermarked_sample,
        latent_generation_seed_random=42,
    )
    # Short local clip (length 4)
    local_clip = TemporalAttackPlaceholder("local_clip", {"clip_length": 4})
    clipped_sample = local_clip.apply(seeded_sample)
    
    print(f"Ground truth offset: {clipped_sample.applied_attack_params['ground_truth_offset']}")

    # Config A: coverage_penalty_enabled=True
    res_a = watermark_method_a.detect(clipped_sample, threshold_record=None)
    
    # Config B: coverage_penalty_enabled=False
    config_b = dict(TUBELET_SYNC_CONFIG)
    import copy
    config_b["sync_search"] = copy.deepcopy(TUBELET_SYNC_CONFIG["sync_search"])
    config_b["sync_search"]["coverage_penalty_enabled"] = False
    watermark_method_b = build_method_from_config(config_b)
    res_b = watermark_method_b.detect(clipped_sample, threshold_record=None)
    
    fields = [
        "S_tubelet", "S_sync", "S_final",
        "S_payload_unaligned", "S_payload_aligned", "S_payload_rescue_gain",
        "sync_alignment_matched_count", "sync_alignment_candidate_count",
        "sync_alignment_coverage_ratio", "sync_candidate_score_raw",
        "sync_candidate_score_penalized", "sync_estimated_offset",
        "sync_ground_truth_offset"
    ]
    
    def extract(res):
        out = {}
        out["S_tubelet"] = float(res.S_tubelet) if getattr(res, "S_tubelet", None) is not None else None
        out["S_sync"] = float(res.S_sync) if getattr(res, "S_sync", None) is not None else None
        out["S_final"] = float(res.S_final) if getattr(res, "S_final", None) is not None else None
        for f in fields[3:]:
            val = res.mechanism_trace.get(f)
            if hasattr(val, "item"): val = val.item()
            out[f] = val
        return out

    print("\n--- Result A (Coverage Penalty Enabled) ---")
    print(json.dumps(extract(res_a), indent=2))
    
    print("\n--- Result B (Coverage Penalty Disabled) ---")
    print(json.dumps(extract(res_b), indent=2))

if __name__ == "__main__":
    run_test()
