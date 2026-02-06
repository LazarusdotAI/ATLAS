/** @type {import('tailwindcss').Config} */
/*
 * Pencil.dev Design Token Integration
 * All values reference CSS custom properties defined in src/index.css.
 * The .pen file is the single source of truth — sync tokens there first,
 * then update index.css, and Tailwind picks them up automatically.
 */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT:  'var(--color-bg)',
          card:     'var(--color-bg-card)',
          hover:    'var(--color-bg-hover)',
          elevated: 'var(--color-bg-elevated)',
          input:    'var(--color-bg-input)',
        },
        border: { DEFAULT: 'var(--color-border)', light: 'var(--color-border-light)' },
        text:   { DEFAULT: 'var(--color-text)', muted: 'var(--color-text-muted)', dim: 'var(--color-text-dim)' },
        accent: {
          green:  'var(--color-accent-green)',
          red:    'var(--color-accent-red)',
          amber:  'var(--color-accent-amber)',
          blue:   'var(--color-accent-blue)',
          purple: 'var(--color-accent-purple)',
        },
        focus: { ring: 'var(--color-focus-ring)' },
      },
      fontFamily: {
        sans: ['var(--font-sans)'],
        mono: ['var(--font-mono)'],
      },
      fontSize: {
        '2xs':  ['var(--text-2xs)',  { lineHeight: 'var(--leading-tight)' }],
        'xs':   ['var(--text-xs)',   { lineHeight: 'var(--leading-tight)' }],
        'sm':   ['var(--text-sm)',   { lineHeight: 'var(--leading-normal)' }],
        'base': ['var(--text-base)', { lineHeight: 'var(--leading-normal)' }],
        'lg':   ['var(--text-lg)',   { lineHeight: 'var(--leading-tight)' }],
        'xl':   ['var(--text-xl)',   { lineHeight: 'var(--leading-tight)' }],
        '2xl':  ['var(--text-2xl)',  { lineHeight: 'var(--leading-tight)' }],
      },
      borderRadius: {
        sm:   'var(--radius-sm)',
        md:   'var(--radius-md)',
        lg:   'var(--radius-lg)',
        xl:   'var(--radius-xl)',
        full: 'var(--radius-full)',
      },
      boxShadow: {
        sm:        'var(--shadow-sm)',
        md:        'var(--shadow-md)',
        lg:        'var(--shadow-lg)',
        elevated:  'var(--shadow-elevated)',
        'glow-green': 'var(--shadow-glow-green)',
        'glow-red':   'var(--shadow-glow-red)',
      },
      spacing: {
        'sidebar': 'var(--sidebar-width)',
        'header':  'var(--header-height)',
      },
      width: {
        'icon-sm':     'var(--icon-sm)',
        'icon-md':     'var(--icon-md)',
        'icon-lg':     'var(--icon-lg)',
        'icon-box-sm': 'var(--icon-box-sm)',
        'icon-box-md': 'var(--icon-box-md)',
        'icon-box-lg': 'var(--icon-box-lg)',
      },
      height: {
        'icon-sm':     'var(--icon-sm)',
        'icon-md':     'var(--icon-md)',
        'icon-lg':     'var(--icon-lg)',
        'icon-box-sm': 'var(--icon-box-sm)',
        'icon-box-md': 'var(--icon-box-md)',
        'icon-box-lg': 'var(--icon-box-lg)',
      },
    },
  },
  plugins: [],
}

