import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /v1 se reenvía a la API local; en Docker lo hace Nginx.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: { "/v1": "http://localhost:8000" },
  },
});
