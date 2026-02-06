# StockBotFree — System Architecture

> High-level guide to recreate this multi-agent autonomous trading system.

---

## 1. Overview

StockBotFree is a **multi-agent AI trading system** with two independent execution paths:

1. **Chat Path** — User sends natural language → intent detection → handler → LLM → trade execution with human approval
2. **Autonomous Path** — AI engine loops continuously → strategy generates signals → risk checks → direct execution

Both paths share: **Broker abstraction**, **Risk controls**, **Audit logging**, and **Session state**.

```
┌─────────────────────────────────────────────────────┐
│                    FRONTEND (React)                  │
│  Dashboard │ Chat │ Orders │ Screener                │
│  Strategy Manager │ Signal Consensus │ Kill Switch   │
└───────────────────────┬─────────────────────────────┘
                        │ REST + WebSocket
┌───────────────────────▼─────────────────────────────┐
│                  FASTAPI BACKEND                     │
│                                                      │
│  ┌──────────────┐    ┌──────────────────────┐       │
│  │  CHAT PATH   │    │  AUTONOMOUS PATH     │       │
│  │  /chat POST  │    │  AutonomousTrader    │       │
│  │  Intent →    │    │  loop → Strategy →   │       │
│  │  Handler →   │    │  Signal → Execute    │       │
│  │  LLM →       │    │                      │       │
│  │  Approval    │    │  7 Strategies:       │       │
│  └──────┬───────┘    │  Technical, Momentum │       │
│         │            │  Breakout, MeanRev   │       │
│         │            │  Sentiment, Scalping │       │
│         │            │  EarningsPlaybook    │       │
│         │            └──────────┬───────────┘       │
│         │                       │                    │
│  ┌──────▼───────────────────────▼──────────────┐    │
│  │         BROKER INTERFACE (ABC)               │    │
│  │  get_account │ get_positions │ submit_order  │    │
│  │  get_orders  │ cancel_order  │ call_tool     │    │
│  └──────────────────────┬──────────────────────┘    │
│                         │                            │
│  ┌──────────────────────▼──────────────────────┐    │
│  │         ALPACA BROKER (MCP Client)           │    │
│  │  stdio transport → 44 Alpaca tools          │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  SHARED: Risk │ Kill Switch │ Audit │ State  │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## 2. Directory Structure

```
app/
├── api.py                    # FastAPI REST + WebSocket endpoints
├── llm.py                    # LLM wrapper: intent detection → handlers → response
├── chat_handlers.py          # 10 intent handlers (account, positions, etc.)
├── settings.py               # Environment config (.env loading)
├── brokers/
│   ├── base.py               # BrokerInterface ABC
│   ├── alpaca_broker.py       # Alpaca MCP implementation
│   └── __init__.py            # get_broker() factory
├── mcp_client.py              # Raw AlpacaMCPClient (stdio transport)
├── agents/
│   ├── agent.py               # Base agent class
│   ├── autonomous_trader.py   # Autonomous loop (singleton)
│   ├── base_strategy.py       # BaseStrategy ABC
│   ├── registry.py            # Strategy registry
│   └── strategies/            # 7 strategy implementations
├── strategy/
│   ├── forecaster.py          # Technical indicators + FinGPT
│   ├── sentiment.py           # FinBERT + FinBERT-Tone NLP
│   ├── rl_policy.py           # Stable-Baselines3 RL
│   ├── meta_controller.py     # Weighted voting consensus
│   └── screener.py            # Finviz market scanner
├── risk/
│   ├── pre_trade.py           # Pre-trade risk checks
│   └── kill_switch.py         # Emergency stop
├── tools/
│   └── alpaca_tools.py        # 13 typed tool wrappers (get_bars, etc.)
├── data/
│   └── earnings_calendar.py   # Earnings date database
├── storage/
│   ├── state.py               # Session state singleton
│   └── audit_log.py           # Trade audit trail
├── monitoring/
│   └── anomaly.py             # Anomaly detection
└── middleware/
    └── auth.py                # API key authentication

