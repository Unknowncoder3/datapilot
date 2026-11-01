import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    proxy: {
      "/api": {
        // The local DataPilot backend is run on port 8001 by the development workflow.
        target: process.env.VITE_API_TARGET || "http://127.0.0.1:8001",
        changeOrigin: true,
      },
    },
  },
});
