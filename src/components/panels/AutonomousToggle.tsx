import { useState } from 'react'
import { Power, AlertTriangle } from 'lucide-react'
import { api, type AutonomousStatus } from '../../api'
import { Card, Badge, Button } from '../ui'

interface Props {
  status: AutonomousStatus | null
  onRefresh: () => void
}

export default function AutonomousToggle({ status, onRefresh }: Props) {
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const toggle = async () => {
    if (status?.running) {
      setLoading(true)
      try { await api.autonomousStop() } catch { /* */ }
      setLoading(false)
      onRefresh()
      return
    }
    if (!confirming) { setConfirming(true); return }
    setLoading(true)
    setConfirming(false)
    try { await api.autonomousStart() } catch { /* */ }
    setLoading(false)
    onRefresh()
  }

  const running = status?.running ?? false

  return (
    <Card className={`relative overflow-hidden ${running ? 'border-accent-green/30' : ''}`}>
      {running && (
        <div className="absolute inset-0 bg-accent-green/[0.03] pointer-events-none" />
      )}
      <div className="relative flex items-center justify-between">
        <div className="flex items-center gap-[var(--space-3)]">
          <div className={`w-icon-box-lg h-icon-box-lg rounded-xl flex items-center justify-center ${
            running ? 'bg-accent-green/20' : 'bg-bg-elevated'
          }`}>
            <Power className={`w-icon-lg h-icon-lg ${running ? 'text-accent-green' : 'text-text-dim'}`} />
          </div>
          <div>
            <div className="text-sm font-bold">Autonomous Trading</div>
            <div className="text-2xs text-text-dim">
              {running
                ? `${status?.strategy ?? 'Default'} · ${status?.symbols?.length ?? 0} symbols`
                : 'Multi-agent AI execution engine'}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-[var(--space-3)]">
          {running && (
            <div className="text-right mr-[var(--space-2)]">
              <div className="text-2xs text-text-dim">Trades Today</div>
              <div className="text-sm font-bold font-mono text-accent-green">{status?.trades_today ?? 0}</div>
            </div>
          )}

          {confirming && !running && (
            <div className="flex items-center gap-[var(--space-2)] text-accent-amber text-xs">
              <AlertTriangle className="w-3.5 h-3.5" />
              <span>Confirm?</span>
            </div>
          )}

          <button
            onClick={toggle}
            disabled={loading}
            className={`relative w-14 h-7 rounded-full transition-all duration-300 ${
              running
                ? 'bg-accent-green/20 border border-accent-green/40'
                : confirming
                  ? 'bg-accent-amber/20 border border-accent-amber/40'
                  : 'bg-bg-elevated border border-border'
            } ${loading ? 'opacity-50' : 'cursor-pointer'}`}
          >
            <div className={`absolute top-0.5 w-6 h-6 rounded-full transition-all duration-300 shadow-md ${
              running
                ? 'left-[calc(100%-26px)] bg-accent-green'
                : confirming
                  ? 'left-[calc(100%-26px)] bg-accent-amber'
                  : 'left-0.5 bg-text-dim'
            }`} />
          </button>
        </div>
      </div>

      {running && (
        <div className="relative flex items-center gap-[var(--space-4)] mt-[var(--space-3)] pt-[var(--space-3)] border-t border-border/50">
          <Badge color="green" pulse>● LIVE</Badge>
          {status?.errors ? <Badge color="red">{status.errors} errors</Badge> : null}
          <div className="flex-1" />
          <Button variant="danger" size="sm" onClick={toggle} loading={loading}>
            Stop Engine
          </Button>
        </div>
      )}
    </Card>
  )
}

