from pathlib import Path

import pytest
from pydantic import ValidationError

from src.ingest.manifest import IngestManifest, load_manifest


def test_manifest_rejects_duplicate_ciks() -> None:
    with pytest.raises(ValidationError):
        IngestManifest.model_validate(
            {
                "ciks": [
                    {"cik": "0000319201", "name": "KLA Corp"},
                    {"cik": "319201", "name": "Duplicate KLA"},
                ]
            }
        )


def test_load_manifest_missing_path_exits_cleanly(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.json"
    with pytest.raises(SystemExit) as exc:
        load_manifest(missing)
    assert "Manifest not found" in str(exc.value)


def test_load_manifest_garbage_json_exits_cleanly(tmp_path: Path) -> None:
    bad = tmp_path / "manifest.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(SystemExit) as exc:
        load_manifest(bad)
    assert "not valid JSON" in str(exc.value)
