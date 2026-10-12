import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5173 is fixed because the API only allows that address (CORS).
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
