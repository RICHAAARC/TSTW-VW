"""
文件用途：构建阶段 0 run manifest。
File purpose: Build the governed stage-0 run manifest.
Module type: General module
"""

from __future__ import annotations

from pathlib import Path

from main.core.digest import compute_file_digest, compute_object_digest, compute_path_collection_digest
from main.core.records import ProtocolOutputPaths
from main.core.schema import CONSTRUCTION_PHASE, PROTOCOL_NAME, validate_run_manifest_record


class ManifestBuilder:
    """功能：构建阶段 0 run manifest 摘要。

    Builder for governed stage-0 run manifests.

    Args:
        None.

    Returns:
        None.
    """

    def build_run_manifest(
        self,
        run_id: str,
        method_config_paths: list[str | Path],
        protocol_config_path: str | Path,
        attack_config_path: str | Path,
        ablation_config_path: str | Path,
        event_score_records: list[dict],
        threshold_records: list[dict],
        output_paths: ProtocolOutputPaths,
    ) -> dict[str, object]:
        """功能：生成受治理的 run manifest。

        Build the governed run manifest for a completed stage-0 run.

        Args:
            run_id: Stable run identifier.
            method_config_paths: Method config file paths.
            protocol_config_path: Protocol config file path.
            attack_config_path: Attack config file path.
            ablation_config_path: Ablation config file path.
            event_score_records: Materialized event score records.
            threshold_records: Materialized threshold records.
            output_paths: Governed output layout.

        Returns:
            A governed run manifest dictionary.
        """
        if not isinstance(run_id, str) or not run_id:
            raise ValueError("run_id must be a non-empty string")
        if not isinstance(output_paths, ProtocolOutputPaths):
            raise TypeError("output_paths must be a ProtocolOutputPaths instance")
        if not event_score_records:
            raise ValueError("event_score_records must not be empty")
        if not threshold_records:
            raise ValueError("threshold_records must not be empty")

        manifest_record = {
            "run_id": run_id,
            "created_at": threshold_records[0]["created_at"],
            "construction_phase": CONSTRUCTION_PHASE,
            "protocol_name": PROTOCOL_NAME,
            "method_config_digest": self._compute_config_collection_digest(method_config_paths),
            "protocol_config_digest": compute_file_digest(protocol_config_path),
            "attack_matrix_digest": compute_file_digest(attack_config_path),
            "ablation_config_digest": compute_file_digest(ablation_config_path),
            "records_digest": compute_object_digest(event_score_records),
            "thresholds_digest": compute_object_digest(threshold_records),
            "tables_digest": compute_path_collection_digest(output_paths.table_paths()),
            "figures_digest": compute_path_collection_digest(output_paths.figure_paths()),
            "placeholder_fields": [
                "trajectory_observation_placeholder",
            ],
            "random_fields": [
                "latent_generation_seed_random",
                "latent_tensor_digest_random",
            ],
        }
        validate_run_manifest_record(manifest_record)
        return manifest_record

    def _compute_config_collection_digest(self, config_paths: list[str | Path]) -> str:
        if not isinstance(config_paths, list) or not config_paths:
            raise ValueError("config_paths must be a non-empty list")
        config_digests = [compute_file_digest(path) for path in sorted(map(str, config_paths))]
        return compute_object_digest(config_digests)