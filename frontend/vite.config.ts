import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Only used when developing the frontend separately (`npm run dev`);
    // when served by the FastAPI backend, the API is same-origin.
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
  build: { outDir: 'dist' },
})
