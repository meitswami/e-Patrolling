import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        patrol: {
          bg: '#080c16',
          surface: '#0f1521',
          card: '#141c2b',
          border: '#1e2d42',
          accent: '#00e676',
          'accent-dim': '#00c853',
          'accent-glow': 'rgba(0, 230, 118, 0.15)',
          info: '#60a5fa',
          success: '#34d399',
          danger: '#f43f5e',
          warning: '#f59e0b',
          text: '#e8edf5',
          muted: '#7b8ca8',
          'muted-dim': '#4a5568',
        },
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'system-ui', 'sans-serif'],
        mono: ['var(--font-jetbrains)', 'monospace'],
      },
      boxShadow: {
        'glow-sm': '0 0 8px rgba(0, 230, 118, 0.1)',
        'glow-md': '0 0 20px rgba(0, 230, 118, 0.15)',
        'card': '0 2px 8px rgba(0, 0, 0, 0.3)',
        'card-hover': '0 4px 16px rgba(0, 0, 0, 0.4)',
      },
      backgroundImage: {
        'gradient-subtle': 'linear-gradient(135deg, rgba(0, 230, 118, 0.05) 0%, rgba(96, 165, 250, 0.05) 100%)',
        'gradient-card': 'linear-gradient(180deg, rgba(20, 28, 43, 1) 0%, rgba(15, 21, 33, 1) 100%)',
      },
    },
  },
  plugins: [],
}
export default config
