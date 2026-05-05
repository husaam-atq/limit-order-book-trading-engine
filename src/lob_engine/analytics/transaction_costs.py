"""Transaction cost models used by execution simulations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TransactionCostBreakdown:
    """Transaction cost components in price terms and basis points."""

    spread_cost: float
    market_impact: float
    commission: float
    total_cost: float
    total_cost_bps: float


def spread_cost(spread: float, half_spread_capture: float = 1.0) -> float:
    """Return half-spread cost per share for aggressive execution."""

    if spread < 0:
        raise ValueError("Spread cannot be negative.")
    if half_spread_capture < 0:
        raise ValueError("Half-spread capture cannot be negative.")
    return spread * 0.5 * half_spread_capture


def estimate_market_impact(
    quantity: float, average_daily_volume: float, volatility: float, impact_coefficient: float = 0.1
) -> float:
    """Estimate market impact with a square-root style model."""

    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")
    if average_daily_volume <= 0:
        raise ValueError("Average daily volume must be positive.")
    if volatility < 0:
        raise ValueError("Volatility cannot be negative.")
    return impact_coefficient * volatility * (quantity / average_daily_volume) ** 0.5


def commission_cost(quantity: float, commission_per_share: float = 0.0005) -> float:
    """Return total commission in currency units."""

    if quantity < 0:
        raise ValueError("Quantity cannot be negative.")
    if commission_per_share < 0:
        raise ValueError("Commission cannot be negative.")
    return quantity * commission_per_share


def total_transaction_cost(
    quantity: float,
    price: float,
    spread: float,
    average_daily_volume: float,
    volatility: float,
    commission_per_share: float = 0.0005,
    impact_coefficient: float = 0.1,
) -> TransactionCostBreakdown:
    """Return a simple transaction cost breakdown."""

    if quantity <= 0:
        raise ValueError("Quantity must be positive.")
    if price <= 0:
        raise ValueError("Price must be positive.")
    spread_component = spread_cost(spread)
    impact_component = estimate_market_impact(quantity, average_daily_volume, volatility, impact_coefficient)
    commission_component = commission_cost(quantity, commission_per_share) / quantity
    total_per_share = spread_component + impact_component + commission_component
    return TransactionCostBreakdown(
        spread_cost=spread_component,
        market_impact=impact_component,
        commission=commission_component,
        total_cost=total_per_share * quantity,
        total_cost_bps=total_per_share / price * 10_000,
    )
