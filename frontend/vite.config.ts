import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";

// Em Docker, o alvo do proxy é http://api:8000 (nome do serviço).
const apiProxyTarget = process.env.API_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    host: "0.0.0.0",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
      "/health": {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
  build: {
    target: "es2022",
    sourcemap: true,
    // O bundle do Phaser é grande por natureza; não é código da aplicação.
    chunkSizeWarningLimit: 1500,
  },
});
