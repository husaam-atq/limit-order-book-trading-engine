"""Reusable Streamlit UI components for the dashboard."""

from __future__ import annotations

import html

import streamlit as st


def inject_css() -> None:
    """Apply the dashboard visual system."""

    st.markdown(
        """
        <style>
        :root {
            --bg: #060914;
            --panel: rgba(15, 23, 42, 0.82);
            --panel-strong: rgba(17, 24, 39, 0.96);
            --line: rgba(148, 163, 184, 0.18);
            --text: #e5eefb;
            --muted: #8ea4c8;
            --cyan: #4dd7fa;
            --green: #19c37d;
            --red: #ff5c7a;
            --amber: #f6c35b;
            --violet: #9b8cff;
        }

        .stApp {
            background:
                radial-gradient(circle at 20% 0%, rgba(77, 215, 250, 0.10), transparent 28rem),
                radial-gradient(circle at 80% 12%, rgba(155, 140, 255, 0.09), transparent 32rem),
                linear-gradient(135deg, #050711 0%, #08111f 55%, #050711 100%);
            color: var(--text);
        }

        [data-testid="stHeader"] {
            background: rgba(6, 9, 20, 0.72);
            backdrop-filter: blur(16px);
            border-bottom: 1px solid rgba(148, 163, 184, 0.08);
        }

        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(6, 9, 20, 0.98), rgba(12, 18, 32, 0.98));
            border-right: 1px solid rgba(148, 163, 184, 0.14);
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] p {
            color: var(--text) !important;
        }

        .block-container {
            padding-top: 3.2rem;
            padding-bottom: 3rem;
            max-width: 1360px;
        }

        h1, h2, h3 {
            letter-spacing: 0;
        }

        div[data-testid="stMetric"] {
            background: rgba(15, 23, 42, 0.72);
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 8px;
            padding: 1rem 1.1rem;
            box-shadow: 0 20px 45px rgba(0, 0, 0, 0.22);
        }

        div[data-testid="stMetric"] label {
            color: var(--muted) !important;
            text-transform: uppercase;
            letter-spacing: .08em;
            font-size: .74rem !important;
        }

        div[data-testid="stMetricValue"] {
            color: var(--text);
            font-weight: 750;
        }

        .hero {
            position: relative;
            overflow: hidden;
            padding: 2rem;
            border: 1px solid rgba(77, 215, 250, 0.22);
            border-radius: 8px;
            background:
                linear-gradient(135deg, rgba(14, 24, 43, 0.94), rgba(7, 13, 27, 0.92)),
                repeating-linear-gradient(90deg, rgba(77, 215, 250, 0.06) 0 1px, transparent 1px 56px);
            box-shadow: 0 28px 80px rgba(0, 0, 0, 0.28), inset 0 1px 0 rgba(255,255,255,0.04);
        }

        .hero:after {
            content: "";
            position: absolute;
            right: -16%;
            top: -40%;
            width: 42rem;
            height: 42rem;
            background: radial-gradient(circle, rgba(77, 215, 250, .10), transparent 64%);
            pointer-events: none;
        }

        .hero-kicker {
            color: var(--cyan);
            text-transform: uppercase;
            letter-spacing: .12em;
            font-size: .76rem;
            font-weight: 700;
        }

        .hero h1 {
            margin: .35rem 0 .5rem;
            font-size: clamp(2rem, 4vw, 4rem);
            line-height: 1;
            color: #f8fbff;
        }

        .hero p {
            max-width: 800px;
            color: #b9c7df;
            font-size: 1.02rem;
            line-height: 1.65;
        }

        .section-title {
            display: flex;
            align-items: center;
            gap: .85rem;
            margin: 2rem 0 1rem;
        }

        .section-rail {
            width: .36rem;
            height: 2.25rem;
            border-radius: 2px;
            background: linear-gradient(180deg, var(--cyan), var(--green));
            box-shadow: 0 0 24px rgba(77, 215, 250, .35);
        }

        .section-title h2 {
            margin: 0;
            color: #f8fbff;
            font-size: 1.45rem;
        }

        .section-title span {
            display: block;
            color: var(--muted);
            font-size: .86rem;
            margin-top: .12rem;
        }

        .panel {
            border: 1px solid var(--line);
            border-radius: 8px;
            background: var(--panel);
            box-shadow: 0 18px 45px rgba(0,0,0,.22);
            padding: 1rem 1.1rem;
        }

        .terminal-panel {
            border: 1px solid rgba(77, 215, 250, .18);
            border-radius: 8px;
            background: linear-gradient(180deg, rgba(3, 7, 18, .96), rgba(9, 14, 27, .96));
            box-shadow: inset 0 1px 0 rgba(255,255,255,.04), 0 18px 45px rgba(0,0,0,.25);
            padding: 1rem;
        }

        .metric-card {
            border: 1px solid var(--line);
            border-radius: 8px;
            padding: 1rem;
            background: linear-gradient(180deg, rgba(15,23,42,.9), rgba(8,13,26,.9));
            min-height: 108px;
        }

        .metric-label {
            color: var(--muted);
            text-transform: uppercase;
            letter-spacing: .08em;
            font-size: .72rem;
            margin-bottom: .55rem;
        }

        .metric-value {
            color: #f8fbff;
            font-size: 1.38rem;
            font-weight: 760;
            line-height: 1.1;
            white-space: nowrap;
        }

        .metric-note {
            color: var(--muted);
            font-size: .82rem;
            margin-top: .5rem;
        }

        .badge {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: .25rem .58rem;
            font-size: .74rem;
            font-weight: 700;
            border: 1px solid rgba(148, 163, 184, .18);
            background: rgba(15, 23, 42, .78);
            color: var(--text);
        }

        .badge-pass {
            color: #b6f7d6;
            border-color: rgba(25, 195, 125, .32);
            background: rgba(25, 195, 125, .10);
        }

        .badge-warn {
            color: #ffe1a0;
            border-color: rgba(246, 195, 91, .32);
            background: rgba(246, 195, 91, .10);
        }

        .lob-table {
            width: 100%;
            border-collapse: collapse;
            font-variant-numeric: tabular-nums;
            overflow: hidden;
            border-radius: 8px;
        }

        .lob-table th {
            color: var(--muted);
            font-size: .72rem;
            text-transform: uppercase;
            letter-spacing: .08em;
            border-bottom: 1px solid var(--line);
            padding: .55rem .65rem;
            text-align: right;
        }

        .lob-table td {
            padding: .48rem .65rem;
            border-bottom: 1px solid rgba(148, 163, 184, .08);
            text-align: right;
        }

        .bid-row td { color: #a9f6d0; background: rgba(25,195,125,.045); }
        .ask-row td { color: #ffc0cc; background: rgba(255,92,122,.045); }

        div.stButton > button,
        div[data-testid="stDownloadButton"] > button {
            border-radius: 6px;
            border: 1px solid rgba(77, 215, 250, .35);
            background: linear-gradient(135deg, rgba(77,215,250,.16), rgba(25,195,125,.10));
            color: #e5eefb;
            font-weight: 700;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: .5rem;
            border-bottom: 1px solid rgba(148, 163, 184, .12);
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 6px 6px 0 0;
            color: var(--muted);
            background: rgba(15,23,42,.55);
            border: 1px solid rgba(148, 163, 184, .10);
        }

        .stTabs [aria-selected="true"] {
            color: #f8fbff;
            border-color: rgba(77, 215, 250, .32);
            background: rgba(77, 215, 250, .10);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def hero(title: str, subtitle: str, kicker: str = "Trading Systems Laboratory") -> None:
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-kicker">{html.escape(kicker)}</div>
            <h1>{html.escape(title)}</h1>
            <p>{html.escape(subtitle)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_header(title: str, subtitle: str | None = None) -> None:
    subtitle_html = "" if subtitle is None else f"<span>{html.escape(subtitle)}</span>"
    st.markdown(
        f"""
        <div class="section-title">
            <div class="section-rail"></div>
            <div><h2>{html.escape(title)}</h2>{subtitle_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def metric_card(label: str, value: str, note: str = "") -> None:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{html.escape(label)}</div>
            <div class="metric-value">{html.escape(value)}</div>
            <div class="metric-note">{html.escape(note)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(label: str, passed: bool = True) -> str:
    klass = "badge-pass" if passed else "badge-warn"
    return f'<span class="badge {klass}">{html.escape(label)}</span>'


def panel_open(kind: str = "panel") -> None:
    st.markdown(f'<div class="{kind}">', unsafe_allow_html=True)


def panel_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def limitation_panel(text: str) -> None:
    st.markdown(
        f"""
        <div class="panel" style="border-color: rgba(246,195,91,.30); background: rgba(246,195,91,.07);">
            <span class="badge badge-warn">Model Risk Note</span>
            <div style="height:.6rem"></div>
            <div style="color:#dbe7fb; line-height:1.55;">{html.escape(text)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def order_ladder_html(ladder) -> str:
    """Return a styled HTML ladder from a top-of-book DataFrame."""

    if ladder.empty:
        return '<div class="terminal-panel">No resting liquidity.</div>'
    rows = []
    asks = ladder[ladder["side"].eq("ask")].sort_values("price", ascending=False)
    bids = ladder[ladder["side"].eq("bid")].sort_values("price", ascending=False)
    for _, row in asks.iterrows():
        rows.append(
            f'<tr class="ask-row"><td>{row["side"].upper()}</td><td>{row["price"]:.2f}</td><td>{int(row["quantity"])}</td><td>{int(row["orders"])}</td></tr>'
        )
    for _, row in bids.iterrows():
        rows.append(
            f'<tr class="bid-row"><td>{row["side"].upper()}</td><td>{row["price"]:.2f}</td><td>{int(row["quantity"])}</td><td>{int(row["orders"])}</td></tr>'
        )
    return (
        '<div class="terminal-panel"><table class="lob-table">'
        "<thead><tr><th>Side</th><th>Price</th><th>Quantity</th><th>Orders</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div>"
    )
