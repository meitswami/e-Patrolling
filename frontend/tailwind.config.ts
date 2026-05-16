import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        patrol: {
          bg: '#0a0e1a',
          surface: '#111827',
          card: '#161d2e',
          border: '#1f2d44',
          accent: '#00ff88',
          danger: '#ff3b30',
          warning: '#ff9f0a',
          text: '#e2e8f0',
          muted: '#94a3b8',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'monospace'],
      },
    },
  },
  plugins: [],
}
export default config
