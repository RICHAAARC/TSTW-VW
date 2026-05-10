"""
文件用途：验证阶段 2 Colab notebook 入口遵循受治理合同。
File purpose: Validate that the stage-two Colab notebook entrypoint follows the governed contract.
Module type: General module
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_PATH = ROOT / "paper_workflow" / "Stage2_Real_Video_VAE_Latent_Probe_Colab.ipynb"
REQUIRED_CELL_TITLES = [
    "00_runtime_mode_and_user_config",
    "01_mount_google_drive",
    "02_clone_or_update_repository",
    "03_install_dependencies",
    "04_verify_repository_contract",
    "05_prepare_drive_directories",
    "06_write_or_select_stage2_configs",
    "07_prepare_or_validate_video_dataset",
    "08_check_gpu_and_runtime",
    "09_load_vae_model",
    "10_run_unit_tests_smoke",
    "11_run_stage2_smoke",
    "12_check_stage2_smoke_outputs",
    "13_run_stage2_formal",
    "14_rebuild_tables_and_reports",
    "15_validate_stage2_results",
    "16_pack_results_to_drive",
    "17_print_final_summary",
]


def _load_notebook() -> dict[str, object]:
    return json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))


def _cell_text(cell: dict[str, object]) -> str:
    source = cell.get("source", [])
    if isinstance(source, list):
        return "".join(str(line) for line in source)
    return str(source)


def test_stage2_notebook_exists_and_uses_governed_entrypoints() -> None:
    """Validate that the stage-two notebook exists and delegates to governed modules.

    Args:
        None.

    Returns:
        None.
    """
    assert NOTEBOOK_PATH.exists()
    notebook = _load_notebook()
    cells = notebook.get("cells", [])
    assert isinstance(cells, list) and cells
    notebook_text = "\n".join(_cell_text(cell) for cell in cells if isinstance(cell, dict))

    title_positions: list[int] = []
    for required_title in REQUIRED_CELL_TITLES:
        matching_index = next(
            index
            for index, cell in enumerate(cells)
            if isinstance(cell, dict) and required_title in _cell_text(cell)
        )
        title_positions.append(matching_index)
    assert title_positions == sorted(title_positions)

    assert "main.protocol.stage2_runner" in notebook_text
    assert "main.analysis.stage2_artifacts" in notebook_text
    assert "main.colab.notebook_result_checker" in notebook_text
    assert "main.colab.drive_packager" in notebook_text
    assert "colab_stage2_runtime_config.json" in notebook_text
    assert "/content/drive/MyDrive/tstw_stage2" in notebook_text
    assert "tables/" not in notebook_text
    assert "thresholds/" not in notebook_text
    assert "D:\\" not in notebook_text
    assert "C:\\Users" not in notebook_text
    assert "/Users/" not in notebook_text


def test_stage2_notebook_cells_use_python_metadata() -> None:
    """Validate that every code cell declares Python language metadata.

    Args:
        None.

    Returns:
        None.
    """
    notebook = _load_notebook()
    cells = notebook.get("cells", [])
    code_cells = [cell for cell in cells if isinstance(cell, dict) and cell.get("cell_type") == "code"]
    assert code_cells
    assert all(cell.get("metadata", {}).get("language") == "python" for cell in code_cells)
