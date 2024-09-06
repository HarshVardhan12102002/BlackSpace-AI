import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { loadEnv } from 'vite'


export default defineConfig({
  base: "/",
  plugins: [react()],
  server: {
    port: 3000,
  },
});
