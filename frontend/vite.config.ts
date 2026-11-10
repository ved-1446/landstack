import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// strictPort: the API only allows CORS from http://localhost:5173, so never fall back to another port.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // fs.allow: the Hindi and Marathi sentences live in ONE file, chatbot/strings.json, shared with the backend (one level up)
  server: { port: 5173, strictPort: true, fs: { allow: [".."] } },
});
