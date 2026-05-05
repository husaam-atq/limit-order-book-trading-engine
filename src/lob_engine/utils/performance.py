"""Performance benchmark utilities."""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import numpy as np
import pandas as pd

from lob_engine.core.events import EventType, MarketEvent
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events


def benchmark_event_throughput(
    event_counts: tuple[int, ...] = (1_000, 10_000, 100_000),
    seed: int = 42,
    output_path: str | Path | None = None,
) -> pd.DataFrame:
    """Benchmark replay throughput and per-event latency."""

    rows = []
    for event_count in event_counts:
        events = generate_market_events(SyntheticMarketConfig(num_events=event_count, seed=seed))
        engine = MatchingEngine()
        latencies_ns: list[int] = []
        tracemalloc.start()
        start = time.perf_counter()
        processed = 0
        for _, row in events.iterrows():
            event = _row_to_event(row)
            event_start = time.perf_counter_ns()
            _process_event(engine, event)
            latencies_ns.append(time.perf_counter_ns() - event_start)
            processed += 1
        runtime = time.perf_counter() - start
        _, peak_memory = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        latencies_us = np.asarray(latencies_ns, dtype="float64") / 1_000.0
        rows.append(
            {
                "event_count": event_count,
                "processed_events": processed,
                "runtime_seconds": runtime,
                "events_per_second": processed / runtime if runtime > 0 else np.nan,
                "avg_latency_us": float(latencies_us.mean()),
                "p50_latency_us": float(np.percentile(latencies_us, 50)),
                "p95_latency_us": float(np.percentile(latencies_us, 95)),
                "p99_latency_us": float(np.percentile(latencies_us, 99)),
                "peak_memory_mb": peak_memory / 1024 / 1024,
                "trades": len(engine.trades),
                "resting_orders": len(engine.book),
            }
        )
    result = pd.DataFrame(rows)
    if output_path is not None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        result.to_csv(output, index=False)
    return result


def write_performance_report(results: pd.DataFrame, output_path: str | Path) -> Path:
    """Write a Markdown performance report from benchmark results."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Performance Report",
        "",
        "Benchmark results measure deterministic synthetic event replay through the Python matching engine.",
        "Results depend on CPU, Python version, operating system, and current machine load.",
        "",
        "## Results",
        "",
        _markdown_table(results),
        "",
        "## Methodology",
        "",
        "- Synthetic market events are generated with a fixed random seed.",
        "- Each event is converted into the same order/cancel/modify models used by market replay.",
        "- Latency is measured around matching-engine event processing only.",
        "- Peak memory is measured with `tracemalloc` during each benchmark run.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")
    return output


def _process_event(engine: MatchingEngine, event: MarketEvent):
    if event.event_type in {EventType.LIMIT, EventType.MARKET}:
        return engine.process_order(event.to_order())
    if event.event_type is EventType.CANCEL:
        return engine.process_cancel(event.to_cancel())
    if event.event_type is EventType.MODIFY:
        return engine.process_modify(event.to_modify())
    raise ValueError(f"Unsupported event type {event.event_type}.")


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
