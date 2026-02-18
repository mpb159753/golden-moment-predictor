import { defineConfig, presetUno, presetAttributify } from 'unocss'

export default defineConfig({
  presets: [
    presetUno(),
    presetAttributify(),
  ],
  theme: {
    colors: {
      primary: '#3B82F6',
      'primary-light': '#93C5FD',
      accent: '#F59E0B',
      'accent-warm': '#EF4444',
      'score-recommended': '#10B981',
      'score-possible': '#F59E0B',
      'score-not-recommended': '#9CA3AF',
    },
    borderRadius: {
      sm: '8px',
      md: '12px',
      lg: '20px',
      full: '9999px',
    },
  },
})
