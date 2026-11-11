/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// strictPort: the API only allows CORS from http://localhost:5173, so never fall back to another port.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // fs.allow: the Hindi and Marathi sentences live in ONE file, chatbot/strings.json, shared with the backend (one level up)
  server: { port: 5173, strictPort: true, fs: { allow: [".."] } },
  // Vendor libraries are split into their own files: each stays small and the browser keeps them cached between releases.
  // (The map library is already its own chunk because only the /app/map page imports it.)
  build: {
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: "react", test: /node_modules[\/](react|react-dom|scheduler)[\/]/, priority: 30 },
            { name: "router", test: /node_modules[\/](react-router|cookie|set-cookie-parser)[\/]/, priority: 20 },
            { name: "motion", test: /node_modules[\/](framer-motion|motion-dom|motion-utils)[\/]/, priority: 10 },
          ],
        },
      },
    },
  },
  // npm test: component and routing tests run in a fake browser (jsdom). They never touch the real API or the real map.
  test: { environment: "jsdom", setupFiles: ["./src/test/setup.ts"], include: ["src/**/*.test.{ts,tsx}"] },
});
