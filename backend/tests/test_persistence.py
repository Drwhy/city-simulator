import pytest
from app.simulation.persistence import SAVE_VERSION, read_snapshot, validate_save_version, write_snapshot

def test_snapshot_storage_is_atomic_and_unicode_safe(tmp_path):
    path=tmp_path/"city.json"; payload={"version":SAVE_VERSION,"label":"Résidence"}
    assert write_snapshot(path,payload)==path
    assert read_snapshot(path)==payload
    assert not path.with_suffix(".json.tmp").exists()

def test_persistence_rejects_missing_and_old_versions(tmp_path):
    with pytest.raises(FileNotFoundError): read_snapshot(tmp_path/"missing.json")
    with pytest.raises(ValueError): validate_save_version({"version":SAVE_VERSION-1})
