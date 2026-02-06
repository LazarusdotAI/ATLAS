import { useState } from 'react'
import { Play, Square, Pause, Cpu, TrendingUp, GitBranch, BarChart3, Brain, Zap, Calendar } from 'lucide-react'
import { api, type AutonomousStatus } from '../../api'
import { Card, CardHeader, CardTitle, Badge, Button } from '../ui'

const STRATEGIES = [
  { id: 'technical', name: 'Technical Forecaster', icon: BarChart3, desc: 'RSI + MACD + ATR + Bollinger + VWAP' },
  { id: 'momentum', name: 'Momentum', icon: TrendingUp, desc: 'Price momentum with volume confirmation' },
  { id: 'breakout', name: 'Breakout', icon: Zap, desc: 'Range breakout with ATR filter' },
  { id: 'mean_reversion', name: 'Mean Reversion', icon: GitBranch, desc: 'Bollinger band reversion plays' },
  { id: 'sentiment', name: 'Sentiment (FinBERT)', icon: Brain, desc: 'NLP-driven news sentiment' },
  { id: 'smb_scalping', name: 'SMB Scalping', icon: Cpu, desc: 'Tape-reading scalp strategy' },
  { id: 'earnings_playbook', name: 'Earnings Playbook', icon: Calendar, desc: 'Pre/post-earnings volatility plays' },
] as const

interface Props {
  autoStatus: AutonomousStatus | null
  onRefresh: () => void
}

export default function StrategyManager({ autoStatus, onRefresh }: Props) {
  const [loading, setLoading] = useState<string | null>(null)

  const startStrategy = async (strategyId: string) => {
    setLoading(strategyId)
    try {
      await api.autonomousStart({ strategy: strategyId })
      onRefresh()
    } catch { /* handled by parent */ }
    setLoading(null)
  }

  const stopStrategy = async () => {
    setLoading('stop')
    try {
      await api.autonomousStop()
      onRefresh()
    } catch { /* handled */ }
    setLoading(null)
  }

  const activeStrategy = autoStatus?.strategy?.toLowerCase().replace(/\s+/g, '_')

  return (
    <Card>
      <CardHeader>
        <CardTitle subtitle="7 built-in SMB strategies">Strategy Manager</CardTitle>
        <Badge color={autoStatus?.running ? 'green' : 'dim'} pulse={autoStatus?.running}>
          {autoStatus?.running ? 'LIVE' : 'IDLE'}
        </Badge>
      </CardHeader>
      <div className="space-y-[var(--space-2)]">
        {STRATEGIES.map(s => {
          const isActive = autoStatus?.running && activeStrategy === s.id
          const Icon = s.icon
          return (
            <div
              key={s.id}
              className={`flex items-center gap-[var(--space-3)] p-[var(--space-3)] rounded-lg border transition-all ${
                isActive
                  ? 'border-accent-green/30 bg-accent-green/5'
                  : 'border-border/50 hover:border-border-light hover:bg-bg-hover'
              }`}
            >
              <div className={`w-icon-box-sm h-icon-box-sm rounded-md flex items-center justify-center shrink-0 ${
                isActive ? 'bg-accent-green/20' : 'bg-bg-elevated'
              }`}>
                <Icon className={`w-icon-sm h-icon-sm ${isActive ? 'text-accent-green' : 'text-text-dim'}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-semibold truncate">{s.name}</div>
                <div className="text-2xs text-text-dim truncate">{s.desc}</div>
              </div>
              <div className="flex items-center gap-[var(--space-1)] shrink-0">
                {isActive ? (
                  <>
                    <Badge color="green" pulse>Running</Badge>
                    <Button variant="danger" size="sm" icon={<Square className="w-3 h-3" />}
                      onClick={stopStrategy} loading={loading === 'stop'} />
                  </>
                ) : (
                  <Button variant="secondary" size="sm" icon={<Play className="w-3 h-3" />}
                    onClick={() => startStrategy(s.id)} loading={loading === s.id}
                    disabled={!!autoStatus?.running} />
                )}
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

