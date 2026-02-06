import { useState } from 'react'
import { Calendar, Loader2, Search, FlaskConical } from 'lucide-react'
import { api } from '../../api'
import { Card, CardHeader, CardTitle, Button, Badge, FilterBar } from '../ui'

const MODES = [
  { id: 'playbook', label: 'Playbook' },
  { id: 'backtest', label: 'Backtest' },
]

export default function EarningsPanel() {
  const [symbol, setSymbol] = useState('')
  const [mode, setMode] = useState('playbook')
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    if (!symbol.trim()) return
    setLoading(true)
    const sym = symbol.trim().toUpperCase()
    try {
      const res = mode === 'playbook'
        ? await api.earningsPlaybook(sym)
        : await api.backtest(sym, 'earnings_playbook')
      setResult(res.reply)
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
    setLoading(false)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle subtitle="Historical earnings analysis & backtesting">Earnings & Backtest</CardTitle>
        <Badge color="amber">
          <Calendar className="w-3 h-3" /> Earnings
        </Badge>
      </CardHeader>
      <div className="flex items-center gap-[var(--space-2)] mb-[var(--space-3)]">
        <FilterBar options={MODES} value={mode} onChange={setMode} />
      </div>
      <div className="flex gap-[var(--space-2)] mb-[var(--space-3)]">
        <input
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && run()}
          placeholder="Enter symbol (e.g. TSLA)"
          className="flex-1 bg-bg-input border border-border rounded-lg px-[var(--space-3)] py-[var(--space-2)] text-xs placeholder:text-text-dim focus:border-accent-green/50"
        />
        <Button size="sm" onClick={run} disabled={loading || !symbol.trim()}
          icon={loading
            ? <Loader2 className="w-3.5 h-3.5 animate-spin" />
            : mode === 'playbook' ? <Search className="w-3.5 h-3.5" /> : <FlaskConical className="w-3.5 h-3.5" />}>
          {mode === 'playbook' ? 'Playbook' : 'Backtest'}
        </Button>
      </div>
      {result && (
        <div className="bg-bg-elevated rounded-lg p-[var(--space-3)] text-xs text-text leading-relaxed whitespace-pre-wrap max-h-[300px] overflow-y-auto">
          {result}
        </div>
      )}
    </Card>
  )
}

