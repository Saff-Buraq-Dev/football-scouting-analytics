import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The API (FastAPI, port 8000) is proxied so the browser sees a single origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
});