frontend/
├── design-system.pen          # Pencil.dev design tokens (source of truth)
├── src/
│   ├── index.css              # CSS custom properties from .pen
│   ├── api.ts                 # TypeScript API client
│   ├── App.tsx                # React Router setup
│   ├── components/
│   │   ├── Layout.tsx         # Sidebar + header + outlet
│   │   ├── ui/                # Atomic components (Card, Button, Badge, etc.)
│   │   └── panels/            # Dashboard panels (Strategy, Signals, etc.)

---

## 3. Chat Path (Manual Trading)

**Flow:** `POST /chat` → `process_chat_message()` → `detect_intent()` → handler → LLM → response

### Intent Detection
`app/llm.py:detect_intent()` uses keyword matching to route messages:

| Intent | Keywords | Handler |
|--------|----------|---------|
| `account` | "account", "equity", "balance" | `handle_account()` |
| `positions` | "positions", "holdings" | `handle_positions()` |
| `orders` | "orders", "history" | `handle_orders()` |
| `technical_analysis` | "technical", "rsi", "macd" | `handle_technical()` |
| `consensus` | "consensus", "all models" | `handle_consensus()` |
| `sentiment` | "sentiment", "finbert" | `handle_sentiment()` |
| `screener` | "screen", "scan" | `handle_screener()` |
| `earnings` | "earnings", "playbook" | `handle_earnings()` |
| `backtest` | "backtest" | `handle_backtest()` |
| `kill_switch` | "kill", "emergency" | `handle_kill_switch()` |
| `trade_execute` | "buy", "sell" | Passthrough to LLM |
| `general` | (default) | Passthrough to LLM |

### Trade Execution
When intent is `trade_execute`:
1. LLM generates structured trade action via `_extract_trade_action()`
2. `run_all_checks()` validates: kill switch, market hours, position limits, daily loss
3. If approved → `broker.submit_order()` → audit log
4. Response includes confirmation with fill details

---

## 4. Autonomous Path (AI Trading)

**Flow:** `AutonomousTrader.start()` → loop → strategy → signal → risk → execute

### AutonomousTrader (Singleton)
- Located in `app/agents/autonomous_trader.py`
- Uses `asyncio.Task` for background execution
- Controlled via `/autonomous/start` and `/autonomous/stop` API endpoints
- Requires `AUTONOMOUS_MODE_ENABLED=true` in `.env`

### 7 Built-in Strategies
All extend `BaseStrategy` from `app/agents/base_strategy.py`:

| Strategy | File | Signal Logic |
|----------|------|-------------|
| Technical | `strategies/technical.py` | RSI + MACD + Bollinger crossover |
| Momentum | `strategies/momentum.py` | Price momentum with volume surge |
| Breakout | `strategies/breakout.py` | Range breakout with ATR filter |
| Mean Reversion | `strategies/mean_reversion.py` | Bollinger band mean reversion |
| Sentiment | `strategies/sentiment.py` | FinBERT news sentiment scoring |
| SMB Scalping | `strategies/smb_scalping.py` | Tape-reading scalp patterns |
| Earnings Playbook | `strategies/earnings_playbook.py` | Pre/post earnings volatility |

### Signal Schema (Pydantic)
Every strategy produces a unified signal:
```python
class Signal:
    direction: str      # "LONG" | "SHORT" | "NEUTRAL"
    confidence: float   # 0.0 to 1.0
    stop_level: float   # Stop loss price
    target_level: float # Take profit price
    source: str         # Strategy name
    rationale: str      # Human-readable explanation
```

---

## 5. Signal Engine (4 Modules)

Used by the **chat path** for consensus analysis:

