"""Compare TWAP, VWAP, POV, and implementation-shortfall schedules."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lob_engine.core.orders import Side
from lob_engine.execution import ImplementationShortfallExecutor, ParentOrder, POVExecutor, TWAPExecutor, VWAPExecutor


def main() -> None:
    parent = ParentOrder("P-DEMO", Side.BUY, 5_000, 0, 60, arrival_price=100.0)
    prices = [100.00, 100.01, 100.02, 100.00, 99.99, 100.03, 100.04, 100.02, 100.01, 100.00]
    algorithms = [
        TWAPExecutor(parent, slices=10),
        VWAPExecutor(parent, volume_curve=[0.08, 0.09, 0.1, 0.12, 0.14, 0.14, 0.12, 0.1, 0.07, 0.04]),
        POVExecutor(parent, market_volumes=[10_000, 12_000, 8_000, 9_500, 11_000], participation_rate=0.1),
        ImplementationShortfallExecutor(parent, slices=10, urgency=0.7),
    ]
    results = []
    for algo in algorithms:
        result = algo.execute_against_prices(prices)
        summary = {"algorithm": algo.name, **result.metrics}
        results.append(summary)
    frame = pd.DataFrame(results)
    output = ROOT / "reports" / "execution_results.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)
    print(frame.to_string(index=False))
    print(f"\nSaved {output}")


if __name__ == "__main__":
    main()
