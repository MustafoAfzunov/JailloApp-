import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// The Django API runs on :8000; the proxy keeps the browser on one origin (no CORS, media works too).
const api = process.env.VITE_API_TARGET || 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { proxy: { '/api': api, '/media': api } },
  preview: { proxy: { '/api': api, '/media': api } },
})
