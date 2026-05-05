# Validation Report

Deterministic validation checks passed: **12/12**.

The validation suite exercises price-time priority, price priority, market and limit matching, partial fills, cancellations, microstructure metrics, deterministic replay, execution schedules, transaction cost calculations, backtester accounting, and benchmark execution.

## Validation Checks

| check | passed | detail |
| --- | --- | --- |
| Price-time priority | True | Passive fill order: ['A-old', 'A-new'], quantities: [10, 5]. |
| Price priority | True | First execution price: [101.0]. |
| Market order matching | True | Market buy consumed asks upward; market sell consumed bids downward. |
| Limit order crossing | True | Crossing limit executed; non-crossing limit rested. |
| Partial fills | True | Market remainder cancelled; crossing limit remainder rested. |
| Cancel order | True | Existing order removed; unknown cancel rejected with message. |
| Book metrics | True | Top-level imbalance 0.142857, weighted mid 100.0143. |
| Replay determinism | True | Replay produced 358 identical trades across two runs. |
| Execution algorithms | True | TWAP sums, VWAP curve, POV cap, and shortfall calculation validated. |
| Transaction cost analytics | True | Buy slippage 100.0 bps; sell slippage 100.0 bps. |
| Backtester sanity checks | True | Ending equity 1004986.11; reproducible=True. |
| Performance benchmark | True | Processed 1,000 events at 13,258 events/sec. |

## Benchmark Summary

| event_count | processed_events | runtime_seconds | events_per_second | avg_latency_us | p50_latency_us | p95_latency_us | p99_latency_us | peak_memory_mb | trades | resting_orders |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1000 | 1000 | 0.091 | 11021.725 | 16.238 | 12 | 36.710 | 62.150 | 0.639 | 742 | 113 |
| 10000 | 10000 | 0.843 | 11868.575 | 15.890 | 12.800 | 37 | 57.101 | 6.131 | 8159 | 415 |
| 100000 | 100000 | 8.696 | 11499.863 | 17.040 | 14 | 39.700 | 63.500 | 60.919 | 86118 | 929 |

## Sample Data

- Sample market events: 5,000 rows
- Event data is synthetic and reproducible from a fixed seed.
- Synthetic results are useful for infrastructure validation, not evidence of live trading performance.
