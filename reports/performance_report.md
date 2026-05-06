# Performance Report

Benchmarks separate core matching from replay, analytics, and full-system reporting overhead.
Results are measured on synthetic event streams and depend on hardware, Python version, operating system, and machine load.
Previous committed 100k reference benchmark baseline: 170,258 events/sec.


## Target Summary

| target | met | events_per_second |
| --- | --- | --- |
| 50,000 events/sec | True | 721151.593 |
| 100,000 events/sec | True | 721151.593 |
| 250,000 events/sec | True | 721151.593 |

## Reference vs Optimised Comparison

| benchmark_mode | event_count | reference_events_per_second | optimised_events_per_second | improvement_multiple |
| --- | --- | --- | --- | --- |
| core_matching | 1000 | 278691.266 | 701311.452 | 2.516 |
| core_matching | 10000 | 255649.208 | 757874.314 | 2.965 |
| core_matching | 100000 | 164744.863 | 721151.593 | 4.377 |
| replay_minimal | 1000 | 116222.310 | 653893.939 | 5.626 |
| replay_minimal | 10000 | 84117.802 | 770606.005 | 9.161 |
| replay_minimal | 100000 | 95781.303 | 641741.430 | 6.700 |
| full_system | 1000 | 13551.623 | 69820.213 | 5.152 |
| full_system | 10000 | 10367.648 | 60427.671 | 5.828 |

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

## Bottleneck Summary

- Full profiling details are available in `reports/profile_report.md`.

## Methodology

- `core_matching` measures direct matching-engine processing with prepared events and no snapshots.
- `replay_minimal` measures sequential replay without per-event analytics snapshots.
- `full_system` includes matching, replay, trade capture, snapshots, and DataFrame outputs.
- `analytics` measures post-replay microstructure analytics and report-style calculations separately.
- The optimised path uses integer event codes, tick-normalised prices, heap-cached best prices, lazy cancellation, and optional trade recording.
- The reference path is retained as the readable implementation used by examples, notebooks, dashboard demos, and validation checks.

## Limitations

- The optimised path is still Python and should not be described as exchange-grade or HFT-grade.
- Synthetic event streams do not reproduce all real venue behaviours.
- Per-event latency statistics include Python timing overhead and should be interpreted as benchmark diagnostics.
- Large full-system snapshots can become memory-bound because each event creates reportable analytics state.
