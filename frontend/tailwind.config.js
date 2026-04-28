/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#1890ff',
        'primary-dark': '#096dd9',
        success: '#52c41a',
        warning: '#faad14',
        error: '#f5222d',
        paper: {
          light: '#f5f5dc',
          dark: '#1f1f1f',
        }
      },
      fontFamily: {
        sans: ['PingFang SC', 'Microsoft YaHei', 'sans-serif'],
        mono: ['Fira Code', 'Consolas', 'monospace'],
      }
    },
  },
  plugins: [],
}