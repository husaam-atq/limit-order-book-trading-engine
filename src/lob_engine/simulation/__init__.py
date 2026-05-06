"""Synthetic market generation, replay, fill simulation, and backtesting."""

from lob_engine.simulation.backtester import BacktestResult, EventDrivenBacktester
from lob_engine.simulation.fast_replay import FastMarketReplay, FastReplayResult, prepare_fast_events
from lob_engine.simulation.fill_simulator import simulate_child_order_fills
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.simulation.market_replay import MarketReplay, ReplayResult

__all__ = [
    "BacktestResult",
    "EventDrivenBacktester",
    "FastMarketReplay",
    "FastReplayResult",
    "MarketReplay",
    "ReplayResult",
    "SyntheticMarketConfig",
    "generate_market_events",
    "prepare_fast_events",
    "simulate_child_order_fills",
]
