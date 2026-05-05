"""Run a simple strategy backtest on synthetic market events."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lob_engine.simulation.backtester import EventDrivenBacktester
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.strategies.mean_reversion import MeanReversionStrategy


def main() -> None:
    events = generate_market_events(SyntheticMarketConfig(num_events=3_000, seed=101))
    backtester = EventDrivenBacktester(
        MeanReversionStrategy(window=25, threshold_bps=2.0, order_size=10),
        starting_inventory=50,
        allow_short=False,
    )
    result = backtester.run(events)
    output = ROOT / "reports" / "strategy_backtest_equity.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    result.equity_curve.to_csv(output, index=False)
    print("Backtest metrics")
    for key, value in result.metrics.items():
        print(f"{key}: {value}")
    print(f"\nSaved {output}")


if __name__ == "__main__":
    main()
