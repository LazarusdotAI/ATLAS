const BASE = '/api'

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(`${BASE}${path}`, window.location.origin)
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v))
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// Types
export interface Account {
  equity: number; buying_power: number; cash: number;
  daily_pnl: number; account_type: string; broker: string;
}
export interface Position {
  symbol: string; qty: number; side: string;
  entry_price: number; current_price: number;
  market_value: number; unrealised_pnl: number;
}
export interface Clock {
  is_open: boolean; next_open?: string; next_close?: string; timestamp?: string;
}
export interface ChatReply { reply: string; actions: Record<string, unknown>[]; intent?: string; }
export interface ScreenResult { tickers: string[]; signals: Record<string, unknown>[]; }
export interface AutonomousStatus {
  running: boolean; strategy?: string; symbols?: string[];
  scan_interval?: number; trades_today?: number; errors?: number;
}
export interface KillSwitchInfo {
  active: boolean; reason?: string; activated_at?: string;
  orders_cancelled?: number; positions_closed?: number;
}

// API calls
export const api = {
  // Account & positions
  account: () => get<Account>('/account'),
  positions: () => get<Position[]>('/positions'),
  orders: (status?: string, limit = 20) =>
    get<Record<string, unknown>[]>('/orders', {
      ...(status ? { status } : {}), limit: String(limit),
    }),
  clock: () => get<Clock>('/clock'),
  health: () => get<{ status: string }>('/health'),

  // Chat
  chat: (message: string, context?: { role: string; content: string }[]) =>
    post<ChatReply>('/chat', { message, context }),

  // Screener
  screen: (preset = 'scalp_long', limit = 50) =>
    post<ScreenResult>('/screen', { preset, limit, analyze: true }),

  // Kill switch
  killSwitch: (reason = 'Manual trigger from UI') =>
    post<KillSwitchInfo>('/kill-switch', { reason }),
  killSwitchStatus: () => get<KillSwitchInfo>('/kill-switch'),

  // Autonomous trading
  autonomousStatus: () => get<AutonomousStatus>('/autonomous/status'),
  autonomousStart: (config?: { symbols?: string[]; strategy?: string; scan_interval_seconds?: number }) =>
    post<{ status: string }>('/autonomous/start', config ?? {}),
  autonomousStop: () => post<{ status: string }>('/autonomous/stop'),

  // Chat-powered analysis (these use the /chat endpoint with specific prompts)
  technicalAnalysis: (symbol: string) =>
    post<ChatReply>('/chat', { message: `technical analysis for ${symbol}` }),
  consensus: (symbol: string) =>
    post<ChatReply>('/chat', { message: `what do all signals say about ${symbol}` }),
  tradePlan: (symbol: string, side: string) =>
    post<ChatReply>('/chat', { message: `generate a ${side} trade plan for ${symbol}` }),
  backtest: (symbol: string, strategy: string) =>
    post<ChatReply>('/chat', { message: `backtest ${strategy} strategy on ${symbol}` }),
  earningsPlaybook: (symbol: string) =>
    post<ChatReply>('/chat', { message: `earnings playbook for ${symbol}` }),
  sentiment: (symbol: string) =>
    post<ChatReply>('/chat', { message: `sentiment analysis for ${symbol}` }),
}

