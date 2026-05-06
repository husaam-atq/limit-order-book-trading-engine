# Validation Report

Deterministic validation checks passed: **14/14**.

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
| Reference vs optimised parity | True | Matched 745 trades and 95 live orders. |
| Optimised replay determinism | True | Fast replay produced 756 identical trades. |
| Execution algorithms | True | TWAP sums, VWAP curve, POV cap, and shortfall calculation validated. |
| Transaction cost analytics | True | Buy slippage 100.0 bps; sell slippage 100.0 bps. |
| Backtester sanity checks | True | Ending equity 1004986.11; reproducible=True. |
| Performance benchmark | True | Processed 1,000 events at 598,086 events/sec. |

## Benchmark Summary

| benchmark_mode | events | reference_events_per_second | optimised_events_per_second | improvement_multiple |
| --- | --- | --- | --- | --- |
| core_matching | 100000 | 164744.863 | 721151.593 | 4.377 |
| replay_minimal | 100000 | 95781.303 | 641741.430 | 6.700 |
| full_system | 100000 | nan | 50814.077 | nan |
| analytics | 100000 | 40072.170 | nan | nan |

## Benchmark Targets

| events_per_second | met_50k | met_100k | met_250k |
| --- | --- | --- | --- |
| 721151.593 | True | True | True |

## Full Benchmark Results

| implementation_path | benchmark_mode | event_count | processed_events | runtime_seconds | events_per_second | avg_latency_us | p50_latency_us | p95_latency_us | p99_latency_us | peak_memory_mb | trades | resting_orders | numba_available |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| reference | core_matching | 1000 | 1000 | 0.004 | 278691.266 | 3.476 | 2.400 | 7.700 | 11.205 | 0.254 | 742 | 113 | False |
| reference | replay_minimal | 1000 | 1000 | 0.009 | 116222.310 | 8.605 | 8.605 | 8.605 | 8.605 | 0.567 | 742 | 113 | False |
| reference | full_system | 1000 | 1000 | 0.074 | 13551.623 | 73.793 | 73.793 | 73.793 | 73.793 | 1.879 | 742 | 113 | False |
| optimised | core_matching | 1000 | 1000 | 0.001 | 701311.452 | 1.313 | 1.100 | 2.500 | 3.801 | 0.101 | 742 | 113 | False |
| optimised | replay_minimal | 1000 | 1000 | 0.002 | 653893.939 | 1.530 | 1.530 | 1.530 | 1.530 | 0.118 | 742 | 113 | False |
| optimised | full_system | 1000 | 1000 | 0.014 | 69820.213 | 14.324 | 14.324 | 14.324 | 14.324 | 1.354 | 742 | 113 | False |
| reference | analytics | 1000 | 1000 | 0.020 | 49189.843 | 20.330 | 20.330 | 20.330 | 20.330 | 1.548 | 0 | 0 | False |
| reference | core_matching | 10000 | 10000 | 0.039 | 255649.208 | 3.804 | 2.500 | 8.300 | 14.100 | 2.201 | 8159 | 415 | False |
| reference | replay_minimal | 10000 | 10000 | 0.119 | 84117.802 | 11.888 | 11.888 | 11.888 | 11.888 | 5.257 | 8159 | 415 | False |
| reference | full_system | 10000 | 10000 | 0.965 | 10367.648 | 96.454 | 96.454 | 96.454 | 96.454 | 18.804 | 8159 | 415 | False |
| optimised | core_matching | 10000 | 10000 | 0.013 | 757874.314 | 1.229 | 1 | 2.500 | 3.700 | 0.396 | 8159 | 415 | False |
| optimised | replay_minimal | 10000 | 10000 | 0.013 | 770606.005 | 1.298 | 1.298 | 1.298 | 1.298 | 0.718 | 8159 | 415 | False |
| optimised | full_system | 10000 | 10000 | 0.165 | 60427.671 | 16.549 | 16.549 | 16.549 | 16.549 | 13.807 | 8159 | 415 | False |
| reference | analytics | 10000 | 10000 | 0.189 | 52839.321 | 18.925 | 18.925 | 18.925 | 18.925 | 15.716 | 0 | 0 | False |
| reference | core_matching | 100000 | 100000 | 0.607 | 164744.863 | 5.931 | 3.900 | 13.200 | 23.600 | 21.584 | 86118 | 929 | False |
| reference | replay_minimal | 100000 | 100000 | 1.044 | 95781.303 | 10.440 | 10.440 | 10.440 | 10.440 | 52.031 | 86118 | 929 | False |
| optimised | core_matching | 100000 | 100000 | 0.139 | 721151.593 | 1.292 | 1 | 2.700 | 4.300 | 2.592 | 86118 | 929 | False |
| optimised | replay_minimal | 100000 | 100000 | 0.156 | 641741.430 | 1.558 | 1.558 | 1.558 | 1.558 | 5.990 | 86118 | 929 | False |
| optimised | full_system | 100000 | 100000 | 1.968 | 50814.077 | 19.680 | 19.680 | 19.680 | 19.680 | 142.532 | 86118 | 929 | False |
| reference | analytics | 100000 | 100000 | 2.495 | 40072.170 | 24.955 | 24.955 | 24.955 | 24.955 | 161.523 | 0 | 0 | False |
| optimised | core_matching | 500000 | 500000 | 0.818 | 611426.709 | 1.527 | 1.100 | 3.400 | 5.500 | 11.698 | 434932 | 2009 | False |
| optimised | replay_minimal | 500000 | 500000 | 0.856 | 584400.322 | 1.711 | 1.711 | 1.711 | 1.711 | 29.074 | 434932 | 2009 | False |
| optimised | core_matching | 1000000 | 1000000 | 1.443 | 692786.664 | 1.345 | 1 | 2.900 | 4.600 | 22.786 | 868101 | 2557 | False |
| optimised | replay_minimal | 1000000 | 1000000 | 1.491 | 670505.804 | 1.491 | 1.491 | 1.491 | 1.491 | 57.873 | 868101 | 2557 | False |

## Sample Data

- Sample market events: 5,000 rows
- Event data is synthetic and reproducible from a fixed seed.
- Synthetic results are useful for infrastructure validation, not evidence of live trading performance.
