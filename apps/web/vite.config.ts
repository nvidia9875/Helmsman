import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.svg', 'apple-touch-icon.svg'],
      workbox: {
        // Phase 6: MediaPipe (face_landmarker.task ~3.6MB / WASM) は
        // precache から除外し、初回利用時の lazy fetch + HTTP キャッシュに任せる。
        // PWA バンドルが肥大化するのを避けつつ、main app は引き続きオフライン対応。
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        globIgnores: ['**/mediapipe/**'],
      },
      manifest: {
        name: 'Helmsman',
        short_name: 'Helmsman',
        description: 'Goal-driven AI meeting facilitator',
        theme_color: '#5b8def',
        background_color: '#08080a',
        display: 'standalone',
        icons: [
          {
            src: '/favicon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'any',
          },
          {
            src: '/maskable-icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
            purpose: 'maskable',
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: '127.0.0.1',
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api/, ''),
      },
    },
  },
});
