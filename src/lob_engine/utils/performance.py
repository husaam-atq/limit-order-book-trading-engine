"""Performance benchmark and profiling utilities."""

from __future__ import annotations

import cProfile
import io
import pstats
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

from lob_engine.analytics.microstructure import book_metrics, rolling_order_flow_imbalance, rolling_volatility
from lob_engine.core.events import EventType, MarketEvent
from lob_engine.core.fast_matching_engine import FastMatchingEngine
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import CancelRequest, ModifyRequest, Order, OrderType
from lob_engine.simulation.fast_replay import FastEvent, FastMarketReplay, prepare_fast_events
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.simulation.market_replay import MarketReplay
from lob_engine.utils.acceleration import NUMBA_AVAILABLE, latency_summary_us

BENCHMARK_MODES = ("core_matching", "replay_minimal", "full_system", "analytics")
REFERENCE_MAX_EVENTS = 100_000
FULL_SYSTEM_MAX_EVENTS = 100_000
REFERENCE_FULL_SYSTEM_MAX_EVENTS = 10_000


@dataclass(frozen=True)
class ReferenceAction:
    """Prepared reference event used to keep pandas out of core benchmarks."""

    timestamp: float
    event_type: str
    order_id: str
    side: str | None
    quantity: int
    price: float | None
    target_order_id: str | None


def benchmark_event_throughput(
    event_counts: tuple[int, ...] = (1_000, 10_000, 100_000, 500_000, 1_000_000),
    seed: int = 42,
    output_path: str | Path | None = None,
    include_reference: bool = True,
) -> pd.DataFrame:
    """Benchmark reference and optimised paths across separate benchmark modes."""

    rows: list[dict[str, object]] = []
    for event_count in event_counts:
        events = generate_market_events(SyntheticMarketConfig(num_events=event_count, seed=seed))
        fast_events = prepare_fast_events(events)
        reference_actions = _prepare_reference_actions(events)

        if include_reference and event_count <= REFERENCE_MAX_EVENTS:
            rows.append(_benchmark_reference_core(reference_actions, event_count))
            rows.append(_benchmark_reference_replay_minimal(events, event_count))

        if include_reference and event_count <= REFERENCE_FULL_SYSTEM_MAX_EVENTS:
            rows.append(_benchmark_reference_full_system(events, event_count))

        rows.append(_benchmark_optimised_core(fast_events, event_count))
        rows.append(_benchmark_optimised_replay_minimal(fast_events, event_count))

        if event_count <= FULL_SYSTEM_MAX_EVENTS:
            rows.append(_benchmark_optimised_full_system(fast_events, event_count))
            rows.append(_benchmark_analytics(events, event_count))

    result = pd.DataFrame(rows)
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output, index=False)
    return result


