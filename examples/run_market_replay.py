"""Generate and replay synthetic market events."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.simulation.market_replay import MarketReplay


def main() -> None:
    events = generate_market_events(SyntheticMarketConfig(num_events=5_000, seed=42))
    data_path = ROOT / "data" / "sample_market_events.csv"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(data_path, index=False)
    result = MarketReplay().replay(events)
    snapshots_path = ROOT / "reports" / "market_replay_snapshots.csv"
    trades_path = ROOT / "reports" / "market_replay_trades.csv"
    snapshots_path.parent.mkdir(parents=True, exist_ok=True)
    result.snapshots.to_csv(snapshots_path, index=False)
    result.trades.to_csv(trades_path, index=False)
    print(f"Processed events: {result.processed_events:,}")
    print(f"Trades: {len(result.trades):,}")
    print(f"Final resting orders: {len(result.final_book):,}")
    print(result.snapshots.tail(5).to_string(index=False))


if __name__ == "__main__":
    main()