| Module | Weight | Source |
|--------|--------|--------|
| Forecaster (Technical + FinGPT) | 0.45 | `strategy/forecaster.py` |
| Sentiment (FinBERT) | 0.25 | `strategy/sentiment.py` |
| RL Policy (Stable-Baselines3) | 0.10 | `strategy/rl_policy.py` |
| TradingAgents | 0.40 | `strategy/trading_agents_adapter.py` |

**Meta-Controller** (`strategy/meta_controller.py`) performs weighted voting:
```python
score = sum(signal.confidence * weight for signal, weight in zip(signals, weights))
direction = "LONG" if score > threshold else "SHORT" if score < -threshold else "NEUTRAL"
```

---

## 6. Broker Abstraction

### BrokerInterface ABC (`app/brokers/base.py`)
```python
class BrokerInterface(ABC):
    async def connect(self) -> None
    async def disconnect(self) -> None
    async def get_account(self) -> AccountInfo
    async def get_positions(self) -> List[PositionInfo]
    async def get_orders(self, status, limit) -> List[dict]
    async def submit_order(self, symbol, qty, side, type, ...) -> dict
    async def cancel_order(self, order_id) -> dict
    async def get_clock(self) -> dict
    async def call_tool(self, name, arguments) -> Any  # Raw MCP tool access
```

### AlpacaBroker (`app/brokers/alpaca_broker.py`)
- Wraps `AlpacaMCPClient` (stdio transport to Alpaca MCP server)
- `call_tool()` delegates to internal `_call()` method
- 44 available MCP tools (orders, positions, bars, assets, etc.)

---

## 7. Risk Controls

| Control | Location | Rule |
|---------|----------|------|
| Daily loss limit | `risk/pre_trade.py` | -$100 net P&L hard stop |
| Position size | `risk/pre_trade.py` | Max 5% of equity per trade |
| Max concurrent | `risk/pre_trade.py` | Max 10 open orders |
| Symbol allowlist | `risk/pre_trade.py` | Configurable allowed symbols |
| Market hours | `risk/pre_trade.py` | NYSE 09:30-16:00 ET only |
| Kill switch | `risk/kill_switch.py` | Cancel all + close all |
| Human approval | `llm.py` | Required for chat-path trades |
| Anomaly detection | `monitoring/anomaly.py` | Statistical outlier alerts |

---

## 8. Frontend Architecture

### Design System (Pencil.dev)
The design system is defined in `frontend/design-system.pen` (v2.0.0) and compiled to CSS custom properties in `frontend/src/index.css`.

**Color Palette:**
| Token | Value | Usage |
| ----- | ----- | ----- |
| `--color-bg` | `#0B0E11` | Page background |
| `--color-bg-card` | `#141820` | Card surfaces |
| `--color-bg-elevated` | `#1A2030` | Elevated elements |
| `--color-accent-green` | `#00D4AA` | Profit, success, active |
| `--color-accent-red` | `#FF6B6B` | Loss, danger, kill switch |
| `--color-accent-amber` | `#F0B429` | Warnings, confirmations |
| `--color-accent-blue` | `#58A6FF` | Info, user messages |
| `--color-accent-purple` | `#D2A8FF` | AI/model badges |

**Typography:** Inter (sans), JetBrains Mono (monospace)
**Spacing:** 4px base scale (`--space-1` = 4px through `--space-12` = 48px)

### Component Hierarchy
```
App.tsx (React Router)
└── Layout.tsx (sidebar + header + outlet)
    ├── Dashboard.tsx (main trading dashboard)
    │   ├── KPICard × 4 (equity, P&L, buying power, positions)
    │   ├── AutonomousToggle (start/stop engine)
    │   ├── KillSwitchPanel (emergency stop)
    │   ├── P&L Chart (Recharts area chart)
    │   ├── PositionsPanel (open positions table)
    │   ├── StrategyManager (7 strategies with controls)
    │   ├── QuickChat (LLM assistant)
    │   ├── SignalConsensus (multi-model analysis)
    │   ├── TechnicalPanel (indicator display)
    │   └── EarningsPanel (playbook + backtest)
    ├── Chat.tsx (full chat page)
    ├── Orders.tsx (order history)
    └── Screener.tsx (market scanner)
```

