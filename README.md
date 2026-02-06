# ⚡ StockBotFree

**Manual Scalp Execution Agent** — A trading chatbot connected to Alpaca via Model Context Protocol (MCP) with risk controls, signal engine, and multi-agent strategies.

> ⚠️ **Disclaimer:** This project is for educational and engineering purposes only. Automated trading can cause substantial losses. Use paper trading first and implement strict risk controls. Not investment advice.

---

## Architecture

```
User → React SPA / Streamlit UI
         ↓
FastAPI Backend (REST + WebSocket)
         ↓
LLM (OpenAI / Anthropic / Ollama) → Tool Calls
         ↓
MCP Client → Alpaca MCP Server → Alpaca Trading API (paper/live)
```

**Key principle:** Only ONE component submits orders. All signal modules output structured recommendations that the meta-controller combines into a single trade proposal with human approval.

## Features

| Feature | Status |
|---------|--------|
| Alpaca paper trading via MCP | ✅ |
| LLM chat with trade tool-calling | ✅ |
| Human approval gate (CLI) | ✅ |
| FinBERT sentiment analysis | ✅ |
| Technical forecaster (RSI, MACD, ATR, Bollinger, VWAP) | ✅ |
| Meta-controller (weighted signal consensus) | ✅ |
| Risk limits (daily loss, position size, symbol allowlist) | ✅ |
| Kill switch (cancel all + close all) | ✅ |
| Audit logging (JSONL) | ✅ |
| Market screener (finvizfinance) | ✅ |
| Multi-agent framework (7 strategies) | ✅ |
| Broker abstraction layer | ✅ |
| React + Vite frontend (code-split) | ✅ |
| Streamlit dashboard | ✅ |
| RL policy module | 🟡 Stub |
| API authentication | ❌ |
| Slippage tracking | ❌ |

## Quick Start

### Prerequisites
- Python 3.13+
- Node.js 18+
- Alpaca paper trading account

### Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ALPACA_API_KEY=your_paper_key
export ALPACA_SECRET_KEY=your_paper_secret
export ALPACA_BASE_URL=https://paper-api.alpaca.markets
export LLM_PROVIDER=openai  # or anthropic, ollama
export OPENAI_API_KEY=your_key

# Start the API server
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

### Frontend (React)
```bash
cd frontend
npm install
npm run dev       # Development at http://localhost:5173
npm run build     # Production build
```

### Frontend (Streamlit)
```bash
streamlit run app/web_ui.py --server.port 8501
```

## Project Structure

```
app/
  api.py                  # FastAPI REST + WebSocket endpoints
  settings.py             # Centralized configuration (pydantic-settings)
  llm.py                  # LLM wrapper with trade tool-calling
  mcp_client.py           # Alpaca MCP client (stdio transport)
  web_ui.py               # Streamlit trading dashboard
  tools/
    alpaca_tools.py       # Typed Alpaca MCP tool wrappers
  strategy/
    signal_schema.py      # Unified Signal schema (Pydantic)
    sentiment.py          # FinBERT sentiment module
    forecaster.py         # Technical forecaster (RSI, MACD, ATR, etc.)
    rl_policy.py          # RL policy stub (Phase 2)
    meta_controller.py    # Weighted signal consensus + risk checks
    screener.py           # Market screener via finvizfinance
    trading_agents_adapter.py  # Optional TradingAgents integration
  risk/
    limits.py             # Risk limit validations
    approvals.py          # Human approval gate (Rich CLI)
    kill_switch.py        # Emergency halt mechanism
  storage/
    audit_log.py          # Structured JSONL audit logging
    state.py              # Session state management
  agents/
    agent.py              # Autonomous trading agent lifecycle
    agent_config.py       # Per-agent configuration
    agent_state.py        # Per-agent P&L and trade tracking
    base_strategy.py      # Abstract strategy base class
    registry.py           # Agent registry singleton
    strategies/           # 7 built-in strategies
  brokers/
    base.py               # BrokerInterface ABC
    alpaca_broker.py      # Alpaca MCP broker implementation
frontend/                 # React + Vite + Tailwind SPA
tests/                    # Unit tests (pytest)
scripts/                  # E2E test scripts
```

## Risk Controls

- **Daily loss limit:** -$100 hard stop (no new trades)
- **Position size:** Max 5% of equity per position
- **Open orders:** Max 10 concurrent
- **Symbol allowlist:** Configurable per-env
- **Kill switch:** Cancel all orders + close all positions
- **Human approval:** Required before every order submission

## Implementation Status

See [`IMPLEMENTATION_STATUS.md`](./IMPLEMENTATION_STATUS.md) for the full audit against the original blueprint, including:
- Phase-by-phase completion status
- Critical gaps in security, testing, monitoring, documentation
- Prioritized action plan

**Summary:** Phase 0-1 (core pipeline) = 100% complete. Phase 2-3 (safety hardening) = partial. 13/32 requirements complete, 9 partial, 10 missing. 10 extra features beyond blueprint.

## Testing

```bash
# Unit tests
pytest tests/ -v

# Phase 0 E2E test (requires Alpaca MCP server running)
python -m scripts.test_e2e_phase0

# Phase 1 signal tests (requires Alpaca MCP server running)
python -m scripts.test_phase1_signals
```

## License

Educational use only. See disclaimer above.

