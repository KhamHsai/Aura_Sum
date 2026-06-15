import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  test: {
    environment: 'jsdom',
    globals: true,
    // Exclude Playwright E2E specs — they are run by Playwright, not Vitest
    exclude: ['**/node_modules/**', '**/e2e/**'],
  },
})
