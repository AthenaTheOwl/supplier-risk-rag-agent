import pytest
from pydantic import ValidationError

from src.ingest.manifest import IngestManifest


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
