"""Plotly chart helpers used by examples and the dashboard."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

PLOTLY_TEMPLATE = "plotly_dark"


def apply_dark_layout(fig: go.Figure, title: str | None = None) -> go.Figure:
    """Apply a consistent dark trading-dashboard layout."""

    fig.update_layout(
        template=PLOTLY_TEMPLATE,
        title=title,
        paper_bgcolor="#0b1020",
        plot_bgcolor="#101827",
        font={"color": "#e5eefb", "family": "Inter, Segoe UI, sans-serif"},
        margin={"l": 40, "r": 24, "t": 56 if title else 28, "b": 40},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
    )
    fig.update_xaxes(gridcolor="rgba(148,163,184,0.16)", zerolinecolor="rgba(148,163,184,0.2)")
    fig.update_yaxes(gridcolor="rgba(148,163,184,0.16)", zerolinecolor="rgba(148,163,184,0.2)")
    return fig


def depth_chart(ladder: pd.DataFrame) -> go.Figure:
    """Return a horizontal order book depth chart."""

    fig = go.Figure()
    if not ladder.empty:
        bids = ladder[ladder["side"].isin(["bid", "buy"])]
        asks = ladder[ladder["side"].isin(["ask", "sell"])]
        fig.add_bar(y=bids["price"], x=-bids["quantity"], orientation="h", name="Bid depth", marker_color="#19c37d")
        fig.add_bar(y=asks["price"], x=asks["quantity"], orientation="h", name="Ask depth", marker_color="#ff5c7a")
    fig.update_layout(barmode="relative", xaxis_title="Quantity", yaxis_title="Price")
    return apply_dark_layout(fig, "Order Book Depth")


def time_series_chart(frame: pd.DataFrame, x: str, y_columns: list[str], title: str) -> go.Figure:
    """Return a multi-line time series chart."""

    fig = go.Figure()
    for column in y_columns:
        if column in frame:
            fig.add_scatter(x=frame[x], y=frame[column], mode="lines", name=column.replace("_", " ").title())
    return apply_dark_layout(fig, title)
