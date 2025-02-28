import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { nodePolyfills } from 'vite-plugin-node-polyfills'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // Add polyfills for Node.js modules used by Solana web3.js
    nodePolyfills({
      // Whether to polyfill specific globals
      globals: {
        Buffer: true,
        global: true,
        process: true,
      },
      // Whether to polyfill specific modules
      protocolImports: true,
    }),
  ],
  server: {
    port: 5181,
    strictPort: true,
    host: '0.0.0.0', // Bind to all interfaces
    proxy: {
      '/api': {
        target: 'http://172.28.118.135:8001',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  define: {
    'import.meta.env.VITE_BACKEND_URL': JSON.stringify(process.env.VITE_BACKEND_URL || '/api'),
    'import.meta.env.VITE_FRONTEND_URL': JSON.stringify(process.env.VITE_FRONTEND_URL || 'http://localhost:5181')
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ['@solana/web3.js', 'bn.js'],
  },
  // Configure build options
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Split large dependencies into separate chunks
          'solana-web3': ['@solana/web3.js'],
          'recharts': ['recharts'],
          'chakra': ['@chakra-ui/react', '@chakra-ui/icons'],
        }
      }
    }
  }
})
