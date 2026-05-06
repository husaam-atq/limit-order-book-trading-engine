from pandas.testing import assert_frame_equal

from lob_engine.simulation.fast_replay import FastMarketReplay, prepare_fast_events
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events


def test_fast_replay_is_deterministic():
    events = prepare_fast_events(generate_market_events(SyntheticMarketConfig(num_events=1_000, seed=23)))
    first = FastMarketReplay(record_trades=True).replay(events, snapshots=True)
    second = FastMarketReplay(record_trades=True).replay(events, snapshots=True)
    assert_frame_equal(first.trades, second.trades, check_dtype=False)
    assert_frame_equal(first.snapshots, second.snapshots, check_dtype=False)
    assert len(first.final_book) == len(second.final_book)


def test_fast_replay_without_trade_records_keeps_counts():
    events = prepare_fast_events(generate_market_events(SyntheticMarketConfig(num_events=1_000, seed=42)))
    result = FastMarketReplay(record_trades=False).replay(events, snapshots=False)
    assert result.trades.empty
    assert result.trade_count == 742
    assert len(result.final_book) == 113
