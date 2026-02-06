import { useState } from 'react'
import { ShieldOff, ShieldAlert, AlertTriangle } from 'lucide-react'
import { api, type KillSwitchInfo } from '../../api'
import { Card, Badge, Button } from '../ui'

interface Props {
  status: KillSwitchInfo | null
  onRefresh: () => void
}

export default function KillSwitchPanel({ status, onRefresh }: Props) {
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const trigger = async () => {
    if (!confirming) { setConfirming(true); return }
    setLoading(true)
    setConfirming(false)
    try {
      await api.killSwitch('Manual trigger from dashboard UI')
      onRefresh()
    } catch { /* */ }
    setLoading(false)
  }

  const active = status?.active ?? false

  return (
    <Card className={active ? 'border-accent-red/40 bg-accent-red/5' : ''}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-[var(--space-3)]">
          <div className={`w-icon-box-md h-icon-box-md rounded-lg flex items-center justify-center ${
            active ? 'bg-accent-red/20' : 'bg-bg-elevated'
          }`}>
            {active
              ? <ShieldAlert className="w-icon-md h-icon-md text-accent-red" />
              : <ShieldOff className="w-icon-md h-icon-md text-text-dim" />}
          </div>
          <div>
            <div className="text-xs font-semibold">Kill Switch</div>
            <div className="text-2xs text-text-dim">
              {active ? `Triggered: ${status?.reason ?? 'Unknown'}` : 'Emergency stop all trading'}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-[var(--space-2)]">
          {active ? (
            <Badge color="red" pulse>🛑 ACTIVE</Badge>
          ) : (
            <>
              {confirming && (
                <span className="flex items-center gap-1 text-accent-amber text-2xs">
                  <AlertTriangle className="w-3 h-3" /> Confirm?
                </span>
              )}
              <Button
                variant="danger"
                size="sm"
                icon={<ShieldAlert className="w-3.5 h-3.5" />}
                onClick={trigger}
                loading={loading}
              >
                {confirming ? 'YES, KILL ALL' : 'Kill Switch'}
              </Button>
            </>
          )}
        </div>
      </div>
      {active && status?.activated_at && (
        <div className="mt-[var(--space-2)] text-2xs text-text-dim">
          Activated {new Date(status.activated_at).toLocaleString()} ·
          {status.orders_cancelled ?? 0} orders cancelled ·
          {status.positions_closed ?? 0} positions closed
        </div>
      )}
    </Card>
  )
}

