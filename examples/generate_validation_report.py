"""Generate validation and benchmark reports."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lob_engine.utils.validation import generate_validation_report


def main() -> None:
    artifacts = generate_validation_report()
    validation = artifacts["validation"]
    benchmark = artifacts["benchmark"]
    print(validation.to_string(index=False))
    print("\nBenchmark results")
    print(benchmark.to_string(index=False))
    print("\nArtifacts")
    for key, value in artifacts.items():
        if key not in {"validation", "benchmark"}:
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
