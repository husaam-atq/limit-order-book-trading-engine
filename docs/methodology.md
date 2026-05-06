# Methodology

## Order Book Mechanics

The order book stores visible limit orders on separate bid and ask books. Each price level is a FIFO queue, and an order lookup table maps order IDs to live resting orders for cancellation and replacement.

## Price-Time Priority

Matching follows standard price-time priority:

- Buy orders interact with the lowest available ask first.
- Sell orders interact with the highest available bid first.
- At the same price level, the oldest resting order is filled first.

## Matching Logic

Market orders execute immediately against available opposite-side liquidity. Any unfilled market-order remainder is cancelled. Limit orders execute immediately if they cross the spread. Any unfilled crossing-limit remainder can rest in the book at its limit price.

## Market and Limit Orders

Market orders require side and quantity but no limit price. Limit orders require side, quantity, and a positive limit price. Invalid side, type, quantity, or price inputs are rejected during model construction.

## Partial Fills

When incoming quantity exceeds the best available level, the engine fills across multiple price levels until the incoming order is filled, no eligible liquidity remains, or a limit price constraint prevents further matching.

## Execution Algorithms

TWAP splits a parent order evenly over time. VWAP allocates according to an expected volume curve. POV caps child orders at a target percentage of observed market volume. The implementation-shortfall schedule front-loads participation according to an urgency parameter.

## Slippage and Implementation Shortfall

Slippage is measured side-aware against a benchmark price. For buys, paying above the benchmark is positive slippage cost. For sells, selling below the benchmark is positive slippage cost. Implementation shortfall is measured against the arrival midpoint or arrival reference price.

## Synthetic Data Limitations

The synthetic market generator creates reproducible event streams with clustered volatility, changing liquidity regimes, cancellations, and order-flow imbalance. It is useful for systems validation, but it does not reproduce every empirical property of real exchange data.

## Performance Benchmark Methodology

Benchmarks measure synthetic event processing through both the readable reference implementation and the optimised benchmark path. Runtime, throughput, latency percentiles, trade count, resting order count, and peak memory are recorded. Results depend on hardware, Python version, operating system, and current machine load.

Benchmark modes are separated deliberately:

- Core matching measures direct order book and matching-engine processing with prepared events and no snapshots.
- Replay minimal measures sequential replay without per-event analytics snapshots.
- Full system includes replay, trade capture, snapshots, and report-oriented DataFrame outputs.
- Analytics measures post-replay metric calculation separately.

The optimised path uses tick-normalised integer prices, integer-coded event fields, heap-cached best bid/ask prices, lazy cancellation cleanup, and lightweight slotted records. It is validated against the reference engine with deterministic parity tests before benchmark results are reported.

## Profiling Methodology

The profiling workflow uses timed components plus cProfile/pstats to separate matching work from report generation overhead. It profiles order creation, order book add/cancel, matching-engine processing, market replay, snapshot generation, analytics calculation, and the optimised core loop. The profile report highlights repeated sorting/scanning, object allocation, pandas row access, and per-event snapshot generation as distinct bottleneck categories.
