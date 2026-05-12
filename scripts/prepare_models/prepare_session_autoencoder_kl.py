"""
File purpose: Provide the governed session-only AutoencoderKL preparation entrypoint.
Module type: General module
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
from typing import Any


def _clear_directory(directory_path: Path) -> None:
    """Remove existing session-model contents before copying a local source tree."""
    for child_path in directory_path.iterdir():
        if child_path.is_dir():
            shutil.rmtree(child_path)
            continue
        child_path.unlink()


def prepare_session_autoencoder_kl(
    model_id: str,
    local_model_root: str | Path,
    *,
    revision: str = "main",
    session_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    """Resolve a session-only AutoencoderKL model checkout.

    Args:
        model_id: Hugging Face repo id or a local model directory path.
        local_model_root: Session-local checkout directory.
        revision: Optional model revision.
        session_manifest_path: Optional manifest output path.

    Returns:
        A session-model manifest payload.
    """
    destination_root = Path(local_model_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    source_path = Path(model_id)
    if source_path.exists():
        resolved_source_path = source_path.resolve()
        resolved_destination_root = destination_root.resolve()
        if resolved_source_path.is_file():
            raise ValueError("model_id local_path must be a directory")
        if resolved_source_path != resolved_destination_root:
            _clear_directory(destination_root)
            shutil.copytree(
                resolved_source_path,
                destination_root,
                dirs_exist_ok=True,
            )
            source_kind = "local_path_copied_to_session"
        else:
            source_kind = "local_path_session_root"
        resolved_model_path = resolved_destination_root
    else:
        from huggingface_hub import snapshot_download

        resolved_model_path = Path(
            snapshot_download(
                repo_id=model_id,
                revision=revision,
                local_dir=str(destination_root),
                local_dir_use_symlinks=False,
            )
        )
        source_kind = "snapshot_download"

    manifest_payload = {
        "model_policy": "session_only_no_drive_model_storage",
        "models": [
            {
                "model_role": "stage2_vae",
                "source_kind": source_kind,
                "repo_id": model_id,
                "revision": revision,
                "local_path": str(resolved_model_path),
                "load_api": "AutoencoderKL.from_pretrained",
                "saved_to_drive": False,
                "included_in_result_package": False,
            }
        ],
    }
    if session_manifest_path is not None:
        Path(session_manifest_path).write_text(
            json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    return manifest_payload


def main(argv: list[str] | None = None) -> int:
    """Run the governed session-model preparation CLI.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = argparse.ArgumentParser(
        description="Prepare a session-only AutoencoderKL checkout.",
    )
    parser.add_argument("--model-id", required=True)
    parser.add_argument("--local-model-root", required=True)
    parser.add_argument("--revision", default="main")
    parser.add_argument("--session-manifest-path", default="")
    args = parser.parse_args(argv)
    payload = prepare_session_autoencoder_kl(
        model_id=args.model_id,
        local_model_root=args.local_model_root,
        revision=args.revision,
        session_manifest_path=args.session_manifest_path or None,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
