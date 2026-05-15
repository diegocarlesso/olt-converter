/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: {
          DEFAULT: '#0b0f1a',
          panel: '#101725',
          elevated: '#15192b',
          border: '#1e2638',
        },
        brand: {
          DEFAULT: '#3da9fc',
          light: '#90c2ff',
          dark: '#1e6fbf',
        },
        accent: {
          green: '#5cd6a0',
          red: '#ff6b6b',
          yellow: '#ffd166',
        },
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [],
};
