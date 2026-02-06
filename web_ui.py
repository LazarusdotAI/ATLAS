"""
StockBotFree — Professional Trading Dashboard.

A modern, dark-themed trading interface powered by Streamlit + Plotly.
Connects to the FastAPI backend at http://localhost:8000.

Run:
    streamlit run app/web_ui.py --server.port 8501
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
import plotly.graph_objects as go
import streamlit as st

# ── Configuration ─────────────────────────────────────────────

API_BASE = "http://localhost:8000"
POLL_INTERVAL = 10  # seconds between auto-refresh

# ── Color palette ─────────────────────────────────────────────

C_BG = "#0E1117"
C_CARD = "#161B22"
C_BORDER = "#30363D"
C_TEXT = "#E6EDF3"
C_MUTED = "#8B949E"
C_GREEN = "#00D4AA"
C_RED = "#FF6B6B"
C_AMBER = "#F0B429"
C_BLUE = "#58A6FF"
C_PURPLE = "#BC8CFF"

# ── HTTP helpers ──────────────────────────────────────────────


def _api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | list | None:
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _api_post(path: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any] | None:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=json or {}, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


# ── Session state init ────────────────────────────────────────

for key, default in {
    "messages": [],
    "context": [],
    "pending_action": None,
    "auto_refresh": True,
    "pnl_history": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Page config ───────────────────────────────────────────────

st.set_page_config(
    page_title="StockBotFree — Trading Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────

st.markdown("""
<style>
    .block-container { padding-top: 1.5rem; }
    div[data-testid="stMetric"] {
        background: #161B22; border: 1px solid #30363D;
        border-radius: 10px; padding: 12px 16px;
    }
    div[data-testid="stMetric"] label {
        color: #8B949E; font-size: 0.72rem;
        text-transform: uppercase; letter-spacing: 0.05em;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        font-size: 1.35rem; font-weight: 700;
    }
    section[data-testid="stSidebar"] {
        background: #0D1117; border-right: 1px solid #21262D;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px; background: #161B22;
        border-radius: 10px; padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px; padding: 8px 16px; font-weight: 600;
    }
    .stChatMessage { border-radius: 10px; }
    hr { border-color: #21262D !important; opacity: 0.4; }
</style>
""", unsafe_allow_html=True)


# ── Helper: Plotly P&L mini-chart ─────────────────────────────

def _pnl_spark(history: List[Dict]) -> go.Figure:
    """Tiny spark-line of intraday P&L for the sidebar."""
    times = [h["time"] for h in history]
    vals = [h["pnl"] for h in history]
    colors = [C_GREEN if v >= 0 else C_RED for v in vals]
    fig = go.Figure(go.Scatter(
        x=times, y=vals, mode="lines",
        line=dict(color=C_GREEN if (vals[-1] if vals else 0) >= 0 else C_RED, width=2),
        fill="tozeroy",
        fillcolor="rgba(0,212,170,0.08)" if (vals[-1] if vals else 0) >= 0 else "rgba(255,107,107,0.08)",
    ))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=60,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        showlegend=False,
    )
    return fig


# ── Sidebar ──────────────────────────────────────────────────

with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center; padding:8px 0 2px;">
        <span style="font-size:2rem;">⚡</span>
        <h2 style="margin:0;color:{C_TEXT};font-weight:800;letter-spacing:-0.02em;">StockBotFree</h2>
        <p style="color:{C_MUTED};font-size:0.78rem;margin:0;">Manual Scalp Execution Agent</p>
    </div>""", unsafe_allow_html=True)
    st.divider()

    # ── Account ──
    acct = _api_get("/account")
    if acct:
        equity = acct.get("equity", 0)
        pnl = acct.get("daily_pnl", 0)
        bp = acct.get("buying_power", 0)
        st.session_state.pnl_history.append({"time": datetime.now().strftime("%H:%M:%S"), "pnl": pnl, "equity": equity})
        st.session_state.pnl_history = st.session_state.pnl_history[-100:]
        pnl_c = C_GREEN if pnl >= 0 else C_RED
        st.markdown(f"""
        <div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;padding:14px;margin-bottom:10px;">
            <div style="color:{C_MUTED};font-size:0.68rem;text-transform:uppercase;letter-spacing:0.05em;">Portfolio Value</div>
            <div style="color:{C_TEXT};font-size:1.5rem;font-weight:800;">${equity:,.2f}</div>
            <div style="display:flex;justify-content:space-between;margin-top:8px;">
                <div><div style="color:{C_MUTED};font-size:0.62rem;text-transform:uppercase;">Day P&L</div>
                    <div style="color:{pnl_c};font-size:1rem;font-weight:700;">${pnl:+,.2f}</div></div>
                <div><div style="color:{C_MUTED};font-size:0.62rem;text-transform:uppercase;">Buying Power</div>
                    <div style="color:{C_BLUE};font-size:1rem;font-weight:700;">${bp:,.2f}</div></div>
            </div>
        </div>""", unsafe_allow_html=True)
        if len(st.session_state.pnl_history) > 2:
            st.plotly_chart(_pnl_spark(st.session_state.pnl_history), use_container_width=True, config={"displayModeBar": False})
        if pnl <= -80:
            st.error(f"⛔ P&L ${pnl:,.2f} — NEAR -$100 HARD STOP!")
        elif pnl <= -50:
            st.warning(f"⚠️ P&L ${pnl:,.2f} — caution")
    else:
        st.info("Backend offline — start `uvicorn app.api:app --port 8000`")
    st.divider()

    # ── Positions ──
    positions = _api_get("/positions")
    st.markdown(f"<div style='color:{C_MUTED};font-size:0.7rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;'>📊 Open Positions</div>", unsafe_allow_html=True)
    if positions and len(positions) > 0:
        for p in positions:
            pv = p.get("unrealised_pnl", 0)
            pc = C_GREEN if pv >= 0 else C_RED
            st.markdown(f"""<div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:8px;padding:10px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;"><span style="color:{C_TEXT};font-weight:700;">{p['symbol']}</span>
                <span style="color:{pc};font-weight:700;">${pv:+,.2f}</span></div>
                <div style="color:{C_MUTED};font-size:0.72rem;">{p.get('qty',0)} {p.get('side','?')} @ ${p.get('entry_price',0):,.2f} → ${p.get('current_price',0):,.2f}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.caption("No open positions")
    st.divider()

    # ── Market clock ──
    clock = _api_get("/clock")
    if clock:
        is_open = clock.get("is_open", False)
        dot = f"<span style='color:{C_GREEN};'>●</span>" if is_open else f"<span style='color:{C_RED};'>●</span>"
        label = "MARKET OPEN" if is_open else "MARKET CLOSED"
        st.markdown(f"<div style='font-size:0.85rem;font-weight:700;color:{C_TEXT};'>{dot} {label}</div>", unsafe_allow_html=True)
        nxt = clock.get("next_open") if not is_open else clock.get("next_close")
        if nxt:
            st.caption(f"{'Opens' if not is_open else 'Closes'}: {nxt}")
    st.divider()

    # ── Kill switch ──
    ks = _api_get("/kill-switch")
    if ks and ks.get("active"):
        st.error(f"🚨 KILL SWITCH ACTIVE — {ks.get('reason','N/A')}")
    else:
        if st.button("🛑 EMERGENCY STOP", type="primary", use_container_width=True):
            r = _api_post("/kill-switch", {"reason": "Manual trigger from Web UI"})
            if r:
                st.error("Kill switch triggered!")
                st.rerun()
    st.divider()
    st.toggle("Auto-refresh", key="auto_refresh")
    if st.button("🔄 Refresh now"):
        st.rerun()

# ── Main area ────────────────────────────────────────────────

# KPI banner
if acct:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("💎 Equity", f"${equity:,.2f}")
    k2.metric("📈 Day P&L", f"${pnl:,.2f}", delta=f"${pnl:+,.2f}",
              delta_color="normal" if pnl >= 0 else "inverse")
    k3.metric("💰 Buying Power", f"${bp:,.2f}")
    mkt_label = "OPEN" if (clock and clock.get("is_open")) else "CLOSED"
    k4.metric("⏱️ Market", mkt_label)

tab_dash, tab_chat, tab_screener, tab_orders = st.tabs(
    ["📊 Dashboard", "💬 Chat", "🔍 Screener", "📜 Orders"])

# ━━━━━━━━━━━━━━━━━━━━━ DASHBOARD TAB ━━━━━━━━━━━━━━━━━━━━━━━
with tab_dash:
    if len(st.session_state.pnl_history) > 2:
        hist = st.session_state.pnl_history
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[h["time"] for h in hist], y=[h["pnl"] for h in hist],
            mode="lines+markers", name="P&L",
            line=dict(color=C_GREEN, width=2.5), marker=dict(size=4),
            fill="tozeroy", fillcolor="rgba(0,212,170,0.10)",
        ))
        fig.add_hline(y=0, line_dash="dot", line_color=C_MUTED, opacity=0.5)
        fig.add_hline(y=-100, line_dash="dash", line_color=C_RED, opacity=0.7,
                      annotation_text="Hard Stop -$100", annotation_position="bottom left")
        fig.update_layout(
            title=dict(text="Intraday P&L", font=dict(size=16, color=C_TEXT)),
            template="plotly_dark", paper_bgcolor=C_CARD, plot_bgcolor=C_CARD,
            font=dict(color=C_TEXT, size=11),
            margin=dict(l=40, r=20, t=50, b=30), height=320,
            xaxis=dict(gridcolor="#21262D", title=""),
            yaxis=dict(gridcolor="#21262D", title="P&L ($)", tickprefix="$"),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True, key="pnl_chart")
    else:
        st.markdown(f"""<div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;
            padding:40px;text-align:center;margin:20px 0;">
            <div style="font-size:2rem;margin-bottom:8px;">📊</div>
            <div style="color:{C_MUTED};font-size:0.9rem;">P&L chart will appear as data accumulates</div>
        </div>""", unsafe_allow_html=True)

    if acct:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""<div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;padding:16px;">
                <div style="color:{C_MUTED};font-size:0.7rem;text-transform:uppercase;">Account Type</div>
                <div style="color:{C_PURPLE};font-size:1.1rem;font-weight:700;">{acct.get('account_type','?').upper()}</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;padding:16px;">
                <div style="color:{C_MUTED};font-size:0.7rem;text-transform:uppercase;">Risk Budget Left</div>
                <div style="color:{C_AMBER};font-size:1.1rem;font-weight:700;">${100 + pnl:,.2f}</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            pc = len(positions) if positions else 0
            st.markdown(f"""<div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;padding:16px;">
                <div style="color:{C_MUTED};font-size:0.7rem;text-transform:uppercase;">Open Positions</div>
                <div style="color:{C_BLUE};font-size:1.1rem;font-weight:700;">{pc}</div>
            </div>""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━ CHAT TAB ━━━━━━━━━━━━━━━━━━━━━━━━━
with tab_chat:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("actions"):
                for act in msg["actions"]:
                    if act.get("action") == "trade_proposed" and act.get("status") == "awaiting_approval":
                        order = act.get("order", {})
                        ca, cb = st.columns(2)
                        with ca:
                            if st.button(f"✅ CONFIRM {order.get('side','').upper()} "
                                         f"{order.get('qty','')} {order.get('symbol','')}",
                                         key=f"confirm_{msg.get('ts', id(msg))}", type="primary"):
                                st.session_state.messages.append({"role": "user", "content": "CONFIRM"})
                                st.session_state.context.append({"role": "user", "content": "CONFIRM"})
                                resp = _api_post("/chat", {"message": "CONFIRM", "context": st.session_state.context[-20:]})
                                if resp:
                                    st.session_state.messages.append({"role": "assistant", "content": resp["reply"], "actions": resp.get("actions", [])})
                                    st.session_state.context.append({"role": "assistant", "content": resp["reply"]})
                                act["status"] = "confirmed"
                                st.rerun()
                        with cb:
                            if st.button("❌ Cancel", key=f"cancel_{msg.get('ts', id(msg))}"):
                                st.session_state.messages.append({"role": "user", "content": "CANCEL"})
                                st.session_state.context.append({"role": "user", "content": "CANCEL"})
                                act["status"] = "cancelled"
                                st.session_state.messages.append({"role": "assistant", "content": "Trade cancelled.", "actions": []})
                                st.rerun()

    if prompt := st.chat_input("Enter trade command or question…"):
        ts = time.time()
        st.session_state.messages.append({"role": "user", "content": prompt, "ts": ts})
        st.session_state.context.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                resp = _api_post("/chat", {"message": prompt, "context": st.session_state.context[-20:]})
            if resp:
                reply = resp.get("reply", "No response.")
                actions = resp.get("actions", [])
                st.markdown(reply)
                st.session_state.messages.append({"role": "assistant", "content": reply, "actions": actions, "ts": time.time()})
                st.session_state.context.append({"role": "assistant", "content": reply})
            else:
                fb = "⚠️ Could not reach backend. Is `uvicorn app.api:app` running?"
                st.warning(fb)
                st.session_state.messages.append({"role": "assistant", "content": fb, "actions": []})

# ━━━━━━━━━━━━━━━━━━━━━━ SCREENER TAB ━━━━━━━━━━━━━━━━━━━━━━━
with tab_screener:
    col_p, col_l, col_a = st.columns(3)
    with col_p:
        preset = st.selectbox("Preset", ["scalp_long", "scalp_short", "momentum"])
    with col_l:
        limit = st.slider("Max tickers", 10, 100, 50)
    with col_a:
        analyze = st.checkbox("Run technical analysis", value=True)

    if st.button("🔍 Run Screener", type="primary"):
        with st.spinner("Scanning market…"):
            result = _api_post("/screen", {"preset": preset, "limit": limit, "analyze": analyze})
        if result:
            tickers = result.get("tickers", [])
            st.success(f"Found {len(tickers)} tickers: {', '.join(tickers[:20])}{'…' if len(tickers) > 20 else ''}")
            signals = result.get("signals", [])
            if signals:
                st.markdown(f"<div style='color:{C_MUTED};font-size:0.72rem;text-transform:uppercase;margin:14px 0 6px;letter-spacing:0.05em;'>Top Signals</div>", unsafe_allow_html=True)
                for sig in signals[:15]:
                    d = sig.get("direction", "neutral")
                    ic = {"long": "🟢", "short": "🔴"}.get(d, "⚪")
                    conf = sig.get("confidence", 0)
                    sym = sig.get("symbol", "?")
                    dc = C_GREEN if d == "long" else C_RED if d == "short" else C_MUTED
                    st.markdown(f"""<div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:8px;padding:12px;margin-bottom:6px;">
                        <div style="display:flex;justify-content:space-between;align-items:center;">
                            <span style="color:{C_TEXT};font-weight:700;font-size:0.95rem;">{ic} {sym}</span>
                            <span style="color:{dc};font-weight:600;font-size:0.85rem;">{d.upper()} {conf:.0%}</span>
                        </div>
                        <div style="color:{C_MUTED};font-size:0.75rem;margin-top:4px;">
                            Stop: {sig.get('stop_level','N/A')} &nbsp;|&nbsp; Target: {sig.get('target_level','N/A')}
                        </div>
                    </div>""", unsafe_allow_html=True)
        else:
            st.warning("No results or backend unreachable.")

# ━━━━━━━━━━━━━━━━━━━━━━━ ORDERS TAB ━━━━━━━━━━━━━━━━━━━━━━━━
with tab_orders:
    order_status = st.selectbox("Filter", ["all", "open", "closed", "filled", "cancelled"])
    status_param = None if order_status == "all" else order_status
    orders_data = _api_get("/orders", params={"status": status_param, "limit": 30})
    if orders_data and len(orders_data) > 0:
        import pandas as pd
        df = pd.DataFrame(orders_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    elif orders_data is not None:
        st.markdown(f"""<div style="background:{C_CARD};border:1px solid {C_BORDER};border-radius:10px;
            padding:30px;text-align:center;">
            <div style="color:{C_MUTED};font-size:0.9rem;">No orders found</div>
        </div>""", unsafe_allow_html=True)
    else:
        st.info("Connect backend to view orders.")

# ── Auto-refresh ──────────────────────────────────────────────
if st.session_state.auto_refresh:
    time.sleep(POLL_INTERVAL)
    st.rerun()
