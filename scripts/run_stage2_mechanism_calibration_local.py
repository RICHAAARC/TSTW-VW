"""
文件用途：本地运行 run_stage2_mechanism_calibration 的驱动脚本，对照
    paper_workflow/run_real_video_vae_latent_probe.ipynb 的逻辑。
File purpose: Local driver script for run_stage2_mechanism_calibration,
    mirroring the notebook workflow in paper_workflow/run_real_video_vae_latent_probe.ipynb.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# 确保仓库根目录在 sys.path 中 / Ensure repo root is on sys.path.
_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

os.chdir(_REPO_ROOT)

from paper_workflow.notebook_utils import real_video_vae_latent_probe_workflow as probe_workflow
from paper_workflow.notebook_utils import run_timing_workflow
from paper_workflow.notebook_utils import runtime_profile_workflow
from scripts.profile_runtime import iso_timestamp_utc


# ─── 默认参数 / Default parameters ─────────────────────────────────────────────

# notebook 中对应 TSTW_EXECUTION_RUNTIME_PROFILE
DEFAULT_EXECUTION_RUNTIME_PROFILE = "l4_stage2_calibration_aggressive"
DEFAULT_WORKFLOW_KEY = "real_video_vae_latent_probe_completion_formal"
DEFAULT_STEP_KEY = "step02_run_real_video_vae_latent_probe"
DEFAULT_FAMILY_ID_TEMPLATE = (
    "real_video_vae_latent_probe__formal__davis2017_trainval480p__3060"
)
DEFAULT_PROCESSED_DATASET_KEY = (
    "real_video_vae_latent_probe__davis2017_trainval480p__256x256__32f__8fps__freeze001"
)
DEFAULT_MODEL_ID = "stabilityai/sd-vae-ft-mse"

# 本地路径默认值（等价于 notebook 中的 DRIVE_ROOT / LOCAL_RUNTIME_ROOT）
DEFAULT_DRIVE_ROOT = Path("G:/我的云端硬盘")
DEFAULT_LOCAL_RUNTIME_ROOT = Path("E:/RunTime/TSTW-VW")

# 本次用户指定覆盖参数
DEFAULT_CROSS_EVENT_DECODE_BATCH_SIZE = 6
DEFAULT_CROSS_EVENT_ENCODE_BATCH_SIZE = 6
DEFAULT_SAMPLES_PER_ROLE_OVERRIDE = 20
DEFAULT_BATCH_SIZE_FRAMES = 32
DEFAULT_WORKER_COUNT = 1


# ─── 工具函数 / Helpers ──────────────────────────────────────────────────────────

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="本地运行 run_stage2_mechanism_calibration（对照 notebook 逻辑）。"
    )
    parser.add_argument(
        "--execution-runtime-profile",
        default=DEFAULT_EXECUTION_RUNTIME_PROFILE,
        help="Runtime profile 标识（默认: %(default)s）",
    )
    parser.add_argument(
        "--family-id-template",
        default=DEFAULT_FAMILY_ID_TEMPLATE,
        help="Family ID 模板字符串（默认: %(default)s）",
    )
    parser.add_argument(
        "--processed-dataset-key",
        default=DEFAULT_PROCESSED_DATASET_KEY,
        help="Processed dataset registry key（默认: %(default)s）",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_MODEL_ID,
        help="Hugging Face 模型 ID 或本地目录（默认: %(default)s）",
    )
    parser.add_argument(
        "--drive-root",
        type=Path,
        default=DEFAULT_DRIVE_ROOT,
        help="Drive/云端根目录，等价于 Colab /content/drive/MyDrive（默认: %(default)s）",
    )
    parser.add_argument(
        "--local-runtime-root",
        type=Path,
        default=DEFAULT_LOCAL_RUNTIME_ROOT,
        help="本地运行根目录，等价于 Colab /content/TSTW-VW（默认: %(default)s）",
    )
    parser.add_argument(
        "--cross-event-vae-decode-batch-size",
        type=int,
        default=DEFAULT_CROSS_EVENT_DECODE_BATCH_SIZE,
        help="Cross-event VAE decode 聚合 batch 大小（默认: %(default)s）",
    )
    parser.add_argument(
        "--cross-event-vae-encode-batch-size",
        type=int,
        default=DEFAULT_CROSS_EVENT_ENCODE_BATCH_SIZE,
        help="Cross-event VAE encode 聚合 batch 大小（默认: %(default)s）",
    )
    parser.add_argument(
        "--samples-per-role",
        type=int,
        default=DEFAULT_SAMPLES_PER_ROLE_OVERRIDE,
        help="每个 sample role 的样本数覆盖（默认: %(default)s）",
    )
    parser.add_argument(
        "--batch-size-frames",
        type=int,
        default=DEFAULT_BATCH_SIZE_FRAMES,
        help="VAE encode/decode 单次 frame batch 大小（默认: %(default)s）",
    )
    parser.add_argument(
        "--worker-count",
        type=int,
        default=DEFAULT_WORKER_COUNT,
        help="Shard 内 worker 数（cross-event batching 模式须为 1，默认: %(default)s）",
    )
    parser.add_argument(
        "--workflow-key",
        default=DEFAULT_WORKFLOW_KEY,
        help="结果登记 workflow 标识（默认: %(default)s）",
    )
    parser.add_argument(
        "--step-key",
        default=DEFAULT_STEP_KEY,
        help="结果登记 step 标识（默认: %(default)s）",
    )
    parser.add_argument(
        "--results-drive-root",
        type=Path,
        default=None,
        help="结果包保存目录（默认: <drive_root>/TSTW/results）",
    )
    parser.add_argument(
        "--skip-dataset-copy",
        action="store_true",
        default=False,
        help="跳过从 Drive 复制数据集（本地数据集已就位时使用）",
    )
    parser.add_argument(
        "--require-formal-pass",
        action="store_true",
        default=False,
        help="打包时要求 formal PASS（默认允许 INCONCLUSIVE）",
    )
    return parser.parse_args(argv)


def _load_runtime_profile_config(runtime_profile: str) -> dict:
    """加载 runtime profile 配置文件。"""
    profile_path = _REPO_ROOT / "configs" / "runtime_profiles" / f"{runtime_profile}.json"
    if not profile_path.exists():
        # 回退到 l4_debug profile
        profile_path = _REPO_ROOT / "configs" / "runtime_profiles" / "l4_debug.json"
        print(
            f"[警告] runtime profile '{runtime_profile}' 不存在，"
            f"回退到 {profile_path.name}"
        )
    with profile_path.open(encoding="utf-8") as f:
        payload = json.load(f)
    return {
        **payload,
        "config_path": str(profile_path),
        "config_digest": "",
        "profile_runtime": payload.get("profile_run_timing", True),
        "profile_gpu_runtime": payload.get("profile_gpu_runtime", True),
        "gpu_profile_interval_seconds": payload.get("gpu_profile_interval_seconds", 2),
        "profile_drive_io": payload.get("profile_drive_io", False),
        "drive_io_sample_size_mb": payload.get("drive_io_sample_size_mb", 32),
        "write_runtime_recommendation": payload.get("write_runtime_recommendation", False),
        "vae_batch_size_frames": payload.get("vae_batch_size_frames", 8),
        "lpips_batch_size": payload.get("lpips_batch_size", 8),
        "clip_batch_size": payload.get("clip_batch_size", 8),
        "worker_count": payload.get("worker_count", 1),
        "video_io_worker_count": payload.get("video_io_worker_count", 1),
        "attack_worker_count": payload.get("attack_worker_count", 1),
        "shard_count": payload.get("shard_count", 1),
        "reuse_encoded_latents": payload.get("reuse_encoded_latents", False),
        "reuse_decoded_videos": payload.get("reuse_decoded_videos", False),
        "reuse_attacked_videos": payload.get("reuse_attacked_videos", False),
    }


def _persist_runtime_profile_plan(run_root: Path, payload: dict) -> dict:
    """持久化 runtime profile plan 到 run_root/runtime_profile 目录。"""
    runtime_profile_dir = run_root / "runtime_profile"
    runtime_profile_dir.mkdir(parents=True, exist_ok=True)
    plan_path = runtime_profile_dir / "runtime_profile_plan.json"
    plan_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {**payload, "plan_path": str(plan_path)}


def main(argv: list[str] | None = None) -> int:
    """本地运行 stage2 mechanism calibration 的主入口。

    Run the governed stage-two mechanism calibration locally,
    mirroring the notebook workflow step by step.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    args = _parse_args(argv)

    # ─── 路径解析（对应 notebook cell 3 路径初始化块）──────────────────────────────
    run_mode = "formal"
    runtime_profile = "formal"
    execution_runtime_profile = args.execution_runtime_profile
    workflow_key = args.workflow_key
    step_key = args.step_key
    family_id_template = args.family_id_template
    processed_dataset_key = args.processed_dataset_key
    model_id = args.model_id
    drive_root: Path = args.drive_root
    local_runtime_root: Path = args.local_runtime_root
    batch_size_frames: int = args.batch_size_frames
    worker_count: int = args.worker_count
    cross_event_vae_decode_batch_size: int = args.cross_event_vae_decode_batch_size
    cross_event_vae_encode_batch_size: int = args.cross_event_vae_encode_batch_size
    samples_per_role: int = args.samples_per_role
    require_formal_pass: bool = args.require_formal_pass

    cross_event_vae_batching_enabled = True
    if cross_event_vae_batching_enabled and worker_count != 1:
        raise ValueError(
            "cross-event VAE batching 模式要求 worker_count=1，"
            f"当前 worker_count={worker_count}"
        )

    # ─── 加载 execution runtime profile 配置 ──────────────────────────────────────
    execution_profile_config = _load_runtime_profile_config(execution_runtime_profile)

    # ─── 路径变量（与 notebook 变量名对应）──────────────────────────────────────────
    processed_dataset_root = (
        drive_root / "TSTW" / "datasets" / "processed" / processed_dataset_key
    )
    local_dataset_root = local_runtime_root / "datasets" / processed_dataset_key
    local_model_root = local_runtime_root / "session_models" / "autoencoder_kl"

    results_drive_root: Path = (
        args.results_drive_root
        if args.results_drive_root is not None
        else drive_root / "TSTW" / "results"
    )

    # Git commit 用于 family_id 物化
    git_commit = subprocess.check_output(
        ["git", "rev-parse", "--short", "HEAD"],
        text=True,
        cwd=_REPO_ROOT,
    ).strip()

    family_id = probe_workflow.materialize_family_id(
        family_id_template=family_id_template,
        git_commit=git_commit,
    )

    family_root = results_drive_root / "families" / family_id
    run_root = local_runtime_root / "runs" / "real_video_vae_latent_probe_formal"
    run_id = run_root.name
    runtime_config_path = run_root / "artifacts" / "runtime_config.json"
    session_model_manifest_path = run_root / "artifacts" / "session_model_manifest.json"

    # stage2 calibration 独立 run root（避免覆盖主 formal run 产物）
    stage2_calibration_run_root = (
        local_runtime_root / "runs" / "real_video_vae_latent_probe_stage2_mechanism_calibration"
    )
    stage2_candidate_method_config_path = (
        stage2_calibration_run_root / "artifacts" / "tubelet_sync_real_video_vae_candidate.json"
    )
    stage2_calibration_summary_path = (
        stage2_calibration_run_root / "artifacts" / "stage2_mechanism_calibration_summary.json"
    )

    attack_matrix_path = Path("configs/attacks/real_video_attack_matrix.json")
    ablation_config_path = Path("configs/ablation/real_video_vae_latent_ablation.json")
    stage2_mechanism_config_path = Path("configs/protocol/stage2_mechanism_gate.json")
    stage2_calibration_grid_path = Path(
        "configs/ablation/stage2_vae_mechanism_calibration_grid.json"
    )

    print(
        json.dumps(
            {
                "run_mode": run_mode,
                "runtime_profile": runtime_profile,
                "execution_runtime_profile": execution_runtime_profile,
                "batch_size_frames": batch_size_frames,
                "worker_count": worker_count,
                "cross_event_vae_batching_enabled": cross_event_vae_batching_enabled,
                "cross_event_vae_decode_batch_size": cross_event_vae_decode_batch_size,
                "cross_event_vae_encode_batch_size": cross_event_vae_encode_batch_size,
                "samples_per_role": samples_per_role,
                "family_id_template": family_id_template,
                "family_id": family_id,
                "git_commit": git_commit,
                "processed_dataset_root": str(processed_dataset_root),
                "local_dataset_root": str(local_dataset_root),
                "run_root": str(run_root),
                "family_root": str(family_root),
                "stage2_calibration_run_root": str(stage2_calibration_run_root),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    # ─── Step 01: runtime profile plan 持久化 ─────────────────────────────────────
    effective_profile_plan = dict(execution_profile_config)
    effective_profile_plan["vae_batch_size_frames"] = batch_size_frames
    effective_profile_plan["batch_size_frames"] = batch_size_frames
    effective_profile_plan["worker_count"] = worker_count
    effective_profile_plan["cross_event_vae_batching_enabled"] = cross_event_vae_batching_enabled
    effective_profile_plan["cross_event_vae_decode_batch_size"] = cross_event_vae_decode_batch_size
    effective_profile_plan["cross_event_vae_encode_batch_size"] = cross_event_vae_encode_batch_size

    run_timer = run_timing_workflow.start_run_timing(run_root=run_root, run_id=run_id)
    runtime_profile_plan = _persist_runtime_profile_plan(run_root, effective_profile_plan)

    # ─── Step 02: 准备本地 runtime workspace（对应 notebook cell 9）──────────────────
    print("\n[Step 02] 准备本地 runtime workspace ...")
    if not processed_dataset_root.exists():
        raise FileNotFoundError(
            f"processed_dataset_root 不存在: {processed_dataset_root}\n"
            "请确认 Drive 已挂载，且 G:\\我的云端硬盘\\TSTW 目录包含分片数据集。"
        )
    runtime_workspace_handoff = probe_workflow.prepare_probe_runtime_workspace(
        processed_dataset_root=processed_dataset_root,
        local_dataset_root=local_dataset_root,
        family_root=family_root,
        run_root=run_root,
        copy_processed_dataset=not args.skip_dataset_copy,
    )
    local_dataset_root = Path(runtime_workspace_handoff["local_dataset_root"])
    processed_dataset_manifest = Path(runtime_workspace_handoff["local_dataset_manifest_path"])
    if not processed_dataset_manifest.exists():
        raise FileNotFoundError(processed_dataset_manifest)
    print(json.dumps(runtime_workspace_handoff, ensure_ascii=False, indent=2))

    # ─── Step 03: 准备 session model（对应 notebook cell 15）────────────────────────
    print("\n[Step 03] 准备 session model ...")
    with run_timer.event("model_preparation", run_mode=run_mode, runtime_profile=runtime_profile):
        session_model_manifest = probe_workflow.prepare_probe_session_model(
            model_id=model_id,
            local_model_root=local_model_root,
            session_manifest_path=session_model_manifest_path,
            revision="main",
        )
    local_model_root = Path(session_model_manifest["models"][0]["local_path"])
    if not local_model_root.exists():
        raise FileNotFoundError(local_model_root)
    print(json.dumps(session_model_manifest, ensure_ascii=False, indent=2))

    # ─── Step 04: 写出 runtime config（对应 notebook cell 17）──────────────────────
    print("\n[Step 04] 写出 runtime config ...")
    runtime_extra_config: dict = {
        "family_id": family_id,
        "workflow_key": workflow_key,
        "step_key": step_key,
        "git_commit": git_commit,
        "execution_runtime_profile": execution_runtime_profile,
        "runtime_profile_config_path": effective_profile_plan.get("config_path", ""),
        "runtime_profile_config_digest": effective_profile_plan.get("config_digest", ""),
        "batch_size_frames": batch_size_frames,
        "cross_event_vae_batching_enabled": cross_event_vae_batching_enabled,
        "cross_event_vae_decode_batch_size": cross_event_vae_decode_batch_size,
        "cross_event_vae_encode_batch_size": cross_event_vae_encode_batch_size,
        "lpips_batch_size": int(execution_profile_config.get("lpips_batch_size", 8)),
        "clip_batch_size": int(execution_profile_config.get("clip_batch_size", 8)),
        "worker_count": worker_count,
        "video_io_worker_count": int(
            execution_profile_config.get("video_io_worker_count", 1)
        ),
        "attack_worker_count": int(
            execution_profile_config.get("attack_worker_count", 1)
        ),
        "shard_count": int(execution_profile_config.get("shard_count", 1)),
        "shard_index": 0,
        "reuse_encoded_latents": bool(
            execution_profile_config.get("reuse_encoded_latents", False)
        ),
        "reuse_decoded_videos": bool(
            execution_profile_config.get("reuse_decoded_videos", False)
        ),
        "reuse_attacked_videos": bool(
            execution_profile_config.get("reuse_attacked_videos", False)
        ),
        "quality_metrics": {
            "enable_lpips": False,
            "enable_clip_similarity": False,
        },
        "temporal_metrics": {
            "enable_motion_consistency": False,
        },
        "runtime_manifest_overrides": {
            "family_root": str(family_root),
            "session_model_manifest_path": str(session_model_manifest_path),
        },
    }
    runtime_config_handoff = probe_workflow.write_probe_runtime_config(
        runtime_config_path=runtime_config_path,
        execution_environment="local",
        processed_dataset_key=processed_dataset_key,
        local_dataset_root=local_dataset_root,
        processed_dataset_root=processed_dataset_root,
        vae_model_local_path=local_model_root,
        dataset_manifest_path=processed_dataset_manifest,
        require_formal_pass_criteria=require_formal_pass,
        extra_config=runtime_extra_config,
    )
    print(json.dumps(runtime_config_handoff["runtime_config"], ensure_ascii=False, indent=2))

    # ─── Step 05: 运行 stage2 mechanism calibration（对应 notebook cell 31）──────────
    print("\n[Step 05] 运行 stage2 mechanism calibration ...")
    with run_timer.event(
        "stage2_mechanism_calibration", run_mode=run_mode, runtime_profile=runtime_profile
    ):
        stage2_calibration_summary = probe_workflow.run_probe_stage2_mechanism_calibration(
            run_root=stage2_calibration_run_root,
            run_mode=run_mode,
            runtime_profile=runtime_profile,
            grid_config_path=stage2_calibration_grid_path,
            attack_matrix_path=attack_matrix_path,
            ablation_config_path=ablation_config_path,
            mechanism_config_path=stage2_mechanism_config_path,
            dataset_manifest_path=processed_dataset_manifest,
            runtime_config_path=runtime_config_path,
            samples_per_role=samples_per_role,
            batch_size_frames=batch_size_frames,
            output_method_config_path=stage2_candidate_method_config_path,
        )
    print(
        json.dumps(
            {
                "stage2_calibration_summary_path": str(stage2_calibration_summary_path),
                "stage2_candidate_method_config_path": str(stage2_candidate_method_config_path),
                "stage2_calibration_summary": stage2_calibration_summary,
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    # ─── Step 06: 打包结果到 Drive（对应 notebook cell 33 打包逻辑）──────────────────
    # 注意：stage2 calibration 独立 run root；本脚本仅打包 calibration run root。
    # 若需打包主 formal run_root，需先运行主 formal 流程（run_main_formal）。
    print("\n[Step 06] 打包 stage2 calibration 结果 ...")
    stage2_family_root = results_drive_root / "families" / family_id / "stage2_calibration"
    stage2_family_root.mkdir(parents=True, exist_ok=True)

    # 将 calibration summary JSON 写到 family_root 方便归档
    summary_copy_path = stage2_family_root / "stage2_mechanism_calibration_summary.json"
    summary_copy_path.write_text(
        json.dumps(stage2_calibration_summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    # 将 candidate method config 写到 family_root
    if stage2_candidate_method_config_path.exists():
        import shutil
        candidate_copy_path = (
            stage2_family_root / "tubelet_sync_real_video_vae_candidate.json"
        )
        shutil.copy2(stage2_candidate_method_config_path, candidate_copy_path)
        print(f"candidate method config -> {candidate_copy_path}")

    run_timing_summary = run_timing_workflow.summarize_run_timing(run_root=run_root)
    final_summary = {
        "family_id": family_id,
        "run_root": str(run_root),
        "family_root": str(family_root),
        "stage2_calibration_run_root": str(stage2_calibration_run_root),
        "stage2_family_root": str(stage2_family_root),
        "stage2_calibration_summary": stage2_calibration_summary,
        "run_timing_summary": run_timing_summary,
        "stage2_candidate_method_config_path": str(stage2_candidate_method_config_path),
        "summary_copy_path": str(summary_copy_path),
    }
    print("\n[完成] 最终摘要：")
    print(json.dumps(final_summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
