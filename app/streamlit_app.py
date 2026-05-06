"""Streamlit dashboard for the limit order book trading engine."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from lob_engine.analytics.microstructure import book_metrics, rolling_order_flow_imbalance, rolling_volatility
from lob_engine.analytics.slippage import slippage_bps
from lob_engine.analytics.transaction_costs import total_transaction_cost
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderType, Side
from lob_engine.execution import ImplementationShortfallExecutor, ParentOrder, POVExecutor, TWAPExecutor, VWAPExecutor
from lob_engine.simulation.backtester import EventDrivenBacktester
from lob_engine.simulation.market_generator import SyntheticMarketConfig, generate_market_events
from lob_engine.simulation.market_replay import MarketReplay
from lob_engine.strategies.mean_reversion import MeanReversionStrategy
from lob_engine.utils.performance import benchmark_event_throughput
from lob_engine.utils.plotting import apply_dark_layout, depth_chart, time_series_chart
from lob_engine.utils.validation import run_validation_suite
from ui_components import (
    hero,
    inject_css,
    limitation_panel,
    metric_card,
    order_ladder_html,
    section_header,
    status_badge,
)

st.set_page_config(
    page_title="Limit Order Book Trading Engine",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_css()


@st.cache_data(show_spinner=False)
def demo_engine() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    engine = MatchingEngine()
    for order in [
        Order("B-001", Side.BUY, OrderType.LIMIT, 120, 99.95, timestamp=1),
        Order("B-002", Side.BUY, OrderType.LIMIT, 80, 99.92, timestamp=2),
        Order("B-003", Side.BUY, OrderType.LIMIT, 60, 99.90, timestamp=3),
        Order("A-001", Side.SELL, OrderType.LIMIT, 100, 100.05, timestamp=4),
        Order("A-002", Side.SELL, OrderType.LIMIT, 90, 100.08, timestamp=5),
        Order("A-003", Side.SELL, OrderType.LIMIT, 70, 100.10, timestamp=6),
    ]:
        engine.process_order(order)
    engine.process_order(Order("BUY-MKT", Side.BUY, OrderType.MARKET, 130, timestamp=7))
    return engine.book.top_n_levels(10), engine.trades_frame(), book_metrics(engine.book)


@st.cache_data(show_spinner=False)
def replay_data(num_events: int, seed: int):
    events = generate_market_events(SyntheticMarketConfig(num_events=num_events, seed=seed))
    return MarketReplay().replay(events)


@st.cache_data(show_spinner=False)
def execution_comparison(parent_qty: int, side: str) -> pd.DataFrame:
    parent = ParentOrder("P-DASH", side, parent_qty, 0, 60, arrival_price=100.0)
    prices = [100.00, 100.01, 100.02, 100.00, 99.99, 100.03, 100.04, 100.02, 100.01, 100.00]
    algos = [
        TWAPExecutor(parent, slices=10),
        VWAPExecutor(parent, volume_curve=[0.08, 0.09, 0.1, 0.12, 0.14, 0.14, 0.12, 0.1, 0.07, 0.04]),
        POVExecutor(parent, market_volumes=[10_000, 12_000, 9_000, 11_000, 10_500], participation_rate=0.1),
        ImplementationShortfallExecutor(parent, slices=10, urgency=0.7),
    ]
    rows = []
    for algo in algos:
        result = algo.execute_against_prices(prices)
        for key, value in result.metrics.items():
            rows.append({"algorithm": algo.name, "metric": key, "value": value})
    return pd.DataFrame(rows)


@st.cache_data(show_spinner=False)
def backtest_data(num_events: int, seed: int):
    events = generate_market_events(SyntheticMarketConfig(num_events=num_events, seed=seed))
    strategy = MeanReversionStrategy(window=25, threshold_bps=2.0, order_size=10)
    return EventDrivenBacktester(strategy, starting_inventory=50, allow_short=False).run(events)


@st.cache_data(show_spinner=False)
def validation_data() -> pd.DataFrame:
    return run_validation_suite(include_performance=False)


def dark_bar(frame: pd.DataFrame, x: str, y: str, color: str, title: str) -> go.Figure:
    fig = px.bar(frame, x=x, y=y, color=color, color_discrete_sequence=["#4dd7fa", "#19c37d", "#f6c35b", "#ff5c7a"])
    return apply_dark_layout(fig, title)


def overview_page() -> None:
    validation = validation_data()
    passed = int(validation["passed"].sum())
    total = len(validation)
    hero(
        "Limit Order Book Trading Engine",
        "Event-driven matching, market replay, execution algorithms, slippage analytics, strategy backtesting, validation checks, and performance benchmarks in one reproducible Python project.",
    )
    cols = st.columns(4)
    with cols[0]:
        metric_card("Validation", f"{passed}/{total}", "Deterministic checks passed")
    with cols[1]:
        metric_card("Execution", "TWAP / VWAP / POV", "Plus implementation shortfall")
    with cols[2]:
        metric_card("Replay", "Synthetic events", "Fixed seeds, no live-data dependency")
    with cols[3]:
        metric_card("Analytics", "LOB + TCA", "Spread, depth, imbalance, slippage")

    section_header("Validation Snapshot", "Core invariants exercised by deterministic tests")
    status = "PASS" if passed == total else "REVIEW"
    st.markdown(f"{status_badge(status, passed == total)}", unsafe_allow_html=True)
    st.dataframe(validation, use_container_width=True, hide_index=True)

    section_header("Architecture Map", "Reusable package modules beneath the dashboard")
    arch = pd.DataFrame(
        [
            ("core", "Order models, order book, matching engine, events, clock"),
            ("analytics", "Microstructure metrics, liquidity, slippage, transaction costs"),
            ("execution", "TWAP, VWAP, POV, implementation shortfall schedules"),
            ("simulation", "Synthetic generator, market replay, fill simulator, backtester"),
            ("strategies", "Market making, mean reversion, momentum examples"),
            ("utils", "Validation, performance benchmarks, plotting, I/O"),
        ],
        columns=["module", "responsibility"],
    )
    st.dataframe(arch, use_container_width=True, hide_index=True)


def order_book_page() -> None:
    ladder, trades, metrics = demo_engine()
    section_header("Live Order Book Demo", "Terminal-style ladder, top-of-book metrics, and trade tape")
    cols = st.columns([1.1, 1])
    with cols[0]:
        st.markdown(order_ladder_html(ladder), unsafe_allow_html=True)
    with cols[1]:
        st.plotly_chart(depth_chart(ladder), use_container_width=True)
    kpis = st.columns(5)
    formats = {
        "best_bid": "{:.2f}",
        "best_ask": "{:.2f}",
        "mid_price": "{:.2f}",
        "spread": "{:.4f}",
        "imbalance": "{:.4f}",
    }
    for col, (label, key) in zip(
        kpis,
        [
            ("Best Bid", "best_bid"),
            ("Best Ask", "best_ask"),
            ("Mid", "mid_price"),
            ("Spread", "spread"),
            ("OBI", "imbalance"),
        ],
    ):
        with col:
            value = metrics.get(key)
            metric_card(label, "n/a" if value is None else formats[key].format(value), "current snapshot")
    section_header("Trade Tape", "Aggressor/passive fills produced by the same matching engine")
    st.dataframe(trades, use_container_width=True, hide_index=True)


def matching_page() -> None:
    section_header("Matching Engine Demo", "Price-time priority, market orders, crossing limits, and partial fills")
    engine = MatchingEngine()
    engine.process_order(Order("ASK-OLD", Side.SELL, OrderType.LIMIT, 50, 100.01, timestamp=1))
    engine.process_order(Order("ASK-NEW", Side.SELL, OrderType.LIMIT, 75, 100.01, timestamp=2))
    engine.process_order(Order("ASK-2", Side.SELL, OrderType.LIMIT, 80, 100.03, timestamp=3))
    result = engine.process_order(Order("BUY-MKT", Side.BUY, OrderType.MARKET, 140, timestamp=4))
    cols = st.columns([1, 1])
    with cols[0]:
        st.markdown(order_ladder_html(engine.book.top_n_levels(10)), unsafe_allow_html=True)
    with cols[1]:
        trade_frame = pd.DataFrame([trade.to_dict() for trade in result.trades])
        st.dataframe(trade_frame, use_container_width=True, hide_index=True)
    st.caption("The oldest resting order at the best ask fills first; the residual walks to the next price level.")


def replay_page() -> None:
    st.sidebar.divider()
    events = st.sidebar.slider("Replay events", 500, 5_000, 2_000, step=500)
    seed = st.sidebar.number_input("Replay seed", value=42, step=1)
    result = replay_data(events, int(seed))
    section_header("Market Replay", "Sequential synthetic event replay with book snapshots and trades")
    cols = st.columns(4)
    with cols[0]:
        metric_card("Events", f"{result.processed_events:,}", "processed sequentially")
    with cols[1]:
        metric_card("Trades", f"{len(result.trades):,}", "matched executions")
    with cols[2]:
        metric_card("Resting", f"{len(result.final_book):,}", "final live orders")
    with cols[3]:
        metric_card("Rejects", f"{len(result.rejections):,}", "mostly stale cancels/modifies")
    tabs = st.tabs(["Mid / Spread", "Imbalance", "Snapshots", "Trades"])
    with tabs[0]:
        st.plotly_chart(
            time_series_chart(result.snapshots, "timestamp", ["mid_price", "spread"], "Replay Mid Price and Spread"),
            use_container_width=True,
        )
    with tabs[1]:
        st.plotly_chart(
            time_series_chart(
                result.snapshots, "timestamp", ["imbalance", "book_pressure"], "Order Book Imbalance and Pressure"
            ),
            use_container_width=True,
        )
    with tabs[2]:
        st.dataframe(result.snapshots.tail(200), use_container_width=True, hide_index=True)
    with tabs[3]:
        st.dataframe(result.trades.tail(200), use_container_width=True, hide_index=True)


def analytics_page() -> None:
    result = replay_data(2_500, 42)
    section_header("Microstructure Analytics", "Depth, imbalance, rolling volatility, and order-flow imbalance")
    snapshots = result.snapshots.copy()
    snapshots["rolling_volatility"] = rolling_volatility(snapshots["mid_price"].ffill().bfill(), window=30)
    if result.trades.empty:
        buys = sells = pd.Series([0] * len(snapshots))
    else:
        trade_side = result.trades["side"]
        buy_qty = result.trades["quantity"].where(trade_side.eq("buy"), 0)
        sell_qty = result.trades["quantity"].where(trade_side.eq("sell"), 0)
        flow = pd.DataFrame({"timestamp": result.trades["timestamp"], "buy": buy_qty, "sell": sell_qty})
        aligned = pd.merge_asof(
            snapshots[["timestamp"]], flow.sort_values("timestamp"), on="timestamp", direction="backward"
        ).fillna(0)
        buys, sells = aligned["buy"], aligned["sell"]
    snapshots["rolling_ofi"] = rolling_order_flow_imbalance(buys, sells, window=30)
    cols = st.columns(2)
    with cols[0]:
        st.plotly_chart(
            time_series_chart(snapshots, "timestamp", ["rolling_volatility"], "Rolling Mid-Price Volatility"),
            use_container_width=True,
        )
    with cols[1]:
        st.plotly_chart(
            time_series_chart(snapshots, "timestamp", ["rolling_ofi"], "Rolling Order-Flow Imbalance"),
            use_container_width=True,
        )
    st.dataframe(
        snapshots[
            [
                "timestamp",
                "best_bid",
                "best_ask",
                "mid_price",
                "spread",
                "imbalance",
                "rolling_volatility",
                "rolling_ofi",
            ]
        ].tail(150),
        use_container_width=True,
        hide_index=True,
    )


def execution_page() -> None:
    parent_qty = st.sidebar.slider("Parent quantity", 500, 20_000, 5_000, step=500)
    side = st.sidebar.selectbox("Execution side", ["buy", "sell"])
    metrics = execution_comparison(parent_qty, side)
    section_header("Execution Algorithms", "TWAP, VWAP, POV, and implementation-shortfall metrics")
    selected = metrics[
        metrics["metric"].isin(["average_fill_price", "slippage_bps", "participation_rate", "transaction_cost_bps"])
    ]
    fig = dark_bar(selected, "algorithm", "value", "metric", "Execution Quality Comparison")
    st.plotly_chart(fig, use_container_width=True)
    pivot = metrics.pivot(index="algorithm", columns="metric", values="value").reset_index()
    st.dataframe(pivot, use_container_width=True, hide_index=True)


def slippage_page() -> None:
    section_header(
        "Slippage and Transaction Costs", "Side-aware benchmark slippage and simple transaction cost components"
    )
    rows = []
    for algorithm, avg in [
        ("TWAP", 100.025),
        ("VWAP", 100.018),
        ("POV", 100.031),
        ("Implementation Shortfall", 100.015),
    ]:
        rows.append({"algorithm": algorithm, "slippage_bps": slippage_bps(avg, 100.0, Side.BUY)})
    slip = pd.DataFrame(rows)
    costs = total_transaction_cost(10_000, 100.0, spread=0.02, average_daily_volume=2_000_000, volatility=0.02)
    cols = st.columns([1.2, 1])
    with cols[0]:
        st.plotly_chart(
            dark_bar(slip, "algorithm", "slippage_bps", "algorithm", "Slippage vs Arrival Price"),
            use_container_width=True,
        )
    with cols[1]:
        metric_card("Total Cost", f"{costs.total_cost_bps:.2f} bps", "spread + impact + commission")
        metric_card("Spread Cost", f"{costs.spread_cost:.4f}", "per share")
        metric_card("Impact Model", f"{costs.market_impact:.4f}", "square-root proxy")


def strategy_page() -> None:
    result = backtest_data(2_000, 101)
    section_header("Strategy Backtest", "Event-driven demo strategy with inventory and transaction-cost accounting")
    cols = st.columns(4)
    with cols[0]:
        metric_card("Ending Equity", f"{result.metrics['ending_equity']:,.2f}", "mark-to-mid")
    with cols[1]:
        metric_card("P&L", f"{result.metrics['total_pnl']:,.2f}", "synthetic data")
    with cols[2]:
        metric_card("Max Drawdown", f"{result.metrics['max_drawdown']:.2%}", "equity curve")
    with cols[3]:
        metric_card("Fill Rate", f"{result.metrics['fill_rate']:.2%}", "strategy orders")
    tabs = st.tabs(["Equity", "Inventory", "Orders", "Trades"])
    with tabs[0]:
        st.plotly_chart(
            time_series_chart(result.equity_curve, "timestamp", ["equity"], "Strategy Equity Curve"),
            use_container_width=True,
        )
    with tabs[1]:
        st.plotly_chart(
            time_series_chart(result.equity_curve, "timestamp", ["inventory"], "Strategy Inventory"),
            use_container_width=True,
        )
    with tabs[2]:
        st.dataframe(result.orders.tail(200), use_container_width=True, hide_index=True)
    with tabs[3]:
        st.dataframe(result.trades.tail(200), use_container_width=True, hide_index=True)
    limitation_panel(
        "Strategies shown here are infrastructure demonstrations on synthetic data. They include transaction costs and inventory tracking, but they should not be interpreted as evidence of live alpha."
    )


def performance_page() -> None:
    section_header(
        "Performance Benchmarks",
        "Reference vs optimised throughput, latency distribution, memory scaling, and profile findings",
    )
    report_path = ROOT / "reports" / "benchmark_results.csv"
    if report_path.exists():
        results = pd.read_csv(report_path)
    else:
        results = benchmark_event_throughput(event_counts=(1_000, 5_000), seed=42)
    if "benchmark_mode" not in results:
        results = results.assign(benchmark_mode="core_matching", implementation_path="reference")

    modes = sorted(results["benchmark_mode"].dropna().unique())
    event_counts = sorted(results["event_count"].dropna().unique())
    selected_mode = st.sidebar.selectbox(
        "Benchmark mode", modes, index=0 if "core_matching" not in modes else modes.index("core_matching")
    )
    selected_event_count = st.sidebar.selectbox("Benchmark events", event_counts, index=len(event_counts) - 1)
    filtered = results[(results["benchmark_mode"] == selected_mode) & (results["event_count"] == selected_event_count)]
    if filtered.empty:
        filtered = results[results["benchmark_mode"] == selected_mode]
    best = filtered.sort_values("events_per_second", ascending=False).iloc[0]
    core_100k = results[
        (results["benchmark_mode"] == "core_matching")
        & (results["implementation_path"] == "optimised")
        & (results["event_count"] == 100_000)
    ]
    headline = best if core_100k.empty else core_100k.iloc[0]
    cols = st.columns(4)
    with cols[0]:
        metric_card("Optimised Core", f"{headline['events_per_second']:,.0f}", "events/sec at 100k if available")
    with cols[1]:
        metric_card("p95 latency", f"{headline['p95_latency_us']:.2f} us", "core benchmark")
    with cols[2]:
        metric_card("Peak memory", f"{headline['peak_memory_mb']:.2f} MB", "separate tracemalloc run")
    with cols[3]:
        metric_card("Largest run", f"{int(max(event_counts)):,}", "synthetic events")

    comparison = results[results["benchmark_mode"] == selected_mode].copy()
    fig = px.bar(
        comparison,
        x="event_count",
        y="events_per_second",
        color="implementation_path",
        barmode="group",
        color_discrete_map={"reference": "#8ea4c8", "optimised": "#4dd7fa"},
        title=f"Throughput by Event Count: {selected_mode}",
    )
    st.plotly_chart(apply_dark_layout(fig), use_container_width=True)

    latency_cols = ["p50_latency_us", "p95_latency_us", "p99_latency_us"]
    latency = filtered.melt(
        id_vars=["implementation_path"],
        value_vars=[column for column in latency_cols if column in filtered],
        var_name="latency_percentile",
        value_name="microseconds",
    )
    cols = st.columns(2)
    with cols[0]:
        fig_latency = px.bar(
            latency,
            x="latency_percentile",
            y="microseconds",
            color="implementation_path",
            barmode="group",
            title=f"Latency Percentiles: {selected_mode} / {int(selected_event_count):,}",
            color_discrete_map={"reference": "#8ea4c8", "optimised": "#19c37d"},
        )
        st.plotly_chart(apply_dark_layout(fig_latency), use_container_width=True)
    with cols[1]:
        fig_memory = px.line(
            comparison,
            x="event_count",
            y="peak_memory_mb",
            color="implementation_path",
            markers=True,
            title=f"Peak Memory Scaling: {selected_mode}",
            color_discrete_map={"reference": "#8ea4c8", "optimised": "#f6c35b"},
        )
        st.plotly_chart(apply_dark_layout(fig_memory), use_container_width=True)

    profile_path = ROOT / "reports" / "profile_report.md"
    if profile_path.exists():
        profile_text = profile_path.read_text(encoding="utf-8")
        marker = "## Bottleneck Findings"
        summary = profile_text.split(marker, 1)[1].split("##", 1)[0].strip() if marker in profile_text else ""
        if summary:
            st.markdown("#### Bottleneck Summary")
            st.markdown(summary)
    st.dataframe(results, use_container_width=True, hide_index=True)


def validation_page() -> None:
    validation = validation_data()
    passed = int(validation["passed"].sum())
    section_header("Validation Results", "Deterministic benchmark checks for engine correctness")
    cols = st.columns(3)
    with cols[0]:
        metric_card("Checks Passed", f"{passed}/{len(validation)}", "target: all deterministic checks")
    with cols[1]:
        metric_card("Replay", "Deterministic", "same events, same outputs")
    with cols[2]:
        metric_card("Testing", "pytest", "unit + integration coverage")
    st.markdown(status_badge("ALL PASSED", passed == len(validation)), unsafe_allow_html=True)
    st.dataframe(validation, use_container_width=True, hide_index=True)


PAGES = {
    "Overview": overview_page,
    "Order Book": order_book_page,
    "Matching Engine": matching_page,
    "Market Replay": replay_page,
    "Microstructure": analytics_page,
    "Execution Algorithms": execution_page,
    "Slippage & Costs": slippage_page,
    "Strategy Backtest": strategy_page,
    "Performance": performance_page,
    "Validation": validation_page,
}


def main() -> None:
    st.sidebar.markdown("## LOB Engine")
    st.sidebar.caption("Market microstructure and execution analytics")
    page = st.sidebar.radio("Workspace", list(PAGES), label_visibility="collapsed")
    st.sidebar.divider()
    st.sidebar.markdown("**Status**")
    st.sidebar.markdown(status_badge("Deterministic Core", True), unsafe_allow_html=True)
    st.sidebar.markdown(status_badge("Synthetic Replay", True), unsafe_allow_html=True)
    st.sidebar.markdown(status_badge("No Live Data Required", True), unsafe_allow_html=True)
    PAGES[page]()
    st.markdown(
        '<div style="height:2rem"></div><div style="color:#64748b; font-size:.8rem; border-top:1px solid rgba(148,163,184,.12); padding-top:1rem;">Limit Order Book Trading Engine</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
