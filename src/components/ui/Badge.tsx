import type { ReactNode } from 'react'

/* ─── Badge ────────────────────────────────────────────────────
   Pencil.dev design-token-driven status badge / pill.
   Tokens: --color-accent-*, --color-bg-hover, --color-border,
           --radius-full, --space-*, --text-xs
   ────────────────────────────────────────────────────────────── */

interface BadgeProps {
  children: ReactNode
  color?: 'green' | 'red' | 'amber' | 'blue' | 'purple' | 'dim'
  className?: string
  pulse?: boolean
}

const colorStyles = {
  green:  'bg-accent-green/10 text-accent-green border-accent-green/20',
  red:    'bg-accent-red/10 text-accent-red border-accent-red/20',
  amber:  'bg-accent-amber/10 text-accent-amber border-accent-amber/20',
  blue:   'bg-accent-blue/10 text-accent-blue border-accent-blue/20',
  purple: 'bg-accent-purple/10 text-accent-purple border-accent-purple/20',
  dim:    'bg-bg-hover text-text-dim border-border',
}

export default function Badge({ children, color = 'dim', className = '', pulse = false }: BadgeProps) {
  return (
    <span className={`inline-flex items-center gap-[var(--space-1)] px-[var(--space-2)] py-[var(--space-0-5)] rounded-full border text-xs font-semibold ${colorStyles[color]} ${pulse ? 'animate-pulse' : ''} ${className}`}>
      {children}
    </span>
  )
}