### Atomic UI Components (`frontend/src/components/ui/`)
`Card`, `Button`, `Badge`, `KPICard`, `StatusDot`, `DataTable`, `FilterBar`, `LoadingFallback`

### State Management
- **No Redux/Zustand** — uses `useState` + polling (`setInterval` every 10s)
- Dashboard polls: account, positions, autonomous status, kill switch status
- Analysis panels are on-demand (user triggers fetch)

---

## 9. API Endpoints

All endpoints served by FastAPI at `http://localhost:8000`.

| Method | Path | Purpose |
| ------ | ---- | ------- |
| GET | `/health` | Health check (returns kill switch status) |
| GET | `/account` | Account info (equity, P&L, buying power) |
| GET | `/positions` | Open positions list |
| GET | `/orders` | Order history |
| POST | `/chat` | Chat message → intent → handler → LLM response |
| POST | `/screen` | Market screener (finviz presets) |
| POST | `/kill-switch` | Trigger emergency stop |
| GET | `/kill-switch/status` | Kill switch state |
| GET | `/autonomous/status` | Autonomous engine state |
| POST | `/autonomous/start` | Start autonomous trading loop |
| POST | `/autonomous/stop` | Stop autonomous trading loop |
| WS | `/ws` | WebSocket for real-time updates |

---

## 10. How to Run

### Prerequisites
- Python 3.11+
- Node.js 18+
- Alpaca paper trading account (API key + secret)

### Environment Setup (`.env`)
```env
ALPACA_API_KEY=your_key
ALPACA_API_SECRET=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets
LLM_API_KEY=your_openai_or_compatible_key
LLM_MODEL=gpt-4o-mini
AUTONOMOUS_MODE_ENABLED=false
DAILY_LOSS_LIMIT=-100
MAX_POSITION_PCT=0.05
MAX_CONCURRENT_ORDERS=10
```

### Start Backend
```bash
pip install -r requirements.txt
uvicorn app.api:app --host 0.0.0.0 --port 8000
```

### Start Frontend
```bash
cd frontend
npm install
npm run dev          # dev server on http://localhost:5173
# npm run build      # production build → dist/
```

---

## 11. How to Add a New Strategy

1. Create `app/agents/strategies/my_strategy.py`:
```python
from app.agents.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    name = "my_strategy"

    async def generate_signal(self, symbol: str, broker) -> Signal:
        # Fetch data via broker.call_tool("get_stock_bars", {...})
        # Compute indicators
        # Return Signal(direction, confidence, stop, target, source, rationale)
        ...
```

2. Register in `app/agents/registry.py`:
```python
from app.agents.strategies.my_strategy import MyStrategy
STRATEGY_REGISTRY["my_strategy"] = MyStrategy
```

3. The strategy will automatically appear in the `StrategyManager` panel
   and be available for the autonomous engine.

---

## 12. Key Design Decisions

| Decision | Rationale |
| -------- | --------- |
| MCP (Model Context Protocol) for Alpaca | Standard tool-calling interface; 44 tools available without manual REST wrappers |
| BrokerInterface ABC | Swap brokers (Alpaca → IBKR) without changing strategy/signal code |
| Two execution paths | Chat = human-in-loop safety; Autonomous = speed for scalping |
| Weighted consensus | No single model is always right; blending 4 sources reduces false signals |
| Pydantic signals | Type-safe, serializable, testable; every signal follows the same schema |
| Pencil.dev design tokens | Single source of truth for UI; change `.pen` file → CSS vars cascade everywhere |
| Polling (not WebSocket for UI) | Simpler state management; 10s interval is fast enough for dashboard; WS available for real-time when needed |
