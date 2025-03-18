// vite.config.ts
import { defineConfig } from "file:///mnt/c/Users/Shane%20Holmes/CascadeProjects/windsurf-project/soleco/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///mnt/c/Users/Shane%20Holmes/CascadeProjects/windsurf-project/soleco/frontend/node_modules/@vitejs/plugin-react/dist/index.mjs";
import { nodePolyfills } from "file:///mnt/c/Users/Shane%20Holmes/CascadeProjects/windsurf-project/soleco/frontend/node_modules/vite-plugin-node-polyfills/dist/index.js";
var vite_config_default = defineConfig({
  plugins: [
    react(),
    // Add polyfills for Node.js modules used by Solana web3.js
    nodePolyfills({
      // Whether to polyfill specific globals
      globals: {
        Buffer: true,
        global: true,
        process: true
      },
      // Whether to polyfill specific modules
      protocolImports: true
    })
  ],
  server: {
    port: 5181,
    strictPort: true,
    host: "0.0.0.0",
    // Bind to all interfaces
    proxy: {
      "/api": {
        target: "http://172.28.118.135:8001",
        changeOrigin: true,
        secure: false
      }
    }
  },
  define: {
    "import.meta.env.VITE_BACKEND_URL": JSON.stringify(process.env.VITE_BACKEND_URL || "/api"),
    "import.meta.env.VITE_FRONTEND_URL": JSON.stringify(process.env.VITE_FRONTEND_URL || "http://localhost:5181")
  },
  // Optimize dependencies
  optimizeDeps: {
    include: ["@solana/web3.js", "bn.js"]
  },
  // Configure build options
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          // Split large dependencies into separate chunks
          "solana-web3": ["@solana/web3.js"],
          "recharts": ["recharts"],
          "chakra": ["@chakra-ui/react", "@chakra-ui/icons"]
        }
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcudHMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCIvbW50L2MvVXNlcnMvU2hhbmUgSG9sbWVzL0Nhc2NhZGVQcm9qZWN0cy93aW5kc3VyZi1wcm9qZWN0L3NvbGVjby9mcm9udGVuZFwiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9maWxlbmFtZSA9IFwiL21udC9jL1VzZXJzL1NoYW5lIEhvbG1lcy9DYXNjYWRlUHJvamVjdHMvd2luZHN1cmYtcHJvamVjdC9zb2xlY28vZnJvbnRlbmQvdml0ZS5jb25maWcudHNcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfaW1wb3J0X21ldGFfdXJsID0gXCJmaWxlOi8vL21udC9jL1VzZXJzL1NoYW5lJTIwSG9sbWVzL0Nhc2NhZGVQcm9qZWN0cy93aW5kc3VyZi1wcm9qZWN0L3NvbGVjby9mcm9udGVuZC92aXRlLmNvbmZpZy50c1wiO2ltcG9ydCB7IGRlZmluZUNvbmZpZyB9IGZyb20gJ3ZpdGUnXG5pbXBvcnQgcmVhY3QgZnJvbSAnQHZpdGVqcy9wbHVnaW4tcmVhY3QnXG5pbXBvcnQgeyBub2RlUG9seWZpbGxzIH0gZnJvbSAndml0ZS1wbHVnaW4tbm9kZS1wb2x5ZmlsbHMnXG5cbi8vIGh0dHBzOi8vdml0ZWpzLmRldi9jb25maWcvXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbXG4gICAgcmVhY3QoKSxcbiAgICAvLyBBZGQgcG9seWZpbGxzIGZvciBOb2RlLmpzIG1vZHVsZXMgdXNlZCBieSBTb2xhbmEgd2ViMy5qc1xuICAgIG5vZGVQb2x5ZmlsbHMoe1xuICAgICAgLy8gV2hldGhlciB0byBwb2x5ZmlsbCBzcGVjaWZpYyBnbG9iYWxzXG4gICAgICBnbG9iYWxzOiB7XG4gICAgICAgIEJ1ZmZlcjogdHJ1ZSxcbiAgICAgICAgZ2xvYmFsOiB0cnVlLFxuICAgICAgICBwcm9jZXNzOiB0cnVlLFxuICAgICAgfSxcbiAgICAgIC8vIFdoZXRoZXIgdG8gcG9seWZpbGwgc3BlY2lmaWMgbW9kdWxlc1xuICAgICAgcHJvdG9jb2xJbXBvcnRzOiB0cnVlLFxuICAgIH0pLFxuICBdLFxuICBzZXJ2ZXI6IHtcbiAgICBwb3J0OiA1MTgxLFxuICAgIHN0cmljdFBvcnQ6IHRydWUsXG4gICAgaG9zdDogJzAuMC4wLjAnLCAvLyBCaW5kIHRvIGFsbCBpbnRlcmZhY2VzXG4gICAgcHJveHk6IHtcbiAgICAgICcvYXBpJzoge1xuICAgICAgICB0YXJnZXQ6ICdodHRwOi8vMTcyLjI4LjExOC4xMzU6ODAwMScsXG4gICAgICAgIGNoYW5nZU9yaWdpbjogdHJ1ZSxcbiAgICAgICAgc2VjdXJlOiBmYWxzZSxcbiAgICAgIH1cbiAgICB9XG4gIH0sXG4gIGRlZmluZToge1xuICAgICdpbXBvcnQubWV0YS5lbnYuVklURV9CQUNLRU5EX1VSTCc6IEpTT04uc3RyaW5naWZ5KHByb2Nlc3MuZW52LlZJVEVfQkFDS0VORF9VUkwgfHwgJy9hcGknKSxcbiAgICAnaW1wb3J0Lm1ldGEuZW52LlZJVEVfRlJPTlRFTkRfVVJMJzogSlNPTi5zdHJpbmdpZnkocHJvY2Vzcy5lbnYuVklURV9GUk9OVEVORF9VUkwgfHwgJ2h0dHA6Ly9sb2NhbGhvc3Q6NTE4MScpXG4gIH0sXG4gIC8vIE9wdGltaXplIGRlcGVuZGVuY2llc1xuICBvcHRpbWl6ZURlcHM6IHtcbiAgICBpbmNsdWRlOiBbJ0Bzb2xhbmEvd2ViMy5qcycsICdibi5qcyddLFxuICB9LFxuICAvLyBDb25maWd1cmUgYnVpbGQgb3B0aW9uc1xuICBidWlsZDoge1xuICAgIHNvdXJjZW1hcDogdHJ1ZSxcbiAgICByb2xsdXBPcHRpb25zOiB7XG4gICAgICBvdXRwdXQ6IHtcbiAgICAgICAgbWFudWFsQ2h1bmtzOiB7XG4gICAgICAgICAgLy8gU3BsaXQgbGFyZ2UgZGVwZW5kZW5jaWVzIGludG8gc2VwYXJhdGUgY2h1bmtzXG4gICAgICAgICAgJ3NvbGFuYS13ZWIzJzogWydAc29sYW5hL3dlYjMuanMnXSxcbiAgICAgICAgICAncmVjaGFydHMnOiBbJ3JlY2hhcnRzJ10sXG4gICAgICAgICAgJ2NoYWtyYSc6IFsnQGNoYWtyYS11aS9yZWFjdCcsICdAY2hha3JhLXVpL2ljb25zJ10sXG4gICAgICAgIH1cbiAgICAgIH1cbiAgICB9XG4gIH1cbn0pXG4iXSwKICAibWFwcGluZ3MiOiAiO0FBQWtaLFNBQVMsb0JBQW9CO0FBQy9hLE9BQU8sV0FBVztBQUNsQixTQUFTLHFCQUFxQjtBQUc5QixJQUFPLHNCQUFRLGFBQWE7QUFBQSxFQUMxQixTQUFTO0FBQUEsSUFDUCxNQUFNO0FBQUE7QUFBQSxJQUVOLGNBQWM7QUFBQTtBQUFBLE1BRVosU0FBUztBQUFBLFFBQ1AsUUFBUTtBQUFBLFFBQ1IsUUFBUTtBQUFBLFFBQ1IsU0FBUztBQUFBLE1BQ1g7QUFBQTtBQUFBLE1BRUEsaUJBQWlCO0FBQUEsSUFDbkIsQ0FBQztBQUFBLEVBQ0g7QUFBQSxFQUNBLFFBQVE7QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLFlBQVk7QUFBQSxJQUNaLE1BQU07QUFBQTtBQUFBLElBQ04sT0FBTztBQUFBLE1BQ0wsUUFBUTtBQUFBLFFBQ04sUUFBUTtBQUFBLFFBQ1IsY0FBYztBQUFBLFFBQ2QsUUFBUTtBQUFBLE1BQ1Y7QUFBQSxJQUNGO0FBQUEsRUFDRjtBQUFBLEVBQ0EsUUFBUTtBQUFBLElBQ04sb0NBQW9DLEtBQUssVUFBVSxRQUFRLElBQUksb0JBQW9CLE1BQU07QUFBQSxJQUN6RixxQ0FBcUMsS0FBSyxVQUFVLFFBQVEsSUFBSSxxQkFBcUIsdUJBQXVCO0FBQUEsRUFDOUc7QUFBQTtBQUFBLEVBRUEsY0FBYztBQUFBLElBQ1osU0FBUyxDQUFDLG1CQUFtQixPQUFPO0FBQUEsRUFDdEM7QUFBQTtBQUFBLEVBRUEsT0FBTztBQUFBLElBQ0wsV0FBVztBQUFBLElBQ1gsZUFBZTtBQUFBLE1BQ2IsUUFBUTtBQUFBLFFBQ04sY0FBYztBQUFBO0FBQUEsVUFFWixlQUFlLENBQUMsaUJBQWlCO0FBQUEsVUFDakMsWUFBWSxDQUFDLFVBQVU7QUFBQSxVQUN2QixVQUFVLENBQUMsb0JBQW9CLGtCQUFrQjtBQUFBLFFBQ25EO0FBQUEsTUFDRjtBQUFBLElBQ0Y7QUFBQSxFQUNGO0FBQ0YsQ0FBQzsiLAogICJuYW1lcyI6IFtdCn0K
