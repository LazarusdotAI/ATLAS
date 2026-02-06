import { useState } from 'react'
import { Search, Loader2, TrendingUp, TrendingDown, Minus } from 'lucide-react'
import { api } from '../api'
import { Card, Badge, Button, FilterBar } from '../components/ui'

const PRESETS = [
  { id: 'scalp_long', label: 'Scalp Long' },
  { id: 'scalp_short', label: 'Scalp Short' },
  { id: 'momentum', label: 'Momentum' },
  { id: 'mean_reversion', label: 'Mean Reversion' },
]

export default function Screener() {
  const [preset, setPreset] = useState('scalp_long')
  const [results, setResults] = useState<Record<string, unknown>[] | null>(null)
  const [tickers, setTickers] = useState<string[]>([])
  const [scanning, setScanning] = useState(false)

  const scan = async () => {
    setScanning(true)
    try {
      const res = await api.screen(preset, 30)
      setTickers(res.tickers)
      setResults(res.signals)
    } catch { setResults([]); setTickers([]) }
    setScanning(false)
  }

  const dirIcon = (dir: string) => {
    if (dir === 'LONG') return <TrendingUp className="w-3.5 h-3.5 text-accent-green" />
    if (dir === 'SHORT') return <TrendingDown className="w-3.5 h-3.5 text-accent-red" />
    return <Minus className="w-3.5 h-3.5 text-text-dim" />
  }

  const dirColor = (dir: string): 'green' | 'red' | 'dim' =>
    dir === 'LONG' ? 'green' : dir === 'SHORT' ? 'red' : 'dim'

  return (
    <div className="space-y-[var(--space-4)]">
      <div>
        <h2 className="text-lg font-bold">Market Screener</h2>
        <p className="text-xs text-text-dim">Scan for trading opportunities using preset strategies</p>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-[var(--space-3)]">
        <FilterBar options={PRESETS} value={preset} onChange={setPreset} />
        <Button
          icon={scanning ? <Loader2 className="w-icon-md h-icon-md animate-spin" /> : <Search className="w-icon-md h-icon-md" />}
          onClick={scan}
          disabled={scanning}
        >
          {scanning ? 'Scanning...' : 'Run Scan'}
        </Button>
      </div>

      {/* Results */}
      {results !== null && (
        <Card>
          <div className="text-xs text-text-dim mb-[var(--space-3)]">{tickers.length} tickers found · {results.length} signals generated</div>
          {results.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-[var(--space-3)]">
              {results.map((s, i) => {
                const sym = String(s.symbol ?? s.ticker ?? `#${i}`)
                const dir = String(s.direction ?? s.side ?? 'NEUTRAL')
                const conf = Number(s.confidence ?? s.score ?? 0)
                const entry = s.entry_price ?? s.entry
                const stop = s.stop_loss ?? s.stop
                const target = s.take_profit ?? s.target
                return (
                  <Card key={i} variant="ghost" padding="sm" hover className="border border-border">
                    <div className="flex items-center justify-between mb-[var(--space-2)]">
                      <span className="font-bold text-sm">{sym}</span>
                      <div className="flex items-center gap-[var(--space-1-5)]">
                        {dirIcon(dir)}
                        <Badge color={dirColor(dir)}>{dir}</Badge>
                      </div>
                    </div>
                    {/* Confidence bar */}
                    <div className="mb-[var(--space-2)]">
                      <div className="flex justify-between text-2xs text-text-dim mb-[var(--space-0-5)]">
                        <span>Confidence</span><span>{(conf * 100).toFixed(0)}%</span>
                      </div>
                      <div className="h-1.5 bg-bg rounded-full overflow-hidden">
                        <div className="h-full rounded-full bg-accent-green transition-all" style={{ width: `${conf * 100}%` }} />
                      </div>
                    </div>
                    <div className="flex gap-[var(--space-3)] text-2xs text-text-dim">
                      {entry != null && <span>Entry: <span className="text-text font-mono">${Number(entry).toFixed(2)}</span></span>}
                      {stop != null && <span>Stop: <span className="text-accent-red font-mono">${Number(stop).toFixed(2)}</span></span>}
                      {target != null && <span>Target: <span className="text-accent-green font-mono">${Number(target).toFixed(2)}</span></span>}
                    </div>
                  </Card>
                )
              })}
            </div>
          ) : (
            <div className="text-center py-[var(--space-8)] text-text-dim text-sm">No signals found for this preset</div>
          )}
        </Card>
      )}
    </div>
  )
}

