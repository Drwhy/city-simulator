import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const httpTarget = env.VITE_BACKEND_PROXY_TARGET || "http://localhost:8000";
  const wsTarget = httpTarget.replace(/^http/, "ws");

  return {
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
      proxy: {
        "/api": { target: httpTarget, changeOrigin: true },
        "/ws": { target: wsTarget, ws: true },
      },
    },
  };
});
