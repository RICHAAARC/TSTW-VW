"""阶段四 paper artifact gate 的投稿图表生成器。

该模块只从 `tables/` 和 `figure_data/` 中读取已经受治理的 CSV, 生成可投递论文使用的静态 PNG/PDF 图表。
图表不是新的实验结果, 而是对已冻结表格的可视化表达。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from main.core.digest import compute_file_digest

FIGURE_DPI = 300
METHOD_ORDER = [
    "tubelet_sync",
    "tubelet_only",
    "frame_prc",
    "external_videoseal",
    "external_hidden_framewise",
    "external_rivagan",
]
METHOD_LABELS = {
    "tubelet_sync": "Tubelet-Sync",
    "tubelet_only": "Tubelet-Only",
    "frame_prc": "Frame PRC",
    "external_videoseal": "VideoSeal",
    "external_hidden_framewise": "HiDDeN framewise",
    "external_rivagan": "RivaGAN",
}
ATTACK_LABELS = {
    "no_attack": "Clean",
    "h264_compression": "H.264",
    "h265_compression": "H.265",
    "spatial_resize": "Resize",
    "crop_resize": "Crop-resize",
    "blur": "Blur",
    "gaussian_noise": "Gaussian noise",
    "frame_dropping": "Frame dropping",
    "speed_change": "Speed change",
    "temporal_crop": "Temporal crop",
    "local_clip": "Local clip",
}
TEMPORAL_ATTACKS = ["frame_dropping", "speed_change", "temporal_crop", "local_clip"]


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """读取 UTF-8 CSV 图表数据。"""
    with Path(path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def safe_float(value: Any) -> float:
    """将 CSV 数值字段转换为 float, 空值视为 0。"""
    if value is None or value == "":
        return 0.0
    return float(value)


def ensure_matplotlib():
    """延迟导入 matplotlib, 使无图形依赖环境仍能读取阶段四表格。"""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    return plt, np


def save_figure(fig: Any, output_base: Path, root: Path) -> dict[str, str]:
    """同时保存 PDF 和 PNG, 并在 manifest 中记录相对路径。"""
    output_base.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = output_base.with_suffix(".pdf")
    png_path = output_base.with_suffix(".png")
    fig.savefig(pdf_path, bbox_inches="tight")
    fig.savefig(png_path, dpi=FIGURE_DPI, bbox_inches="tight")
    return {"pdf": pdf_path.relative_to(root).as_posix(), "png": png_path.relative_to(root).as_posix()}


def build_method_comparison_figure(root: Path) -> dict[str, Any]:
    """生成主方法比较图, 展示各方法在 1% FPR 下的整体 TPR。"""
    plt, _ = ensure_matplotlib()
    rows = read_csv_rows(root / "tables" / "paper_method_comparison_table.csv")
    by_name = {row["method_name"]: row for row in rows}
    ordered = [by_name[name] for name in METHOD_ORDER if name in by_name]
    labels = [METHOD_LABELS.get(row["method_name"], row["method_name"]) for row in ordered]
    values = [safe_float(row["tpr_at_target_fpr"]) for row in ordered]
    colors = ["#1f77b4" if row["method_name"] == "tubelet_sync" else "#9aa0a6" for row in ordered]

    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    bars = ax.barh(labels, values, color=colors)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.0)
    ax.set_xlabel("TPR at 1% target FPR")
    ax.set_title("Tubelet-Sync achieves the highest fixed-FPR detection rate")
    ax.grid(axis="x", color="#dddddd", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(value + 0.015, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", fontsize=9)
    fig.tight_layout()
    paths = save_figure(fig, root / "figures" / "paper_method_comparison", root)
    plt.close(fig)
    return {"figure_id": "paper_method_comparison", "title": "Overall method comparison", "paths": paths}


def build_sync_gain_figure(root: Path) -> dict[str, Any]:
    """生成显式同步增益图, 聚焦时间同步敏感攻击。"""
    plt, _ = ensure_matplotlib()
    rows = [row for row in read_csv_rows(root / "tables" / "paper_sync_gain_table.csv") if row["attack_name"] in TEMPORAL_ATTACKS]
    rows.sort(key=lambda row: TEMPORAL_ATTACKS.index(row["attack_name"]))
    labels = [ATTACK_LABELS.get(row["attack_name"], row["attack_name"]) for row in rows]
    gains = [safe_float(row["sync_gain_tpr"]) for row in rows]

    fig, ax = plt.subplots(figsize=(6.8, 3.6))
    bars = ax.bar(labels, gains, color="#1f77b4")
    ax.set_ylim(0, max(gains) * 1.25)
    ax.set_ylabel("TPR gain over Tubelet-Only")
    ax.set_title("Explicit synchronization improves temporal robustness")
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(axis="x", rotation=20)
    for bar, value in zip(bars, gains):
        ax.text(bar.get_x() + bar.get_width() / 2, value + 0.015, f"+{value:.3f}", ha="center", va="bottom", fontsize=9)
    fig.tight_layout()
    paths = save_figure(fig, root / "figures" / "paper_sync_gain_temporal_attacks", root)
    plt.close(fig)
    return {"figure_id": "paper_sync_gain_temporal_attacks", "title": "Sync gain on temporal attacks", "paths": paths}


def build_attack_breakdown_heatmap(root: Path) -> dict[str, Any]:
    """生成攻击分解热力图, 展示各方法在每类攻击下的 TPR。"""
    plt, np = ensure_matplotlib()
    rows = read_csv_rows(root / "tables" / "paper_attack_breakdown_table.csv")
    attack_order = [attack for attack in ATTACK_LABELS if any(row["attack_name"] == attack for row in rows)]
    method_order = [method for method in METHOD_ORDER if any(row["method_name"] == method for row in rows)]
    lookup = {(row["method_name"], row["attack_name"]): safe_float(row["tpr_at_target_fpr"]) for row in rows}
    matrix = np.array([[lookup.get((method, attack), 0.0) for attack in attack_order] for method in method_order])

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    image = ax.imshow(matrix, cmap="Blues", vmin=0.0, vmax=1.0, aspect="auto")
    ax.set_xticks(range(len(attack_order)), [ATTACK_LABELS.get(attack, attack) for attack in attack_order], rotation=35, ha="right")
    ax.set_yticks(range(len(method_order)), [METHOD_LABELS.get(method, method) for method in method_order])
    ax.set_title("Attack-wise TPR at 1% target FPR")
    for row_index in range(matrix.shape[0]):
        for col_index in range(matrix.shape[1]):
            value = matrix[row_index, col_index]
            color = "white" if value >= 0.55 else "#222222"
            ax.text(col_index, row_index, f"{value:.2f}", ha="center", va="center", fontsize=7.5, color=color)
    cbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.02)
    cbar.set_label("TPR")
    fig.tight_layout()
    paths = save_figure(fig, root / "figures" / "paper_attack_breakdown_heatmap", root)
    plt.close(fig)
    return {"figure_id": "paper_attack_breakdown_heatmap", "title": "Attack-wise robustness heatmap", "paths": paths}


def build_external_baseline_figure(root: Path) -> dict[str, Any]:
    """生成外部 baseline 比较图, 用于论文 baseline comparison 表达。"""
    plt, _ = ensure_matplotlib()
    rows = read_csv_rows(root / "tables" / "paper_external_baseline_table.csv")
    rows.sort(key=lambda row: safe_float(row["tpr_at_target_fpr"]), reverse=True)
    labels = [METHOD_LABELS.get(row["method_name"], row["method_name"]) for row in rows]
    values = [safe_float(row["tpr_at_target_fpr"]) for row in rows]

    fig, ax = plt.subplots(figsize=(6.0, 3.2))
    bars = ax.barh(labels, values, color="#b0b7c3")
    ax.invert_yaxis()
    ax.set_xlim(0, max(0.15, max(values) * 1.25 if values else 0.15))
    ax.set_xlabel("TPR at 1% target FPR")
    ax.set_title("External video watermark baselines under the aligned protocol")
    ax.grid(axis="x", color="#dddddd", linewidth=0.8)
    ax.spines[["top", "right", "left"]].set_visible(False)
    for bar, value in zip(bars, values):
        ax.text(value + 0.004, bar.get_y() + bar.get_height() / 2, f"{value:.3f}", va="center", fontsize=9)
    fig.tight_layout()
    paths = save_figure(fig, root / "figures" / "paper_external_baseline_comparison", root)
    plt.close(fig)
    return {"figure_id": "paper_external_baseline_comparison", "title": "External baseline comparison", "paths": paths}


def build_paper_figures(root: str | Path) -> dict[str, Any]:
    """生成阶段四投稿图表并写出图表 manifest。"""
    root_path = Path(root)
    figure_entries = [
        build_method_comparison_figure(root_path),
        build_sync_gain_figure(root_path),
        build_attack_breakdown_heatmap(root_path),
        build_external_baseline_figure(root_path),
    ]
    manifest = {
        "figure_count": len(figure_entries),
        "figures": figure_entries,
        "figure_digests": {
            entry["figure_id"]: {
                suffix: compute_file_digest(root_path / path)
                for suffix, path in entry["paths"].items()
            }
            for entry in figure_entries
        },
    }
    manifest_path = root_path / "figures" / "paper_figure_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {**manifest, "manifest_path": manifest_path.as_posix()}
