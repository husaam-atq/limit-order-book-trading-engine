from pandas.testing import assert_frame_equal

from lob_engine.simulation.fast_replay import FastMarketReplay, prepare_fast_events
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.simulation.market_replay import MarketReplay


def test_fast_engine_trade_records_match_reference():
    events = generate_market_events(SyntheticMarketConfig(num_events=1_000, seed=7))
    reference = MarketReplay().replay(events)
    fast = FastMarketReplay(record_trades=True).replay(prepare_fast_events(events), snapshots=True)
    columns = ["trade_id", "timestamp", "aggressor_order_id", "passive_order_id", "side", "price", "quantity"]
    assert_frame_equal(
        reference.trades[columns].reset_index(drop=True),
        fast.trades[columns].reset_index(drop=True),
        check_dtype=False,
        atol=1e-12,
        rtol=1e-12,
    )


def test_fast_engine_final_book_matches_reference():
    events = generate_market_events(SyntheticMarketConfig(num_events=2_000, seed=19))
    reference = MarketReplay().replay(events)
    fast = FastMarketReplay(record_trades=True).replay(prepare_fast_events(events), snapshots=False)
    assert reference.final_book.best_bid() == fast.final_book.best_bid()
    assert reference.final_book.best_ask() == fast.final_book.best_ask()
    assert len(reference.final_book) == len(fast.final_book)

    for side in ("buy", "sell"):
        ref_depth = reference.final_book.total_depth(side, levels=10)
        fast_depth = fast.final_book.total_depth(1 if side == "buy" else -1, levels=10)
        assert ref_depth == fast_depth
