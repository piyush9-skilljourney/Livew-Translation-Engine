import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  // No special asset or optimization config needed!
  // The AI files are served directly from the /public folder.
  plugins: [
    react()
  ],
})
