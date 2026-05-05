from pandas.testing import assert_frame_equal

from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.simulation.market_replay import MarketReplay


def test_replay_deterministic():
    events = generate_market_events(SyntheticMarketConfig(num_events=300, seed=123))
    one = MarketReplay().replay(events)
    two = MarketReplay().replay(events)
    assert_frame_equal(
        one.snapshots[["timestamp", "mid_price", "spread", "trade_count"]],
        two.snapshots[["timestamp", "mid_price", "spread", "trade_count"]],
    )


def test_replay_outputs_shapes_and_events():
    events = generate_market_events(SyntheticMarketConfig(num_events=200, seed=3))
    result = MarketReplay().replay(events)
    assert result.processed_events == 200
    assert len(result.snapshots) == 200
    assert {"best_bid", "best_ask", "mid_price", "imbalance"}.issubset(result.snapshots.columns)
