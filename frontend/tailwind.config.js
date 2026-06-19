/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      colors: {
        band: {
          bg: '#0a0a0a',
          surface: '#111111',
          border: '#1f1f1f',
          card: '#161616',
          purple: '#7c3aed',
          'purple-light': '#a855f7',
          'purple-dim': '#7c3aed33',
          green: '#22c55e',
          yellow: '#f59e0b',
          red: '#ef4444',
          blue: '#3b82f6',
          muted: '#6b7280',
          text: '#e5e7eb',
          'text-dim': '#9ca3af',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
