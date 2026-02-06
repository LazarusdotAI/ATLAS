import type { ReactNode } from 'react'

/* ─── Card ─────────────────────────────────────────────────────
   Pencil.dev design-token-driven container component.
   Variants: default | elevated | ghost
   Tokens: --color-bg-card, --color-bg-elevated, --color-border,
           --radius-xl, --shadow-lg, --shadow-elevated, --space-*
   ────────────────────────────────────────────────────────────── */

interface CardProps {
  children: ReactNode
  className?: string
  variant?: 'default' | 'elevated' | 'ghost'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
}

const variantStyles = {
  default:  'bg-bg-card border border-border shadow-sm',
  elevated: 'bg-bg-elevated border border-border-light shadow-elevated',
  ghost:    'bg-transparent border border-transparent',
}

const paddingStyles = {
  none: '',
  sm:   'p-[var(--space-3)]',
  md:   'p-[var(--space-4)]',
  lg:   'p-[var(--space-5)]',
}

export default function Card({ children, className = '', variant = 'default', padding = 'lg', hover = false }: CardProps) {
  return (
    <div className={`rounded-xl ${variantStyles[variant]} ${paddingStyles[padding]} ${hover ? 'hover:border-border-light hover:shadow-md transition-all' : ''} ${className}`}>
      {children}
    </div>
  )
}

/* ─── Card sub-components ─── */

export function CardHeader({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`flex items-center justify-between mb-[var(--space-4)] ${className}`}>{children}</div>
}

export function CardTitle({ children, subtitle }: { children: ReactNode; subtitle?: string }) {
  return (
    <div>
      <h2 className="text-sm font-semibold">{children}</h2>
      {subtitle && <p className="text-xs text-text-dim">{subtitle}</p>}
    </div>
  )
}

