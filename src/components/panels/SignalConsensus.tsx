import { useState } from 'react'
import { Brain, Loader2, Search } from 'lucide-react'
import { api } from '../../api'
import { Card, CardHeader, CardTitle, Button, Badge } from '../ui'

export default function SignalConsensus() {
  const [symbol, setSymbol] = useState('')
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const run = async () => {
    if (!symbol.trim()) return
    setLoading(true)
    try {
      const res = await api.consensus(symbol.trim().toUpperCase())
      setResult(res.reply)
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    }
    setLoading(false)
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle subtitle="Sentiment + Technical + RL + TradingAgents">Signal Consensus</CardTitle>
        <Badge color="purple">
          <Brain className="w-3 h-3" /> Multi-Model
        </Badge>
      </CardHeader>
      <div className="flex gap-[var(--space-2)] mb-[var(--space-3)]">
        <input
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && run()}
          placeholder="Enter symbol (e.g. AAPL)"
          className="flex-1 bg-bg-input border border-border rounded-lg px-[var(--space-3)] py-[var(--space-2)] text-xs placeholder:text-text-dim focus:border-accent-green/50"
        />
        <Button size="sm" onClick={run} disabled={loading || !symbol.trim()}
          icon={loading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Search className="w-3.5 h-3.5" />}>
          Analyze
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

