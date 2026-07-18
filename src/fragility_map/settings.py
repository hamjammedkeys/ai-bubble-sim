from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectPaths:
    root: Path
    data_dir: Path
    raw_dir: Path
    processed_dir: Path
    db_path: Path


def get_paths(root: Path | None = None) -> ProjectPaths:
    project_root = root or Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    return ProjectPaths(
        root=project_root,
        data_dir=data_dir,
        raw_dir=data_dir / "raw",
        processed_dir=data_dir / "processed",
        db_path=data_dir / "ai_fragility.duckdb",
    )
