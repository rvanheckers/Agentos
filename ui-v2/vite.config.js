import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  base: '/ui-v2/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'index.html')
      },
      output: {
        manualChunks: {
          vendor: ['dompurify'],
          features: [
            './src/features/video-upload/components/upload-zone.js',
            './src/features/results/components/results-grid.js',
            './src/features/processing/components/processing-panel.js'
          ],
          shared: [
            './src/shared/services/websocket-service.js',
            './src/shared/services/notification-service.js'
          ]
        }
      }
    },
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  },
  server: {
    port: 3001,
    open: true
  }
});