"""Deterministic validation checks and report generation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pandas.testing import assert_frame_equal

from lob_engine.analytics.microstructure import book_metrics, order_book_imbalance, weighted_mid_price
from lob_engine.analytics.slippage import implementation_shortfall, slippage_bps
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import CancelRequest, Order, OrderStatus, OrderType, Side
from lob_engine.execution import ImplementationShortfallExecutor, ParentOrder, POVExecutor, TWAPExecutor, VWAPExecutor
from lob_engine.simulation.backtester import EventDrivenBacktester
from lob_engine.simulation.fast_replay import FastMarketReplay, prepare_fast_events
from lob_engine.simulation.market_generator import (
    SyntheticMarketConfig,
    generate_market_events,
    write_sample_market_events,
)
from lob_engine.simulation.market_replay import MarketReplay
from lob_engine.strategies.mean_reversion import MeanReversionStrategy
from lob_engine.utils.io import project_root
from lob_engine.utils.performance import (
    benchmark_event_throughput,
    benchmark_target_status,
    generate_profile_report,
    write_performance_report,
)


def run_validation_suite(include_performance: bool = True) -> pd.DataFrame:
    """Run deterministic validation checks and return pass/fail rows."""

    checks = [
        _check_price_time_priority,
        _check_price_priority,
        _check_market_order_matching,
        _check_limit_order_crossing,
        _check_partial_fills,
        _check_cancel_order,
        _check_book_metrics,
        _check_replay_determinism,
        _check_fast_engine_parity,
        _check_fast_replay_determinism,
        _check_execution_algorithms,
        _check_transaction_cost_analytics,
        _check_backtester_sanity,
    ]
    rows = []
    for check in checks:
        name, passed, detail = check()
        rows.append({"check": name, "passed": bool(passed), "detail": detail})
    if include_performance:
        try:
            benchmark = benchmark_event_throughput(event_counts=(1_000,), seed=42)
            throughput = benchmark[
                (benchmark["implementation_path"] == "optimised") & (benchmark["benchmark_mode"] == "core_matching")
            ]["events_per_second"].iloc[0]
            rows.append(
                {
                    "check": "Performance benchmark",
                    "passed": True,
                    "detail": f"Processed 1,000 events at {throughput:,.0f} events/sec.",
                }
            )
        except Exception as exc:
            rows.append({"check": "Performance benchmark", "passed": False, "detail": str(exc)})
    return pd.DataFrame(rows)


def generate_validation_report(
    output_dir: str | Path | None = None,
    benchmark_event_counts: tuple[int, ...] = (1_000, 10_000, 100_000, 500_000, 1_000_000),
) -> dict[str, Path | pd.DataFrame]:
    """Generate validation, benchmark, execution, sample-data, and performance artifacts."""

    root = project_root()
    out = Path(output_dir) if output_dir is not None else root / "reports"
    out.mkdir(parents=True, exist_ok=True)
    data_dir = root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    sample_events = write_sample_market_events(data_dir / "sample_market_events.csv", num_events=5_000, seed=42)
    execution_results = _sample_execution_results()
    execution_results.to_csv(out / "execution_results.csv", index=False)
    schedule = execution_results[["algorithm", "parent_order_id", "child_order_id", "timestamp", "side", "quantity"]]
    schedule.to_csv(data_dir / "sample_execution_schedule.csv", index=False)

    validation = run_validation_suite(include_performance=True)
    previous_baseline = _read_previous_baseline(out / "benchmark_results.csv")
    benchmark = benchmark_event_throughput(
        event_counts=benchmark_event_counts, seed=42, output_path=out / "benchmark_results.csv"
    )
    profile_path = generate_profile_report(out / "profile_report.md", event_count=10_000, seed=42)
    profile_summary = "- Full profiling details are available in `reports/profile_report.md`."
    write_performance_report(
        benchmark,
        out / "performance_report.md",
        profile_summary=profile_summary,
        previous_baseline_events_per_second=previous_baseline,
    )
    report_path = out / "validation_report.md"
    _write_validation_markdown(validation, benchmark, sample_events, report_path)
    return {
        "validation": validation,
        "benchmark": benchmark,
        "validation_report": report_path,
        "benchmark_results": out / "benchmark_results.csv",
        "performance_report": out / "performance_report.md",
        "profile_report": profile_path,
        "execution_results": out / "execution_results.csv",
    }


def _write_validation_markdown(
    validation: pd.DataFrame, benchmark: pd.DataFrame, sample_events: pd.DataFrame, path: Path
) -> None:
    passed = int(validation["passed"].sum())
    total = int(len(validation))
    lines = [
        "# Validation Report",
        "",
        f"Deterministic validation checks passed: **{passed}/{total}**.",
        "",
        "The validation suite exercises price-time priority, price priority, market and limit matching, partial fills, cancellations, microstructure metrics, deterministic replay, execution schedules, transaction cost calculations, backtester accounting, and benchmark execution.",
        "",
        "## Validation Checks",
        "",
        _markdown_table(validation),
        "",
        "## Benchmark Summary",
        "",
        _markdown_table(_benchmark_summary_table(benchmark)),
        "",
        "## Benchmark Targets",
        "",
        _markdown_table(pd.DataFrame([benchmark_target_status(benchmark)])),
        "",
        "## Full Benchmark Results",
        "",
        _markdown_table(benchmark),
        "",
        "## Sample Data",
        "",
        f"- Sample market events: {len(sample_events):,} rows",
        "- Event data is synthetic and reproducible from a fixed seed.",
        "- Synthetic results are useful for infrastructure validation, not evidence of live trading performance.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _seed_book(engine: MatchingEngine) -> None:
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 10, 99.90, timestamp=1))
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 10, 100.10, timestamp=2))


def _markdown_table(frame: pd.DataFrame) -> str:
    """Render a small Markdown table without optional dependencies."""

    if frame.empty:
        return "_No rows._"
    columns = list(frame.columns)
    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
    for _, row in frame.iterrows():
        values = []
        for column in columns:
            value = row[column]
            if isinstance(value, float) and value.is_integer():
                values.append(str(int(value)))
            elif isinstance(value, float):
                values.append(f"{value:.3f}")
            else:
                values.append(str(value))
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _read_previous_baseline(path: Path) -> float | None:
    """Read a previous 100k reference baseline if a benchmark file already exists."""

    if not path.exists():
        return None
    try:
        previous = pd.read_csv(path)
        if "implementation_path" in previous:
            row = previous[
                (previous["implementation_path"] == "reference")
                & (previous["benchmark_mode"] == "core_matching")
                & (previous["event_count"] == 100_000)
            ]
        else:
            row = previous[previous["event_count"] == 100_000]
        if row.empty:
            return None
        return float(row["events_per_second"].iloc[0])
    except Exception:
        return None


def _benchmark_summary_table(benchmark: pd.DataFrame) -> pd.DataFrame:
    """Return compact reference vs optimised summary at 100k events."""

    rows = []
    for mode in ("core_matching", "replay_minimal", "full_system", "analytics"):
        mode_rows = benchmark[(benchmark["benchmark_mode"] == mode) & (benchmark["event_count"] == 100_000)]
        ref = mode_rows[mode_rows["implementation_path"] == "reference"]
        opt = mode_rows[mode_rows["implementation_path"] == "optimised"]
        if ref.empty and opt.empty:
            continue
        ref_eps = None if ref.empty else float(ref["events_per_second"].iloc[0])
        opt_eps = None if opt.empty else float(opt["events_per_second"].iloc[0])
        rows.append(
            {
                "benchmark_mode": mode,
                "events": 100_000,
                "reference_events_per_second": ref_eps,
                "optimised_events_per_second": opt_eps,
                "improvement_multiple": None if ref_eps in (None, 0) or opt_eps is None else opt_eps / ref_eps,
            }
        )
    return pd.DataFrame(rows)


def _check_price_time_priority() -> tuple[str, bool, str]:
    engine = MatchingEngine()
    engine.process_order(Order("A-old", Side.SELL, OrderType.LIMIT, 10, 101.0, timestamp=1))
    engine.process_order(Order("A-new", Side.SELL, OrderType.LIMIT, 10, 101.0, timestamp=2))
    result = engine.process_order(Order("M-buy", Side.BUY, OrderType.MARKET, 15, timestamp=3))
    passive_ids = [trade.passive_order_id for trade in result.trades]
    quantities = [trade.quantity for trade in result.trades]
    passed = passive_ids == ["A-old", "A-new"] and quantities == [10, 5]
    return "Price-time priority", passed, f"Passive fill order: {passive_ids}, quantities: {quantities}."


def _check_price_priority() -> tuple[str, bool, str]:
    engine = MatchingEngine()
    engine.process_order(Order("A-worse", Side.SELL, OrderType.LIMIT, 10, 102.0, timestamp=1))
    engine.process_order(Order("A-better", Side.SELL, OrderType.LIMIT, 10, 101.0, timestamp=2))
    result = engine.process_order(Order("M-buy", Side.BUY, OrderType.MARKET, 10, timestamp=3))
    prices = [trade.price for trade in result.trades]
    passed = prices == [101.0] and result.trades[0].passive_order_id == "A-better"
    return "Price priority", passed, f"First execution price: {prices}."


def _check_market_order_matching() -> tuple[str, bool, str]:
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 10, 100.01, timestamp=1))
    engine.process_order(Order("A2", Side.SELL, OrderType.LIMIT, 10, 100.02, timestamp=2))
    buy = engine.process_order(Order("MB", Side.BUY, OrderType.MARKET, 15, timestamp=3))
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 10, 99.99, timestamp=4))
    engine.process_order(Order("B2", Side.BUY, OrderType.LIMIT, 10, 99.98, timestamp=5))
    sell = engine.process_order(Order("MS", Side.SELL, OrderType.MARKET, 12, timestamp=6))
    passed = [t.price for t in buy.trades] == [100.01, 100.02] and [t.quantity for t in sell.trades] == [10, 2]
    return "Market order matching", passed, "Market buy consumed asks upward; market sell consumed bids downward."


def _check_limit_order_crossing() -> tuple[str, bool, str]:
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 10, 100.10, timestamp=1))
    crossed = engine.process_order(Order("LB", Side.BUY, OrderType.LIMIT, 5, 100.10, timestamp=2))
    rested = engine.process_order(Order("LB2", Side.BUY, OrderType.LIMIT, 5, 99.90, timestamp=3))
    passed = (
        crossed.trade_count == 1 and engine.book.get_order("LB2") is not None and rested.order.status is OrderStatus.NEW
    )
    return "Limit order crossing", passed, "Crossing limit executed; non-crossing limit rested."


def _check_partial_fills() -> tuple[str, bool, str]:
    engine = MatchingEngine()
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 5, 100.00, timestamp=1))
    market = engine.process_order(Order("MB", Side.BUY, OrderType.MARKET, 8, timestamp=2))
    engine = MatchingEngine()
    engine.process_order(Order("A2", Side.SELL, OrderType.LIMIT, 5, 100.00, timestamp=1))
    limit = engine.process_order(Order("LB", Side.BUY, OrderType.LIMIT, 8, 101.00, timestamp=2))
    passed = (
        market.order.filled_quantity == 5
        and market.order.remaining_quantity == 3
        and market.order.status is OrderStatus.CANCELLED
        and limit.order.filled_quantity == 5
        and limit.order.remaining_quantity == 3
        and engine.book.get_order("LB") is not None
    )
    return "Partial fills", passed, "Market remainder cancelled; crossing limit remainder rested."


def _check_cancel_order() -> tuple[str, bool, str]:
    engine = MatchingEngine()
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 10, 99.90, timestamp=1))
    cancel = engine.process_cancel(CancelRequest("C1", timestamp=2, target_order_id="B1"))
    missing = engine.process_cancel(CancelRequest("C2", timestamp=3, target_order_id="missing"))
    passed = cancel.accepted and engine.book.get_order("B1") is None and not missing.accepted
    return "Cancel order", passed, "Existing order removed; unknown cancel rejected with message."


def _check_book_metrics() -> tuple[str, bool, str]:
    engine = MatchingEngine()
    engine.process_order(Order("B1", Side.BUY, OrderType.LIMIT, 100, 99.90, timestamp=1))
    engine.process_order(Order("B2", Side.BUY, OrderType.LIMIT, 50, 99.80, timestamp=2))
    engine.process_order(Order("A1", Side.SELL, OrderType.LIMIT, 75, 100.10, timestamp=3))
    metrics = book_metrics(engine.book, levels=1)
    imbalance = order_book_imbalance(engine.book, levels=1)
    weighted_mid = weighted_mid_price(engine.book)
    passed = (
        metrics["best_bid"] == 99.90
        and metrics["best_ask"] == 100.10
        and round(metrics["spread"], 2) == 0.20
        and round(metrics["mid_price"], 2) == 100.00
        and round(imbalance, 6) == round((100 - 75) / 175, 6)
        and weighted_mid is not None
    )
    return "Book metrics", passed, f"Top-level imbalance {imbalance:.6f}, weighted mid {weighted_mid:.4f}."


def _check_replay_determinism() -> tuple[str, bool, str]:
    events = generate_market_events(SyntheticMarketConfig(num_events=500, seed=7))
    replay_one = MarketReplay().replay(events)
    replay_two = MarketReplay().replay(events)
    snapshot_cols = ["timestamp", "best_bid", "best_ask", "mid_price", "spread", "imbalance", "trade_count"]
    trade_cols = ["trade_id", "timestamp", "aggressor_order_id", "passive_order_id", "side", "price", "quantity"]
    assert_frame_equal(replay_one.snapshots[snapshot_cols], replay_two.snapshots[snapshot_cols], check_dtype=False)
    if not replay_one.trades.empty:
        assert_frame_equal(replay_one.trades[trade_cols], replay_two.trades[trade_cols], check_dtype=False)
    return "Replay determinism", True, f"Replay produced {len(replay_one.trades)} identical trades across two runs."


def _check_fast_engine_parity() -> tuple[str, bool, str]:
    events = generate_market_events(SyntheticMarketConfig(num_events=1_000, seed=7))
    reference = MarketReplay().replay(events)
    fast = FastMarketReplay(record_trades=True).replay(prepare_fast_events(events), snapshots=True)

    trade_cols = ["trade_id", "timestamp", "aggressor_order_id", "passive_order_id", "side", "price", "quantity"]
    assert_frame_equal(
        reference.trades[trade_cols].reset_index(drop=True),
        fast.trades[trade_cols].reset_index(drop=True),
        check_dtype=False,
        atol=1e-12,
        rtol=1e-12,
    )
    final_reference = _reference_live_orders(reference.final_book)
    final_fast = _fast_live_orders(fast.final_book)
    assert_frame_equal(final_reference, final_fast, check_dtype=False, atol=1e-12, rtol=1e-12)
    passed = (
        reference.final_book.best_bid() == fast.final_book.best_bid()
        and reference.final_book.best_ask() == fast.final_book.best_ask()
        and len(reference.final_book) == len(fast.final_book)
    )
    return (
        "Reference vs optimised parity",
        passed,
        f"Matched {len(fast.trades)} trades and {len(fast.final_book)} live orders.",
    )


def _check_fast_replay_determinism() -> tuple[str, bool, str]:
    events = generate_market_events(SyntheticMarketConfig(num_events=1_000, seed=23))
    prepared = prepare_fast_events(events)
    first = FastMarketReplay(record_trades=True).replay(prepared, snapshots=True)
    second = FastMarketReplay(record_trades=True).replay(prepared, snapshots=True)
    trade_cols = ["trade_id", "timestamp", "aggressor_order_id", "passive_order_id", "side", "price", "quantity"]
    assert_frame_equal(first.trades[trade_cols], second.trades[trade_cols], check_dtype=False)
    assert_frame_equal(first.snapshots, second.snapshots, check_dtype=False)
    return "Optimised replay determinism", True, f"Fast replay produced {len(first.trades)} identical trades."


def _reference_live_orders(book) -> pd.DataFrame:
    rows = []
    for order in book.iter_orders():
        rows.append(
            {
                "order_id": order.order_id,
                "side": order.side.value,
                "price": order.price,
                "remaining_quantity": order.remaining_quantity,
                "status": order.status.value,
            }
        )
    return pd.DataFrame(rows).sort_values("order_id").reset_index(drop=True)


def _fast_live_orders(book) -> pd.DataFrame:
    rows = []
    for order_id, order in book.order_lookup.items():
        status = "new" if order.filled_quantity == 0 else "partially_filled"
        rows.append(
            {
                "order_id": order_id,
                "side": "buy" if order.side == 1 else "sell",
                "price": order.price_ticks * book.tick_size,
                "remaining_quantity": order.remaining,
                "status": status,
            }
        )
    return pd.DataFrame(rows).sort_values("order_id").reset_index(drop=True)


def _check_execution_algorithms() -> tuple[str, bool, str]:
    parent = ParentOrder("P1", Side.BUY, 1_000, 0, 10, arrival_price=100.0)
    twap = TWAPExecutor(parent, slices=5).build_schedule()
    vwap = VWAPExecutor(parent, volume_curve=[1, 2, 3, 4]).build_schedule()
    pov = POVExecutor(parent, market_volumes=[1_000, 2_000, 1_500], participation_rate=0.1).build_schedule()
    is_sched = ImplementationShortfallExecutor(parent, slices=5, urgency=0.8).build_schedule()
    passed = (
        twap["quantity"].sum() == parent.quantity
        and vwap["quantity"].iloc[-1] > vwap["quantity"].iloc[0]
        and (pov["actual_participation"] <= 0.1000001).all()
        and is_sched["quantity"].iloc[0] > is_sched["quantity"].iloc[-1]
        and round(implementation_shortfall(101.0, 100.0, Side.BUY), 6) == 100.0
    )
    return "Execution algorithms", passed, "TWAP sums, VWAP curve, POV cap, and shortfall calculation validated."


def _check_transaction_cost_analytics() -> tuple[str, bool, str]:
    buy_slip = slippage_bps(101.0, 100.0, Side.BUY)
    sell_slip = slippage_bps(99.0, 100.0, Side.SELL)
    passed = round(buy_slip, 6) == 100.0 and round(sell_slip, 6) == 100.0
    return "Transaction cost analytics", passed, f"Buy slippage {buy_slip:.1f} bps; sell slippage {sell_slip:.1f} bps."


def _check_backtester_sanity() -> tuple[str, bool, str]:
    events = generate_market_events(SyntheticMarketConfig(num_events=600, seed=11))
    result_one = EventDrivenBacktester(MeanReversionStrategy(window=20, threshold_bps=1.5), starting_inventory=50).run(
        events
    )
    result_two = EventDrivenBacktester(MeanReversionStrategy(window=20, threshold_bps=1.5), starting_inventory=50).run(
        events
    )
    inventory_ok = (result_one.equity_curve["inventory"] >= 0).all()
    reproducible = round(result_one.metrics["ending_equity"], 8) == round(result_two.metrics["ending_equity"], 8)
    finite_equity = result_one.equity_curve["equity"].notna().all()
    passed = bool(inventory_ok and reproducible and finite_equity)
    return (
        "Backtester sanity checks",
        passed,
        f"Ending equity {result_one.metrics['ending_equity']:.2f}; reproducible={reproducible}.",
    )


def _sample_execution_results() -> pd.DataFrame:
    parent = ParentOrder("P-SAMPLE", Side.BUY, 2_000, 0, 30, arrival_price=100.0)
    prices = [100.00, 100.01, 100.02, 100.00, 99.99, 100.03, 100.04, 100.02, 100.01, 100.00]
    rows = []
    algorithms = [
        TWAPExecutor(parent, slices=10),
        VWAPExecutor(parent, volume_curve=[0.08, 0.09, 0.1, 0.12, 0.14, 0.14, 0.12, 0.1, 0.07, 0.04]),
        POVExecutor(parent, market_volumes=[2_000] * 10, participation_rate=0.1),
        ImplementationShortfallExecutor(parent, slices=10, urgency=0.7),
    ]
    for algo in algorithms:
        result = algo.execute_against_prices(prices)
        fills = result.fills.copy()
        for key, value in result.metrics.items():
            fills[key] = value
        rows.append(fills)
    return pd.concat(rows, ignore_index=True)
