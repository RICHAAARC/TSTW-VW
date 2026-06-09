"""
文件用途：提供 trajectory-aware sampling probe 的最小受治理入口。
File purpose: Provide the minimal governed entrypoints for the trajectory-aware sampling probe.
Module type: Package module
"""

from experiments.trajectory_aware_sampling_probe.readiness_audit import (
    build_trajectory_aware_sampling_readiness_decision,
)

__all__ = ["build_trajectory_aware_sampling_readiness_decision"]
