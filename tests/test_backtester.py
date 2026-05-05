from lob_engine.simulation.backtester import EventDrivenBacktester
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.strategies.mean_reversion import MeanReversionStrategy


def test_backtester_runs_and_tracks_inventory():
    events = generate_market_events(SyntheticMarketConfig(num_events=500, seed=15))
    result = EventDrivenBacktester(MeanReversionStrategy(window=20, threshold_bps=2.0), starting_inventory=50).run(
        events
    )
    assert not result.equity_curve.empty
    assert "inventory" in result.equity_curve
    assert (result.equity_curve["inventory"] >= 0).all()


def test_backtester_reproducible_with_seeded_events():
    events = generate_market_events(SyntheticMarketConfig(num_events=500, seed=16))
    one = EventDrivenBacktester(MeanReversionStrategy(window=20, threshold_bps=2.0), starting_inventory=50).run(events)
    two = EventDrivenBacktester(MeanReversionStrategy(window=20, threshold_bps=2.0), starting_inventory=50).run(events)
    assert round(one.metrics["ending_equity"], 8) == round(two.metrics["ending_equity"], 8)
