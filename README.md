# Limit Order Book Trading Engine

[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-pytest-green.svg)](tests/)
[![Ruff](https://img.shields.io/badge/lint-ruff-46a2f1.svg)](https://docs.astral.sh/ruff/)
[![Black](https://img.shields.io/badge/format-black-111111.svg)](https://black.readthedocs.io/)
[![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-ff4b4b.svg)](app/streamlit_app.py)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)](LICENSE)

Event-driven limit order book and execution simulator implementing price-time priority matching, market replay, TWAP/VWAP/POV execution algorithms, slippage analytics, transaction cost analysis, strategy backtesting, validation checks, performance benchmarks, and a polished Streamlit dashboard.

## What This Project Demonstrates

- Deterministic price-time priority matching with market, limit, cancel, and cancel/replace request handling.
- FIFO price-level queues, partial fills, order lifecycle tracking, maker/taker trade records, and full book snapshots.
- Market microstructure analytics: best bid/ask, spread, midpoint, depth, imbalance, weighted midpoint, book pressure, rolling volatility, and order-flow imbalance.
- Synthetic market event generation with volatility regimes, liquidity regimes, cancellations, and reproducible seeds.
- Market replay without lookahead, including snapshots, trades, rejections, and time-series analytics.
- Execution algorithms for large parent orders: TWAP, VWAP, POV, and implementation shortfall.
- Transaction cost analytics covering arrival-price slippage, benchmark slippage, spread cost, impact, commission, and total cost in basis points.
- Event-driven strategy backtesting with inventory, cash, P&L, drawdown, turnover, fill-rate, and transaction-cost accounting.
- A readable reference implementation plus a faster optimised benchmark path.
- Benchmark modes that separate core matching, replay, full-system, and analytics workloads up to 1,000,000 synthetic events.

## Why It Matters For Quant Trading

Market microstructure and execution systems sit close to the trading venue: order priority, queue position, liquidity, fill quality, and implementation shortfall directly affect realised performance. This project focuses on those mechanics rather than alpha claims, making it suitable for quant developer, execution trading, market microstructure, systematic trading infrastructure, and trading analytics discussions.

## Headline Validation Results

Latest validation run: **14/14 deterministic checks passed**.

| Area | Result |
| --- | --- |
| Price-time priority | Passed |
| Price priority | Passed |
| Market order matching | Passed |
| Limit order crossing | Passed |
| Partial fills | Passed |
| Cancel handling | Passed |
| Book metrics | Passed |
| Replay determinism | Passed |
| Reference vs optimised parity | Passed |
| Optimised replay determinism | Passed |
| Execution algorithms | Passed |
| Transaction cost analytics | Passed |
| Backtester sanity checks | Passed |
| Performance benchmark execution | Passed |

Full report: [reports/validation_report.md](reports/validation_report.md)

## Performance Benchmark Summary

Benchmarks use deterministic synthetic events and were measured on local hardware. Results depend on hardware, Python version, operating system, and machine load. The readable reference implementation remains available; the optimised path is benchmarked separately so matching throughput is not mixed with dashboard, snapshot, or reporting overhead.

| Benchmark mode | Events | Reference events/sec | Optimised events/sec | Improvement | p95 latency (us) | Peak memory (MB) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Core matching | 100,000 | 164,745 | 721,152 | 4.38x | 2.70 | 2.59 |
| Replay minimal | 100,000 | 95,781 | 641,741 | 6.70x | 1.56 | 5.99 |
| Full system | 100,000 | n/a | 50,814 | n/a | 19.68 | 142.53 |
| Core matching | 1,000,000 | n/a | 692,787 | n/a | 2.90 | 22.79 |

Previous committed 100,000-event full-loop baseline was approximately 11,500 events/sec. The optimised 100,000-event core matching benchmark processed 721,152 events/sec, a 62.7x improvement over that baseline and a 4.4x improvement over the current readable reference core benchmark while preserving deterministic price-time priority and replay parity.

Full results: [reports/benchmark_results.csv](reports/benchmark_results.csv), [reports/performance_report.md](reports/performance_report.md), and [reports/profile_report.md](reports/profile_report.md)

## Dashboard Screenshots

The Streamlit dashboard is designed as a premium dark trading analytics interface with custom styling, terminal-style ladder views, dark Plotly charts, metric cards, status badges, and page-like sections.

| Section | Screenshot path |
| --- | --- |
| Order book ladder | `docs/images/order_book_ladder.png` |
| Matching engine demo | `docs/images/matching_engine_demo.png` |
| Market replay | `docs/images/market_replay.png` |
| Execution algorithms | `docs/images/execution_algorithms.png` |
| Slippage analysis | `docs/images/slippage_analysis.png` |
| Strategy backtest | `docs/images/strategy_backtest.png` |
| Performance benchmark | `docs/images/performance_benchmark.png` |

![Order book ladder](docs/images/order_book_ladder.png)
![Matching engine demo](docs/images/matching_engine_demo.png)
![Market replay](docs/images/market_replay.png)
![Execution algorithms](docs/images/execution_algorithms.png)
![Slippage analysis](docs/images/slippage_analysis.png)
![Strategy backtest](docs/images/strategy_backtest.png)
![Performance benchmark](docs/images/performance_benchmark.png)

If these images are absent after a clean checkout, see [docs/images/README.md](docs/images/README.md) for the refresh checklist.

## Architecture

```text
src/lob_engine/
|-- core/          # orders, events, reference book/engine, fast book/engine
|-- analytics/     # microstructure, liquidity, slippage, transaction costs
|-- execution/     # TWAP, VWAP, POV, implementation shortfall
|-- simulation/    # synthetic generator, replay, fast replay, fill simulator, backtester
|-- strategies/    # market making, mean reversion, momentum examples
`-- utils/         # validation, performance, profiling, plotting, I/O
```

## Module Map

| Module | Purpose |
| --- | --- |
| `lob_engine.core.orders` | Validated order, cancel, and modify/replace request models |
| `lob_engine.core.order_book` | Bid/ask books, FIFO levels, snapshots, depth, cancellation |
| `lob_engine.core.matching_engine` | Price-time priority matching and trade records |
| `lob_engine.core.fast_order_book` | Tick-normalised optimised book with heap-cached best prices and lazy cancellation |
| `lob_engine.core.fast_matching_engine` | Lightweight integer-code matching path for performance benchmarks |
| `lob_engine.simulation.market_generator` | Reproducible synthetic market events |
| `lob_engine.simulation.market_replay` | Sequential event replay without lookahead |
| `lob_engine.simulation.fast_replay` | Prepared-record replay path for core and minimal replay benchmarks |
| `lob_engine.execution` | Parent-order slicing and execution summaries |
| `lob_engine.analytics` | Microstructure, slippage, and transaction cost metrics |
| `lob_engine.simulation.backtester` | Strategy loop with cash, inventory, P&L, and fills |
| `lob_engine.utils.validation` | Deterministic validation, parity checks, and report generation |
| `lob_engine.utils.performance` | Reference/optimised benchmark modes and profiling workflow |
| `app/streamlit_app.py` | Dashboard and visual analytics interface |

## Installation

```bash
git clone https://github.com/husaam-atq/limit-order-book-trading-engine.git
cd limit-order-book-trading-engine
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Optional acceleration dependencies can be installed with:

```bash
python -m pip install -e ".[dev,accel]"
```

The package works without optional acceleration dependencies.

## Run Tests

```bash
python -m compileall src app examples
python -m pytest -v
python -m ruff check .
python -m black --check .
```

## Run Validation, Profiling, And Benchmarks

```bash
python examples/generate_validation_report.py
```

This writes:

- [reports/validation_report.md](reports/validation_report.md)
- [reports/benchmark_results.csv](reports/benchmark_results.csv)
- [reports/performance_report.md](reports/performance_report.md)
- [reports/profile_report.md](reports/profile_report.md)
- [reports/execution_results.csv](reports/execution_results.csv)
- [data/sample_market_events.csv](data/sample_market_events.csv)
- [data/sample_execution_schedule.csv](data/sample_execution_schedule.csv)

## Run The Dashboard

```bash
streamlit run app/streamlit_app.py
```

Dashboard sections:

- Project overview
- Live order book demo
- Matching engine demo
- Market replay
- Microstructure analytics
- Execution algorithms comparison
- Slippage and transaction cost analysis
- Strategy backtest
- Performance benchmarks
- Validation results

## Example Usage

```python
from lob_engine.core.matching_engine import MatchingEngine
from lob_engine.core.orders import Order, OrderType, Side

engine = MatchingEngine()
engine.process_order(Order("ASK-1", Side.SELL, OrderType.LIMIT, 100, 100.05, timestamp=1))
result = engine.process_order(Order("BUY-1", Side.BUY, OrderType.MARKET, 40, timestamp=2))

print(result.trades[0].price, result.trades[0].quantity)
print(engine.book.top_n_levels(5))
```

More examples:

```bash
python examples/run_order_book_demo.py
python examples/run_matching_engine_demo.py
python examples/run_execution_algorithms.py
python examples/run_market_replay.py
python examples/run_strategy_backtest.py
```

## Notebooks

| Notebook | Focus |
| --- | --- |
| `01_order_book_basics.ipynb` | Book structure, depth, cancellation, snapshots |
| `02_matching_engine_validation.ipynb` | Priority rules, market orders, crossing limits, partial fills |
| `03_execution_algorithms.ipynb` | TWAP, VWAP, POV, implementation shortfall comparison |
| `04_market_replay_and_slippage.ipynb` | Synthetic replay, microstructure time series, fill simulation |

Execute from the repository root:

```bash
python -m jupyter nbconvert --to notebook --execute notebooks/01_order_book_basics.ipynb --output executed_01_order_book_basics.ipynb
python -m jupyter nbconvert --to notebook --execute notebooks/02_matching_engine_validation.ipynb --output executed_02_matching_engine_validation.ipynb
python -m jupyter nbconvert --to notebook --execute notebooks/03_execution_algorithms.ipynb --output executed_03_execution_algorithms.ipynb
python -m jupyter nbconvert --to notebook --execute notebooks/04_market_replay_and_slippage.ipynb --output executed_04_market_replay_and_slippage.ipynb
```

## Results And Interpretation

The validation suite targets deterministic matching-engine correctness and reproducible replay behaviour. The synthetic strategy examples are included to demonstrate infrastructure, accounting, and analytics workflows. They do not imply live profitability and should not be interpreted as alpha research.

Performance results show that a clear reference implementation and a faster Python path can coexist. The optimised path improves core benchmark throughput by removing pandas from the hot loop, avoiding per-event snapshots, caching best prices, using tick-normalised integer prices, and reducing order allocation overhead. The code favours clarity, deterministic validation, and modular design over exchange-grade low-latency engineering.

## Limitations

- Synthetic events are not a substitute for full-depth historical exchange data.
- Queue position, hidden liquidity, auctions, order amendments, self-trade prevention, and exchange-specific edge cases are simplified.
- The backtesting layer is intentionally compact and designed for infrastructure demonstration.
- Benchmark results are machine-specific and should be regenerated on the target environment.
- The optimised benchmark path is designed for reproducible synthetic workloads and does not include venue connectivity, persistence, risk checks, or exchange-specific edge cases.
- Strategies are simple examples and not trading recommendations.

## Future Improvements

- Add tree-backed price levels or a compiled extension for larger books and heavier cancellation loads.
- Add exchange-specific order types, tick-size tables, and session calendars.
- Add historical data adapters for public LOBSTER-style or exchange sample datasets.
- Extend fill models with queue position and adverse selection.
- Expand optional acceleration for analytics hot paths while retaining the pure-Python path.
- Add richer transaction cost calibration from empirical spreads and volatility.


## Purpose

This repository is intended to show practical trading systems engineering: clean models, deterministic matching rules, reproducible validation, testing discipline, execution analytics, benchmark reporting, and a dashboard suitable for explaining the system visually.
