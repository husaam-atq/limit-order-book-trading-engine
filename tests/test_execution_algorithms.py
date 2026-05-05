from lob_engine.core.orders import Side
from lob_engine.execution import ImplementationShortfallExecutor, ParentOrder, POVExecutor, TWAPExecutor, VWAPExecutor


def test_twap_schedule_sums_to_parent_quantity():
    parent = ParentOrder("P1", Side.BUY, 100, 0, 10, 100.0)
    schedule = TWAPExecutor(parent, slices=6).build_schedule()
    assert schedule["quantity"].sum() == 100


def test_vwap_schedule_follows_volume_curve():
    parent = ParentOrder("P1", Side.BUY, 100, 0, 10, 100.0)
    schedule = VWAPExecutor(parent, volume_curve=[1, 3, 6]).build_schedule()
    assert schedule["quantity"].tolist() == [10, 30, 60]


def test_pov_does_not_exceed_target_participation():
    parent = ParentOrder("P1", Side.SELL, 1_000, 0, 10, 100.0)
    schedule = POVExecutor(parent, market_volumes=[100, 200, 500], participation_rate=0.1).build_schedule()
    assert (schedule["actual_participation"] <= 0.1000001).all()


def test_implementation_shortfall_front_loads_with_urgency():
    parent = ParentOrder("P1", Side.BUY, 100, 0, 10, 100.0)
    schedule = ImplementationShortfallExecutor(parent, slices=5, urgency=0.9).build_schedule()
    assert schedule["quantity"].iloc[0] > schedule["quantity"].iloc[-1]
