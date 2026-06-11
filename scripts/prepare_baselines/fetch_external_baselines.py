"""拉取阶段三外部 baseline 的上游代码快照。"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.baseline_comparison_gate.source_intake import (
    REQUIRED_BASELINE_NAMES,
    load_all_source_manifests,
    validate_source_manifest,
)

DEFAULT_CONFIG_DIR = ROOT / "configs" / "baselines"
DEFAULT_EXTERNAL_ROOT = ROOT / "external_baselines"


def run_command(command: list[str], cwd: Path | None = None, dry_run: bool = False) -> None:
    """执行外部命令, dry-run 时只打印命令。"""
    printable = " ".join(command)
    if dry_run:
        print(f"[dry-run] {printable}")
        return
    subprocess.run(command, cwd=cwd, check=True)


def ensure_baseline_source(
    baseline_name: str,
    manifest: dict[str, Any],
    external_root: Path,
    dry_run: bool = False,
) -> Path:
    """将一个 baseline 的上游仓库固定到 manifest 记录的 commit。"""
    violations = validate_source_manifest(manifest)
    if violations:
        raise ValueError(f"{baseline_name} source manifest is invalid: {violations}")

    baseline_root = external_root / baseline_name
    upstream_root = baseline_root / "upstream"
    repository_url = manifest["upstream_repository_url"]
    upstream_commit = manifest["upstream_commit"]

    if not upstream_root.exists():
        baseline_root.mkdir(parents=True, exist_ok=True)
        run_command(
            ["git", "clone", "--filter=blob:none", "--depth", "1", repository_url, str(upstream_root)],
            dry_run=dry_run,
        )
    else:
        run_command(["git", "fetch", "--depth", "1", "origin", upstream_commit], cwd=upstream_root, dry_run=dry_run)

    run_command(["git", "checkout", upstream_commit], cwd=upstream_root, dry_run=dry_run)
    return upstream_root


def build_fetch_plan(config_dir: Path, external_root: Path) -> dict[str, Any]:
    """构建不执行网络操作的 baseline 拉取计划。"""
    manifests = load_all_source_manifests(config_dir)
    return {
        "project_stage": "baseline_comparison_gate",
        "external_root": str(external_root),
        "baselines": [
            {
                "baseline_name": baseline_name,
                "repository_url": manifests[baseline_name]["upstream_repository_url"],
                "upstream_commit": manifests[baseline_name]["upstream_commit"],
                "target_path": str(external_root / baseline_name / "upstream"),
            }
            for baseline_name in REQUIRED_BASELINE_NAMES
        ],
    }


def main(argv: list[str] | None = None) -> None:
    """命令行入口, 用于本地或 Colab 冷启动时拉取 baseline 源码。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config-dir", type=Path, default=DEFAULT_CONFIG_DIR)
    parser.add_argument("--external-root", type=Path, default=DEFAULT_EXTERNAL_ROOT)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--print-plan", action="store_true")
    args = parser.parse_args(argv)

    plan = build_fetch_plan(args.config_dir, args.external_root)
    if args.print_plan:
        print(json.dumps(plan, indent=2, ensure_ascii=False))

    manifests = load_all_source_manifests(args.config_dir)
    for baseline_name in REQUIRED_BASELINE_NAMES:
        ensure_baseline_source(
            baseline_name=baseline_name,
            manifest=manifests[baseline_name],
            external_root=args.external_root,
            dry_run=args.dry_run,
        )


if __name__ == "__main__":
    main()
