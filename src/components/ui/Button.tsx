import type { ButtonHTMLAttributes, ReactNode } from 'react'

/* ─── Button ───────────────────────────────────────────────────
   Pencil.dev design-token-driven button with variant system.
   Tokens: --color-accent-*, --color-bg-*, --color-border,
           --radius-lg, --radius-xl, --space-*, --text-xs, --text-sm
   ────────────────────────────────────────────────────────────── */

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  icon?: ReactNode
  loading?: boolean
  children?: ReactNode
}

const variantStyles = {
  primary:   'bg-accent-green/10 border border-accent-green/20 text-accent-green hover:bg-accent-green/20 hover:shadow-glow-green',
  secondary: 'bg-bg-card border border-border text-text-muted hover:text-text hover:bg-bg-hover',
  ghost:     'border border-transparent text-text-muted hover:text-text hover:bg-bg-hover',
  danger:    'bg-accent-red/10 border border-accent-red/20 text-accent-red hover:bg-accent-red/20 hover:shadow-glow-red',
}

const sizeStyles = {
  sm: 'px-[var(--space-3)] py-[var(--space-1-5)] text-xs rounded-lg gap-[var(--space-1-5)]',
  md: 'px-[var(--space-4)] py-[var(--space-2)] text-sm rounded-lg gap-[var(--space-2)]',
  lg: 'px-[var(--space-5)] py-[var(--space-3)] text-sm rounded-xl gap-[var(--space-2)]',
}

export default function Button({
  variant = 'primary', size = 'md', icon, loading, children, className = '', disabled, ...rest
}: ButtonProps) {
  return (
    <button
      className={`inline-flex items-center justify-center font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
      disabled={disabled || loading}
      {...rest}
    >
      {icon && <span className="shrink-0">{icon}</span>}
      {children}
    </button>
  )
}

