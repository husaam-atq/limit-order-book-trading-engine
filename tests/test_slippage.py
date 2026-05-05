from lob_engine.analytics.slippage import benchmark_twap, benchmark_vwap, implementation_shortfall, slippage_bps
from lob_engine.analytics.transaction_costs import total_transaction_cost
from lob_engine.core.orders import Side


def test_slippage_bps_buy_and_sell():
    assert slippage_bps(101.0, 100.0, Side.BUY) == 100.0
    assert slippage_bps(99.0, 100.0, Side.SELL) == 100.0


def test_benchmarks():
    assert benchmark_vwap([100, 102], [1, 3]) == 101.5
    assert benchmark_twap([100, 102]) == 101.0


def test_implementation_shortfall_and_costs():
    assert implementation_shortfall(101.0, 100.0, Side.BUY) == 100.0
    costs = total_transaction_cost(1_000, 100.0, spread=0.02, average_daily_volume=1_000_000, volatility=0.02)
    assert costs.total_cost_bps > 0
