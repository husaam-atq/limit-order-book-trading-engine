"""I/O helpers with paths relative to the repository root."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def project_root() -> Path:
    """Return the repository root path."""

    return Path(__file__).resolve().parents[3]


def data_path(name: str) -> Path:
    """Return a path under the data directory."""

    return project_root() / "data" / name


def reports_path(name: str) -> Path:
    """Return a path under the reports directory."""

    return project_root() / "reports" / name


def read_events(path: str | Path) -> pd.DataFrame:
    """Read a market events CSV."""

    return pd.read_csv(path)


def write_dataframe(frame: pd.DataFrame, path: str | Path) -> Path:
    """Write a DataFrame to CSV after creating parent directories."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    return output
