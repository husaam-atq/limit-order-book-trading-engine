# Profile Report

Profile workload: 10,000 deterministic synthetic events.

## Timed Workflow Components

| component | runtime_seconds | runtime_share_pct |
| --- | --- | --- |
| order_creation | 0.007 | 0.538 |
| order_book_add_cancel | 0.006 | 0.430 |
| reference_process_order | 0.037 | 2.684 |
| reference_market_replay_full | 0.939 | 68.650 |
| snapshot_generation | 0.170 | 12.419 |
| analytics_calculation | 0.197 | 14.438 |
| optimised_core_matching | 0.012 | 0.841 |

## cProfile Top Functions

```text
231269 function calls in 0.079 seconds

   Ordered by: cumulative time
   List reduced from 38 to 20 due to restriction <20>

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    0.001    0.001    0.091    0.091 performance.py:408(_run_reference_core)
    10000    0.007    0.000    0.089    0.000 performance.py:434(_process_reference_action)
     8798    0.006    0.000    0.059    0.000 matching_engine.py:67(process_order)
     8798    0.014    0.000    0.047    0.000 matching_engine.py:131(_match)
     8798    0.006    0.000    0.017    0.000 orders.py:72(__post_init__)
     8159    0.008    0.000    0.017    0.000 matching_engine.py:170(_record_trade)
     8798    0.005    0.000    0.010    0.000 orders.py:16(from_value)
     4279    0.004    0.000    0.005    0.000 order_book.py:49(add_order)
    16318    0.005    0.000    0.005    0.000 orders.py:107(record_fill)
     6428    0.001    0.000    0.003    0.000 order_book.py:118(best_bid)
     8770    0.002    0.000    0.003    0.000 enum.py:720(__call__)
    14116    0.003    0.000    0.003    0.000 {built-in method builtins.min}
     6085    0.001    0.000    0.003    0.000 order_book.py:123(best_ask)
     6303    0.002    0.000    0.002    0.000 {built-in method builtins.max}
     1023    0.001    0.000    0.002    0.000 matching_engine.py:94(process_cancel)
     8798    0.001    0.000    0.002    0.000 orders.py:36(from_value)
    17429    0.002    0.000    0.002    0.000 {method 'append' of 'list' objects}
    17596    0.001    0.000    0.001    0.000 {built-in method builtins.isinstance}
     8770    0.001    0.000    0.001    0.000 enum.py:1128(__new__)
     9536    0.001    0.000    0.001    0.000 {method 'get' of 'dict' objects}
```

## Bottleneck Findings

- Reference replay constructs Python dataclass objects for events and orders inside the hot loop.
- `DataFrame.iterrows()` and pandas row access are slower than prepared records or `itertuples()`.
- The reference book calls `min()`/`max()` over price dictionaries to find best prices, which becomes expensive as book size grows.
- Per-event `book_metrics()` performs repeated depth calculations and sorting, mixing analytics/reporting with matching.
- Trade and snapshot DataFrame construction is useful for analysis but should be outside core matching benchmarks.
- Cancellations in the reference book rebuild price-level queues, while the optimised path uses lazy O(1) cancellation.

## Optimisation Response

- Added an optimised matching path with integer event codes, tick prices, heap-cached best bid/ask, and lightweight order records.
- Added benchmark modes that separate core matching, minimal replay, full-system replay, and analytics.
- Retained the readable reference engine and added parity tests to protect price-time priority and deterministic replay.
