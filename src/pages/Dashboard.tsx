import { useCallback, useEffect, useRef, useState } from 'react'
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'
import { TrendingUp, TrendingDown, DollarSign, BarChart3, ShieldAlert, RefreshCw } from 'lucide-react'
import { api, type Account, type Position, type AutonomousStatus, type KillSwitchInfo } from '../api'
import { KPICard, Card, CardHeader, CardTitle, Button } from '../components/ui'
import {
  StrategyManager, AutonomousToggle, KillSwitchPanel,
  SignalConsensus, TechnicalPanel, EarningsPanel,
  QuickChat, PositionsPanel,
} from '../components/panels'

interface PnlPoint { time: string; pnl: number }

export default function Dashboard() {
  const [acct, setAcct] = useState<Account | null>(null)
  const [positions, setPositions] = useState<Position[]>([])
  const [autoStatus, setAutoStatus] = useState<AutonomousStatus | null>(null)
  const [ksStatus, setKsStatus] = useState<KillSwitchInfo | null>(null)
  const [pnlHistory, setPnlHistory] = useState<PnlPoint[]>([])
  const [loading, setLoading] = useState(true)
  const histRef = useRef<PnlPoint[]>([])

  const refresh = useCallback(async () => {
    try {
      const [a, p, auto, ks] = await Promise.all([
        api.account(), api.positions(),
        api.autonomousStatus().catch(() => null),
        api.killSwitchStatus().catch(() => null),
      ])
      setAcct(a); setPositions(p)
      if (auto) setAutoStatus(auto as AutonomousStatus)
      if (ks) setKsStatus(ks as KillSwitchInfo)
      const pt: PnlPoint = {
        time: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
        pnl: a.daily_pnl,
      }
      histRef.current = [...histRef.current.slice(-99), pt]
      setPnlHistory([...histRef.current])
    } catch { /* offline */ }
    setLoading(false)
  }, [])

  useEffect(() => { refresh(); const id = setInterval(refresh, 10000); return () => clearInterval(id) }, [refresh])

  if (loading) return <div className="flex items-center justify-center h-full text-text-muted">Loading...</div>

  const pnl = acct?.daily_pnl ?? 0
  const equity = acct?.equity ?? 0
  const bp = acct?.buying_power ?? 0

  const kpis = [
    { label: 'Equity', value: `$${equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}`, icon: DollarSign, color: 'text-accent-blue', bg: 'bg-accent-blue/10' },
    { label: 'Day P&L', value: `${pnl >= 0 ? '+' : ''}$${pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}`, icon: pnl >= 0 ? TrendingUp : TrendingDown, color: pnl >= 0 ? 'text-accent-green' : 'text-accent-red', bg: pnl >= 0 ? 'bg-accent-green/10' : 'bg-accent-red/10' },
    { label: 'Buying Power', value: `$${bp.toLocaleString('en-US', { minimumFractionDigits: 2 })}`, icon: BarChart3, color: 'text-accent-purple', bg: 'bg-accent-purple/10' },
    { label: 'Open Positions', value: String(positions.length), icon: ShieldAlert, color: 'text-accent-amber', bg: 'bg-accent-amber/10' },
  ]

  return (
    <div className="space-y-[var(--space-5)]">
      {/* ── Row 1: KPI Cards ── */}
      <div className="grid grid-cols-4 gap-[var(--space-4)]">
        {kpis.map(k => <KPICard key={k.label} {...k} />)}
      </div>

      {/* ── Row 2: Autonomous Toggle + Kill Switch ── */}
      <div className="grid grid-cols-[1fr_auto] gap-[var(--space-4)]">
        <AutonomousToggle status={autoStatus} onRefresh={refresh} />
        <KillSwitchPanel status={ksStatus} onRefresh={refresh} />
      </div>

      {/* ── Row 3: P&L Chart + Positions ── */}
      <div className="grid grid-cols-2 gap-[var(--space-4)]">
        <Card>
          <CardHeader>
            <CardTitle subtitle="Real-time profit & loss tracking">Intraday P&L</CardTitle>
            <Button variant="ghost" size="sm" icon={<RefreshCw className="w-icon-md h-icon-md" />} onClick={refresh} />
          </CardHeader>
          <div className="h-52">
            {pnlHistory.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={pnlHistory}>
                  <defs>
                    <linearGradient id="pnlGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={pnl >= 0 ? '#00D4AA' : '#FF6B6B'} stopOpacity={0.3} />
                      <stop offset="100%" stopColor={pnl >= 0 ? '#00D4AA' : '#FF6B6B'} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" tick={{ fill: '#484F58', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#484F58', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={v => `$${v}`} />
                  <Tooltip contentStyle={{ background: '#141820', border: '1px solid #1E2433', borderRadius: 8, fontSize: 12 }}
                    labelStyle={{ color: '#8B949E' }} formatter={(v: number) => [`$${v.toFixed(2)}`, 'P&L']} />
                  <ReferenceLine y={0} stroke="#2A3040" strokeDasharray="3 3" />
                  <ReferenceLine y={-100} stroke="#FF6B6B" strokeDasharray="6 3" label={{ value: 'Hard Stop -$100', fill: '#FF6B6B', fontSize: 10, position: 'left' }} />
                  <Area type="monotone" dataKey="pnl" stroke={pnl >= 0 ? '#00D4AA' : '#FF6B6B'} strokeWidth={2} fill="url(#pnlGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-text-dim text-sm">Collecting data points...</div>
            )}
          </div>
        </Card>
        <PositionsPanel positions={positions} />
      </div>

      {/* ── Row 4: Strategy Manager + Trading Assistant ── */}
      <div className="grid grid-cols-2 gap-[var(--space-4)]">
        <StrategyManager autoStatus={autoStatus} onRefresh={refresh} />
        <QuickChat />
      </div>

      {/* ── Row 5: Signal Consensus + Technical Analysis ── */}
      <div className="grid grid-cols-2 gap-[var(--space-4)]">
        <SignalConsensus />
        <TechnicalPanel />
      </div>

      {/* ── Row 6: Earnings & Backtest ── */}
      <EarningsPanel />
    </div>
  )
}

