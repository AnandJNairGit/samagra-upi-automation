import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const basePath = env.VITE_BASE_PATH || '/upi/';

  return {
    plugins: [react()],
    base: basePath,
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      host: '0.0.0.0',
      port: 5173,
      watch: {
        usePolling: true,
      },
      proxy: {
        // In local Docker dev, proxy /upi-api to the backend container at port 8000
        '/upi-api': {
          target: process.env.VITE_DEV_BACKEND_TARGET || 'http://backend:8000',
          changeOrigin: true,
          rewrite: (p) => p.replace(/^\/upi-api/, ''),
        },
      },
    },
    preview: {
      host: '0.0.0.0',
      port: 5173,
    },
  };
});