def write_performance_report(
    results: pd.DataFrame,
    output_path: str | Path,
    profile_summary: str | None = None,
    previous_baseline_events_per_second: float | None = None,
) -> Path:
    """Write a Markdown performance report from benchmark results."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    target = _target_summary(results)
    comparison = _comparison_table(results)
    lines = [
        "# Performance Report",
        "",
        "Benchmarks separate core matching from replay, analytics, and full-system reporting overhead.",
        "Results are measured on synthetic event streams and depend on hardware, Python version, operating system, and machine load.",
        "",
        "## Target Summary",
        "",
        _markdown_table(target),
        "",
        "## Reference vs Optimised Comparison",
        "",
        _markdown_table(comparison),
        "",
        "## Full Benchmark Results",
        "",
        _markdown_table(results),
        "",
        "## Bottleneck Summary",
        "",
        profile_summary
        or (
            "- Reference replay spends material time in pandas row iteration, object construction, repeated best-price scans, "
            "per-event snapshot generation, and DataFrame assembly."
        ),
        "",
        "## Methodology",
        "",
        "- `core_matching` measures direct matching-engine processing with prepared events and no snapshots.",
        "- `replay_minimal` measures sequential replay without per-event analytics snapshots.",
        "- `full_system` includes matching, replay, trade capture, snapshots, and DataFrame outputs.",
        "- `analytics` measures post-replay microstructure analytics and report-style calculations separately.",
        "- The optimised path uses integer event codes, tick-normalised prices, heap-cached best prices, lazy cancellation, and optional trade recording.",
        "- The reference path is retained as the readable implementation used by examples, notebooks, dashboard demos, and validation checks.",
        "",
        "## Limitations",
        "",
        "- The optimised path is still Python and should not be described as exchange-grade or HFT-grade.",
        "- Synthetic event streams do not reproduce all real venue behaviours.",
        "- Per-event latency statistics include Python timing overhead and should be interpreted as benchmark diagnostics.",
        "- Large full-system snapshots can become memory-bound because each event creates reportable analytics state.",
        "",
    ]
    if previous_baseline_events_per_second is not None:
        lines.insert(
            4,
            f"Previous committed 100k reference benchmark baseline: {previous_baseline_events_per_second:,.0f} events/sec.",
        )
        lines.insert(5, "")
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def generate_profile_report(output_path: str | Path, event_count: int = 20_000, seed: int = 42) -> Path:
    """Profile the reference workflow and write a Markdown profile report."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    events = generate_market_events(SyntheticMarketConfig(num_events=event_count, seed=seed))
    reference_actions = _prepare_reference_actions(events)
    fast_events = prepare_fast_events(events)

    profile = cProfile.Profile()
    profile.enable()
    _run_reference_core(reference_actions)
    profile.disable()
    stats_stream = io.StringIO()
    stats = pstats.Stats(profile, stream=stats_stream).strip_dirs().sort_stats("cumtime")
    stats.print_stats(20)

    timings = [
        _time_block("order_creation", lambda: _profile_order_creation(reference_actions)),
        _time_block("order_book_add_cancel", _profile_book_add_cancel),
        _time_block("reference_process_order", lambda: _run_reference_core(reference_actions)),
        _time_block("reference_market_replay_full", lambda: MarketReplay().replay(events)),
        _time_block("snapshot_generation", lambda: _profile_snapshot_generation(events)),
        _time_block("analytics_calculation", lambda: _run_analytics_workload(events)),
        _time_block("optimised_core_matching", lambda: _run_fast_core(fast_events, record_trades=False)),
    ]
    timing_frame = pd.DataFrame(timings)
    total_timed = timing_frame["runtime_seconds"].sum()
    timing_frame["runtime_share_pct"] = np.where(
        total_timed > 0, timing_frame["runtime_seconds"] / total_timed * 100, 0.0
    )

    lines = [
        "# Profile Report",
        "",
        f"Profile workload: {event_count:,} deterministic synthetic events.",
        "",
        "## Timed Workflow Components",
        "",
        _markdown_table(timing_frame),
        "",
        "## cProfile Top Functions",
        "",
        "```text",
        stats_stream.getvalue().strip(),
        "```",
        "",
        "## Bottleneck Findings",
        "",
        "- Reference replay constructs Python dataclass objects for events and orders inside the hot loop.",
        "- `DataFrame.iterrows()` and pandas row access are slower than prepared records or `itertuples()`.",
        "- The reference book calls `min()`/`max()` over price dictionaries to find best prices, which becomes expensive as book size grows.",
        "- Per-event `book_metrics()` performs repeated depth calculations and sorting, mixing analytics/reporting with matching.",
        "- Trade and snapshot DataFrame construction is useful for analysis but should be outside core matching benchmarks.",
        "- Cancellations in the reference book rebuild price-level queues, while the optimised path uses lazy O(1) cancellation.",
        "",
        "## Optimisation Response",
        "",
        "- Added an optimised matching path with integer event codes, tick prices, heap-cached best bid/ask, and lightweight order records.",
        "- Added benchmark modes that separate core matching, minimal replay, full-system replay, and analytics.",
        "- Retained the readable reference engine and added parity tests to protect price-time priority and deterministic replay.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def benchmark_target_status(results: pd.DataFrame) -> dict[str, object]:
    """Return target status for the fastest 100k optimised core benchmark."""

    rows = results[
        (results["implementation_path"] == "optimised")
        & (results["benchmark_mode"] == "core_matching")
        & (results["event_count"] == 100_000)
    ]
    if rows.empty:
        return {"events_per_second": 0.0, "met_50k": False, "met_100k": False, "met_250k": False}
    eps = float(rows["events_per_second"].iloc[0])
    return {"events_per_second": eps, "met_50k": eps >= 50_000, "met_100k": eps >= 100_000, "met_250k": eps >= 250_000}


def _benchmark_reference_core(actions: list[ReferenceAction], event_count: int) -> dict[str, object]:
    return _measure_loop(
        implementation_path="reference",
        benchmark_mode="core_matching",
        event_count=event_count,
        runner_factory=lambda: _reference_event_runner(actions),
    )


def _benchmark_reference_replay_minimal(events: pd.DataFrame, event_count: int) -> dict[str, object]:
    return _measure_block(
        implementation_path="reference",
        benchmark_mode="replay_minimal",
        event_count=event_count,
        runner=lambda: _run_reference_replay_minimal(events),
    )


def _benchmark_reference_full_system(events: pd.DataFrame, event_count: int) -> dict[str, object]:
    return _measure_block(
        implementation_path="reference",
        benchmark_mode="full_system",
        event_count=event_count,
        runner=lambda: MarketReplay().replay(events),
    )


def _benchmark_optimised_core(events: list[FastEvent], event_count: int) -> dict[str, object]:
    return _measure_loop(
        implementation_path="optimised",
        benchmark_mode="core_matching",
        event_count=event_count,
        runner_factory=lambda: _fast_event_runner(events),
    )


def _benchmark_optimised_replay_minimal(events: list[FastEvent], event_count: int) -> dict[str, object]:
    return _measure_block(
        implementation_path="optimised",
        benchmark_mode="replay_minimal",
        event_count=event_count,
        runner=lambda: FastMarketReplay(record_trades=False).replay(events, snapshots=False),
    )


def _benchmark_optimised_full_system(events: list[FastEvent], event_count: int) -> dict[str, object]:
    return _measure_block(
        implementation_path="optimised",
        benchmark_mode="full_system",
        event_count=event_count,
        runner=lambda: FastMarketReplay(record_trades=True).replay(events, snapshots=True),
    )


def _benchmark_analytics(events: pd.DataFrame, event_count: int) -> dict[str, object]:
    return _measure_block(
        implementation_path="reference",
        benchmark_mode="analytics",
        event_count=event_count,
        runner=lambda: _run_analytics_workload(events),
    )


def _measure_loop(
    implementation_path: str,
    benchmark_mode: str,
    event_count: int,
    runner_factory: Callable[[], tuple[list[object], Callable[[object], None], Callable[[], tuple[int, int]]]],
) -> dict[str, object]:
    events, process_one, final_state = runner_factory()
    latencies_ns: list[int] = []
    start = time.perf_counter()
    for event in events:
        event_start = time.perf_counter_ns()
        process_one(event)
        latencies_ns.append(time.perf_counter_ns() - event_start)
    runtime = time.perf_counter() - start
    trades, resting = final_state()
    peak_memory = _measure_loop_memory(runner_factory)
    return _row(implementation_path, benchmark_mode, event_count, runtime, latencies_ns, peak_memory, trades, resting)


def _measure_block(
    implementation_path: str,
    benchmark_mode: str,
    event_count: int,
    runner: Callable[[], object],
) -> dict[str, object]:
    start_ns = time.perf_counter_ns()
    start = time.perf_counter()
    result = runner()
    runtime = time.perf_counter() - start
    latency_ns = time.perf_counter_ns() - start_ns
    trades, resting = _extract_counts(result)
    peak_memory = _measure_block_memory(runner)
    per_event_latency = [latency_ns / max(event_count, 1)]
    return _row(
        implementation_path, benchmark_mode, event_count, runtime, per_event_latency, peak_memory, trades, resting
    )


def _measure_loop_memory(
    runner_factory: Callable[[], tuple[list[object], Callable[[object], None], Callable[[], tuple[int, int]]]],
) -> int:
    events, process_one, _ = runner_factory()
    tracemalloc.start()
    for event in events:
        process_one(event)
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak_memory


def _measure_block_memory(runner: Callable[[], object]) -> int:
    tracemalloc.start()
    runner()
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak_memory


def _row(
    implementation_path: str,
    benchmark_mode: str,
    event_count: int,
    runtime: float,
    latencies_ns: list[int] | list[float],
    peak_memory: int,
    trades: int,
    resting_orders: int,
) -> dict[str, object]:
    avg_latency, p50_latency, p95_latency, p99_latency = latency_summary_us(np.asarray(latencies_ns, dtype="float64"))
    return {
        "implementation_path": implementation_path,
        "benchmark_mode": benchmark_mode,
        "event_count": event_count,
        "processed_events": event_count,
        "runtime_seconds": runtime,
        "events_per_second": event_count / runtime if runtime > 0 else np.nan,
        "avg_latency_us": avg_latency,
        "p50_latency_us": p50_latency,
        "p95_latency_us": p95_latency,
        "p99_latency_us": p99_latency,
        "peak_memory_mb": peak_memory / 1024 / 1024,
        "trades": trades,
        "resting_orders": resting_orders,
        "numba_available": NUMBA_AVAILABLE,
    }


def _reference_event_runner(
    actions: list[ReferenceAction],
) -> tuple[list[ReferenceAction], Callable[[ReferenceAction], None], Callable[[], tuple[int, int]]]:
    engine = MatchingEngine()

    def process(action: ReferenceAction) -> None:
        _process_reference_action(engine, action)

    return actions, process, lambda: (len(engine.trades), len(engine.book))


def _fast_event_runner(
    events: list[FastEvent],
) -> tuple[list[FastEvent], Callable[[FastEvent], None], Callable[[], tuple[int, int]]]:
    engine = FastMatchingEngine(record_trades=False)

    def process(event: FastEvent) -> None:
        engine.process_event(
            event.event_type,
            event.order_id,
            event.side,
            event.quantity,
            event.price_ticks,
            event.timestamp,
            event.target_order_id,
        )

    return events, process, lambda: (engine.trade_count, len(engine.book))


def _run_reference_core(actions: list[ReferenceAction]) -> MatchingEngine:
    engine = MatchingEngine()
    for action in actions:
        _process_reference_action(engine, action)
    return engine


def _run_reference_replay_minimal(events: pd.DataFrame) -> MatchingEngine:
    return _run_reference_core(_prepare_reference_actions(events))


def _run_fast_core(events: list[FastEvent], record_trades: bool) -> FastMatchingEngine:
    engine = FastMatchingEngine(record_trades=record_trades)
    for event in events:
        engine.process_event(
            event.event_type,
            event.order_id,
            event.side,
            event.quantity,
            event.price_ticks,
            event.timestamp,
            event.target_order_id,
        )
    return engine


def _process_reference_action(engine: MatchingEngine, action: ReferenceAction) -> None:
    if action.event_type == "limit":
        engine.process_order(
            Order(
                order_id=action.order_id,
                side=action.side,
                order_type=OrderType.LIMIT,
                quantity=action.quantity,
                price=action.price,
                timestamp=action.timestamp,
            )
        )
    elif action.event_type == "market":
        engine.process_order(
            Order(
                order_id=action.order_id,
                side=action.side,
                order_type=OrderType.MARKET,
                quantity=action.quantity,
                timestamp=action.timestamp,
            )
        )
    elif action.event_type == "modify":
        engine.process_modify(
            ModifyRequest(
                order_id=action.order_id,
                timestamp=action.timestamp,
                target_order_id=action.target_order_id or "",
                new_quantity=action.quantity,
                new_price=action.price or 0.0,
            )
        )
    else:
        engine.process_cancel(
            CancelRequest(
                order_id=action.order_id,
                timestamp=action.timestamp,
                target_order_id=action.target_order_id or "",
            )
        )


def _prepare_reference_actions(events: pd.DataFrame) -> list[ReferenceAction]:
    frame = events.sort_values("timestamp", kind="mergesort")
    actions: list[ReferenceAction] = []
    for row in frame.itertuples(index=False):
        actions.append(
            ReferenceAction(
                timestamp=float(row.timestamp),
                event_type=str(row.event_type),
                order_id=str(row.order_id),
                side=None if pd.isna(row.side) else str(row.side),
                quantity=0 if pd.isna(row.quantity) else int(row.quantity),
                price=None if pd.isna(row.price) else float(row.price),
                target_order_id=None if pd.isna(row.target_order_id) else str(row.target_order_id),
            )
        )
    return actions


def _row_to_event(row: pd.Series) -> MarketEvent:
    side = None if pd.isna(row.get("side")) else row.get("side")
    quantity = None if pd.isna(row.get("quantity")) else int(row.get("quantity"))
    price = None if pd.isna(row.get("price")) else float(row.get("price"))
    target_order_id = None if pd.isna(row.get("target_order_id")) else str(row.get("target_order_id"))
    trader_id = None if pd.isna(row.get("trader_id")) else str(row.get("trader_id"))
    return MarketEvent(
        timestamp=float(row["timestamp"]),
        event_type=str(row["event_type"]),
        order_id=str(row["order_id"]),
        side=side,
        quantity=quantity,
        price=price,
        trader_id=trader_id,
        target_order_id=target_order_id,
        symbol=str(row.get("symbol", "SYNTH")),
    )


def _process_event(engine: MatchingEngine, event: MarketEvent):
    if event.event_type in {EventType.LIMIT, EventType.MARKET}:
        return engine.process_order(event.to_order())
    if event.event_type is EventType.CANCEL:
        return engine.process_cancel(event.to_cancel())
    if event.event_type is EventType.MODIFY:
        return engine.process_modify(event.to_modify())
    raise ValueError(f"Unsupported event type {event.event_type}.")


def _extract_counts(result: object) -> tuple[int, int]:
    if isinstance(result, MatchingEngine):
        return len(result.trades), len(result.book)
    if isinstance(result, FastMatchingEngine):
        return result.trade_count, len(result.book)
    trade_count = int(getattr(result, "trade_count", 0))
    final_book = getattr(result, "final_book", None)
    if trade_count == 0 and hasattr(result, "trades"):
        trades = getattr(result, "trades")
        trade_count = len(trades) if trades is not None else 0
    resting = len(final_book) if final_book is not None else 0
    return trade_count, resting


def _run_analytics_workload(events: pd.DataFrame) -> dict[str, object]:
    replay = FastMarketReplay(record_trades=True).replay(prepare_fast_events(events), snapshots=True)
    snapshots = replay.snapshots
    if not snapshots.empty and "mid_price" in snapshots:
        mid = snapshots["mid_price"].ffill().bfill()
        snapshots["rolling_volatility"] = rolling_volatility(mid, window=min(30, max(len(mid) // 10, 2)))
        buys = np.zeros(len(snapshots))
        sells = np.zeros(len(snapshots))
        snapshots["rolling_ofi"] = rolling_order_flow_imbalance(
            buys, sells, window=min(30, max(len(snapshots) // 10, 1))
        )
    final_metrics = book_metrics_from_fast(replay.final_book)
    return {"snapshots": snapshots, "trades": replay.trades, "metrics": final_metrics}


def book_metrics_from_fast(book) -> dict[str, object]:
    """Return final metrics from a fast book using the reference metric names."""

    return {
        "best_bid": book.best_bid(),
        "best_ask": book.best_ask(),
        "mid_price": book.mid_price(),
        "spread": book.spread(),
        "bid_depth": book.total_depth(1, 5),
        "ask_depth": book.total_depth(-1, 5),
    }


def _profile_order_creation(actions: list[ReferenceAction]) -> None:
    for action in actions:
        if action.event_type == "limit":
            Order(action.order_id, action.side, OrderType.LIMIT, action.quantity, action.price, action.timestamp)
        elif action.event_type == "market":
            Order(action.order_id, action.side, OrderType.MARKET, action.quantity, timestamp=action.timestamp)


def _profile_book_add_cancel() -> None:
    engine = MatchingEngine()
    for idx in range(2_000):
        engine.process_order(Order(f"B{idx}", "buy", OrderType.LIMIT, 10, 99.0 - idx * 0.01, idx))
    for idx in range(0, 2_000, 2):
        engine.process_cancel(CancelRequest(f"C{idx}", float(idx), f"B{idx}"))


def _profile_snapshot_generation(events: pd.DataFrame) -> pd.DataFrame:
    result = MarketReplay().replay(events.head(2_000))
    rows = []
    for _ in range(100):
        rows.append(book_metrics(result.final_book, levels=5))
    return pd.DataFrame(rows)


def _time_block(name: str, func: Callable[[], object]) -> dict[str, object]:
    start = time.perf_counter()
    func()
    runtime = time.perf_counter() - start
    return {"component": name, "runtime_seconds": runtime}


def _comparison_table(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mode in BENCHMARK_MODES:
        mode_frame = results[results["benchmark_mode"] == mode]
        common_counts = sorted(set(mode_frame["event_count"]))
        for event_count in common_counts:
            ref = mode_frame[
                (mode_frame["event_count"] == event_count) & (mode_frame["implementation_path"] == "reference")
            ]
            opt = mode_frame[
                (mode_frame["event_count"] == event_count) & (mode_frame["implementation_path"] == "optimised")
            ]
            if ref.empty or opt.empty:
                continue
            ref_eps = float(ref["events_per_second"].iloc[0])
            opt_eps = float(opt["events_per_second"].iloc[0])
            rows.append(
                {
                    "benchmark_mode": mode,
                    "event_count": event_count,
                    "reference_events_per_second": ref_eps,
                    "optimised_events_per_second": opt_eps,
                    "improvement_multiple": opt_eps / ref_eps if ref_eps > 0 else np.nan,
                }
            )
    return pd.DataFrame(rows)


def _target_summary(results: pd.DataFrame) -> pd.DataFrame:
    status = benchmark_target_status(results)
    return pd.DataFrame(
        [
            {
                "target": "50,000 events/sec",
                "met": bool(status["met_50k"]),
                "events_per_second": status["events_per_second"],
            },
            {
                "target": "100,000 events/sec",
                "met": bool(status["met_100k"]),
                "events_per_second": status["events_per_second"],
            },
            {
                "target": "250,000 events/sec",
                "met": bool(status["met_250k"]),
                "events_per_second": status["events_per_second"],
            },
        ]
    )


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
