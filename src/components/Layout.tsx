import { Outlet, NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, MessageSquare, ListOrdered, Search,
  Zap, Shield, Clock,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api, type Account, type Clock as ClockT } from '../api'
import { StatusDot, Badge } from './ui'

const NAV = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/chat',      icon: MessageSquare,   label: 'Chat' },
  { to: '/orders',    icon: ListOrdered,     label: 'Orders' },
  { to: '/screener',  icon: Search,          label: 'Screener' },
]

export default function Layout() {
  const location = useLocation()
  const [acct, setAcct] = useState<Account | null>(null)
  const [clock, setClock] = useState<ClockT | null>(null)
  const [killActive, setKillActive] = useState(false)

  const fetchData = useCallback(async () => {
    try {
      const [a, c, ks] = await Promise.all([api.account(), api.clock(), api.killSwitchStatus()])
      setAcct(a); setClock(c); setKillActive(!!(ks as any)?.active)
    } catch { /* backend offline */ }
  }, [])

  useEffect(() => { fetchData(); const id = setInterval(fetchData, 10000); return () => clearInterval(id) }, [fetchData])

  const pnl = acct?.daily_pnl ?? 0
  const pnlColor = pnl >= 0 ? 'text-accent-green' : 'text-accent-red'

  return (
    <div className="flex h-screen overflow-hidden">
      {/* ── Sidebar ── */}
      <aside className="w-sidebar bg-bg-card border-r border-border flex flex-col items-center py-[var(--space-4)] shrink-0">
        {/* Logo */}
        <div className="mb-[var(--space-6)] flex flex-col items-center">
          <div className="w-icon-box-lg h-icon-box-lg rounded-xl bg-accent-green/10 flex items-center justify-center">
            <Zap className="w-icon-lg h-icon-lg text-accent-green" />
          </div>
          <span className="text-2xs font-bold text-text-muted mt-[var(--space-1)] tracking-wider">SBF</span>
        </div>

        {/* Nav items */}
        <nav className="flex-1 flex flex-col gap-[var(--space-1)] w-full px-[var(--space-2)]">
          {NAV.map(({ to, icon: Icon, label }) => {
            const active = location.pathname === to
            return (
              <NavLink key={to} to={to} title={label}
                className={`flex flex-col items-center gap-[var(--space-0-5)] py-2.5 rounded-lg transition-all
                  ${active ? 'nav-glow bg-accent-green/5 text-accent-green' : 'text-text-dim hover:text-text-muted hover:bg-bg-hover'}`}>
                <Icon className="w-icon-lg h-icon-lg" />
                <span className="text-2xs font-medium">{label}</span>
              </NavLink>
            )
          })}
        </nav>

        {/* Kill switch indicator */}
        {killActive && (
          <div className="mb-[var(--space-2)] w-icon-box-lg h-icon-box-lg rounded-xl bg-accent-red/20 flex items-center justify-center animate-pulse" title="Kill switch ACTIVE">
            <Shield className="w-icon-lg h-icon-lg text-accent-red" />
          </div>
        )}

        {/* Market status dot */}
        <div className="mb-[var(--space-2)]" title={clock?.is_open ? 'Market Open' : 'Market Closed'}>
          <StatusDot active={clock?.is_open ?? false} activeLabel="OPEN" inactiveLabel="CLOSED" />
        </div>
      </aside>

      {/* ── Main content ── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header bar */}
        <header className="h-header border-b border-border bg-bg-card/50 backdrop-blur-sm flex items-center justify-between px-[var(--space-6)] shrink-0">
          <div className="flex items-center gap-[var(--space-6)]">
            <h1 className="text-lg font-bold tracking-tight">
              <span className="text-accent-green">Stock</span><span className="text-text">BotFree</span>
            </h1>
            <div className="flex items-center gap-[var(--space-1-5)] text-xs text-text-muted">
              <Clock className="w-icon-sm h-icon-sm" />
              <span>{new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', timeZone: 'America/Chicago' })} CT</span>
            </div>
          </div>

          {/* Account summary in header */}
          <div className="flex items-center gap-[var(--space-5)]">
            {acct && (<>
              <div className="text-right">
                <div className="text-2xs text-text-dim uppercase tracking-wider">Equity</div>
                <div className="text-sm font-bold font-mono">${acct.equity.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
              </div>
              <div className="w-px h-[var(--space-8)] bg-border" />
              <div className="text-right">
                <div className="text-2xs text-text-dim uppercase tracking-wider">Day P&L</div>
                <div className={`text-sm font-bold font-mono ${pnlColor}`}>
                  {pnl >= 0 ? '+' : ''}${pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="w-px h-[var(--space-8)] bg-border" />
              <div className="text-right">
                <div className="text-2xs text-text-dim uppercase tracking-wider">Buying Power</div>
                <div className="text-sm font-bold font-mono text-accent-blue">${acct.buying_power.toLocaleString('en-US', { minimumFractionDigits: 2 })}</div>
              </div>
            </>)}
            {pnl <= -80 && (
              <Badge color="red" pulse>⛔ NEAR HARD STOP</Badge>
            )}
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-y-auto p-[var(--space-6)]">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

