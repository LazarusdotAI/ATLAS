/* ─── StatusDot ────────────────────────────────────────────────
   Pencil.dev design-token-driven status indicator with label.
   Tokens: --color-accent-green, --color-accent-red,
           --color-text-dim, --text-2xs, --space-0-5
   ────────────────────────────────────────────────────────────── */

interface StatusDotProps {
  active: boolean
  activeLabel?: string
  inactiveLabel?: string
  size?: 'sm' | 'md'
}

export default function StatusDot({ active, activeLabel = 'OPEN', inactiveLabel = 'CLOSED', size = 'sm' }: StatusDotProps) {
  const dotSize = size === 'sm' ? 'w-2.5 h-2.5' : 'w-3 h-3'
  return (
    <div className="flex flex-col items-center">
      <div className={`${dotSize} rounded-full ${active ? 'bg-accent-green animate-pulse' : 'bg-accent-red'}`} />
      <span className="text-2xs text-text-dim mt-[var(--space-0-5)]">{active ? activeLabel : inactiveLabel}</span>
    </div>
  )
}

