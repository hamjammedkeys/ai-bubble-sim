from pathlib import Path

from fragility_map.settings import get_paths


def test_get_paths_uses_project_root(tmp_path: Path) -> None:
    paths = get_paths(tmp_path)

    assert paths.root == tmp_path
    assert paths.data_dir == tmp_path / "data"
    assert paths.raw_dir == tmp_path / "data" / "raw"
    assert paths.processed_dir == tmp_path / "data" / "processed"
    assert paths.db_path == tmp_path / "data" / "ai_fragility.duckdb"
