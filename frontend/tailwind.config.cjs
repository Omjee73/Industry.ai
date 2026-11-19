/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    fontFamily: {
      sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica Neue', 'Arial', 'sans-serif'],
      mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Consolas', 'monospace'],
    },
    colors: {
      bg: 'var(--color-bg)',
      panel: 'var(--color-panel)',
      'panel-elevated': 'var(--color-panel-elevated)',
      fg: 'var(--color-fg)',
      muted: 'var(--color-muted)',
      subtle: 'var(--color-subtle)',
      border: 'var(--color-border)',
      primary: 'var(--color-primary)',
      'primary-fg': 'var(--color-primary-fg)',
      ok: 'var(--color-ok)',
      'ok-soft': 'var(--color-ok-soft)',
      missing: 'var(--color-missing)',
      'missing-soft': 'var(--color-missing-soft)',
      review: 'var(--color-review)',
      'review-soft': 'var(--color-review-soft)',
      white: '#FFFFFF',
    },
  },
  plugins: [],
}
