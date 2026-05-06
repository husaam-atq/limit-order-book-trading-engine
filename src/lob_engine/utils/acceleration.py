"""Optional numeric acceleration helpers."""

from __future__ import annotations

import numpy as np

try:  # pragma: no cover - depends on optional local installation
    from numba import njit

    NUMBA_AVAILABLE = True
except Exception:  # pragma: no cover - exercised when Numba is not installed
    njit = None
    NUMBA_AVAILABLE = False


if NUMBA_AVAILABLE:  # pragma: no cover - optional path

    @njit(cache=True)
    def _latency_summary_numba(latencies_ns):
        values = np.sort(latencies_ns.astype(np.float64) / 1000.0)
        n = len(values)
        avg = 0.0
        for value in values:
            avg += value
        avg /= n
        p50 = values[int(round((n - 1) * 0.50))]
        p95 = values[int(round((n - 1) * 0.95))]
        p99 = values[int(round((n - 1) * 0.99))]
        return avg, p50, p95, p99


def latency_summary_us(latencies_ns: np.ndarray) -> tuple[float, float, float, float]:
    """Return average, p50, p95, and p99 latency in microseconds."""

    if len(latencies_ns) == 0:
        return np.nan, np.nan, np.nan, np.nan
    if NUMBA_AVAILABLE and len(latencies_ns) >= 250_000:  # pragma: no cover - optional path
        avg, p50, p95, p99 = _latency_summary_numba(latencies_ns)
        return float(avg), float(p50), float(p95), float(p99)
    latencies_us = latencies_ns.astype("float64") / 1_000.0
    return (
        float(latencies_us.mean()),
        float(np.percentile(latencies_us, 50)),
        float(np.percentile(latencies_us, 95)),
        float(np.percentile(latencies_us, 99)),
    )
