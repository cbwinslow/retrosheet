import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./app/**/*.{js,ts,jsx,tsx,mdx}', './components/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Georgia', 'Cambria', 'serif'],
        sans: ['Aptos', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['Cascadia Code', 'ui-monospace', 'SFMono-Regular', 'monospace'],
      },
      colors: {
        chalk: '#f6ead6',
        clay: '#b45f32',
        grass: '#0e4d38',
        pine: '#06140f',
      },
    },
  },
  plugins: [],
}

export default config
