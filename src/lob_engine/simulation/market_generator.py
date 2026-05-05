"""Reproducible synthetic market event generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SyntheticMarketConfig:
    """Configuration for synthetic event generation."""

    num_events: int = 10_000
    seed: int = 42
    start_price: float = 100.0
    tick_size: float = 0.01
    base_order_size: int = 100
    symbol: str = "SYNTH"
    volatility_regime_probability: float = 0.03
    liquidity_regime_probability: float = 0.04


def _round_to_tick(price: float, tick_size: float) -> float:
    return round(round(price / tick_size) * tick_size, 8)


def generate_market_events(config: SyntheticMarketConfig | None = None) -> pd.DataFrame:
    """Generate synthetic limit, market, cancel, and modify events."""

    cfg = config or SyntheticMarketConfig()
    if cfg.num_events <= 0:
        raise ValueError("Number of events must be positive.")
    rng = np.random.default_rng(cfg.seed)
    rows: list[dict[str, object]] = []
    active_ids: list[str] = []
    mid = cfg.start_price
    volatility = 0.015
    liquidity_multiplier = 1.0
    imbalance_bias = 0.0
    timestamp = 0.0
    next_id = 1

    def next_order_id(prefix: str) -> str:
        nonlocal next_id
        order_id = f"{prefix}{next_id:08d}"
        next_id += 1
        return order_id

    # Seed both sides of the book with visible liquidity.
    for level in range(1, 16):
        for side, sign in (("buy", -1), ("sell", 1)):
            timestamp += 0.001
            price = _round_to_tick(mid + sign * (level + 1) * cfg.tick_size, cfg.tick_size)
            quantity = int(cfg.base_order_size * (1.5 + rng.random()))
            order_id = next_order_id("L")
            active_ids.append(order_id)
            rows.append(
                {
                    "timestamp": timestamp,
                    "event_type": "limit",
                    "order_id": order_id,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "trader_id": f"MM{level:02d}",
                    "target_order_id": None,
                    "symbol": cfg.symbol,
                }
            )

    remaining = max(cfg.num_events - len(rows), 0)
    for idx in range(remaining):
        timestamp += float(rng.exponential(0.05))
        if rng.random() < cfg.volatility_regime_probability:
            volatility = float(rng.choice([0.008, 0.015, 0.035, 0.06]))
        if rng.random() < cfg.liquidity_regime_probability:
            liquidity_multiplier = float(rng.choice([0.5, 0.8, 1.2, 1.8]))
        if idx % 250 == 0:
            imbalance_bias = float(rng.uniform(-0.35, 0.35))

        mid += float(rng.normal(0.0, volatility))
        mid = max(mid, cfg.tick_size * 10)
        side = "buy" if rng.random() < 0.5 + imbalance_bias / 2 else "sell"
        event_draw = rng.random()

        if event_draw < 0.64:
            distance = int(rng.integers(1, 9))
            sign = -1 if side == "buy" else 1
            price = _round_to_tick(mid + sign * distance * cfg.tick_size, cfg.tick_size)
            quantity = max(1, int(rng.gamma(2.0, cfg.base_order_size * liquidity_multiplier / 2)))
            order_id = next_order_id("L")
            active_ids.append(order_id)
            rows.append(
                {
                    "timestamp": timestamp,
                    "event_type": "limit",
                    "order_id": order_id,
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "trader_id": f"T{rng.integers(1, 25):02d}",
                    "target_order_id": None,
                    "symbol": cfg.symbol,
                }
            )
        elif event_draw < 0.88:
            quantity = max(1, int(rng.gamma(1.6, cfg.base_order_size / 2)))
            rows.append(
                {
                    "timestamp": timestamp,
                    "event_type": "market",
                    "order_id": next_order_id("M"),
                    "side": side,
                    "quantity": quantity,
                    "price": None,
                    "trader_id": f"TAKER{rng.integers(1, 12):02d}",
                    "target_order_id": None,
                    "symbol": cfg.symbol,
                }
            )
        elif event_draw < 0.98 and active_ids:
            target_index = int(rng.integers(0, len(active_ids)))
            target_id = active_ids.pop(target_index)
            rows.append(
                {
                    "timestamp": timestamp,
                    "event_type": "cancel",
                    "order_id": next_order_id("C"),
                    "side": None,
                    "quantity": None,
                    "price": None,
                    "trader_id": f"T{rng.integers(1, 25):02d}",
                    "target_order_id": target_id,
                    "symbol": cfg.symbol,
                }
            )
        elif active_ids:
            target_id = active_ids[int(rng.integers(0, len(active_ids)))]
            side_for_price = side
            sign = -1 if side_for_price == "buy" else 1
            price = _round_to_tick(mid + sign * int(rng.integers(1, 10)) * cfg.tick_size, cfg.tick_size)
            quantity = max(1, int(rng.gamma(2.0, cfg.base_order_size * liquidity_multiplier / 2)))
            rows.append(
                {
                    "timestamp": timestamp,
                    "event_type": "modify",
                    "order_id": next_order_id("R"),
                    "side": None,
                    "quantity": quantity,
                    "price": price,
                    "trader_id": f"T{rng.integers(1, 25):02d}",
                    "target_order_id": target_id,
                    "symbol": cfg.symbol,
                }
            )

    columns = [
        "timestamp",
        "event_type",
        "order_id",
        "side",
        "quantity",
        "price",
        "trader_id",
        "target_order_id",
        "symbol",
    ]
    return pd.DataFrame(rows, columns=columns).head(cfg.num_events)


def write_sample_market_events(path: str | Path, num_events: int = 5_000, seed: int = 42) -> pd.DataFrame:
    """Generate and persist a sample event file."""

    events = generate_market_events(SyntheticMarketConfig(num_events=num_events, seed=seed))
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    events.to_csv(output, index=False)
    return events
