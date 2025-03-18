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
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      }
    }
  },
  define: {
    // Vite automatically loads variables from .env files with the VITE_ prefix
    // We don't need to explicitly define them here
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
