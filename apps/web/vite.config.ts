import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Vite 5+ rejects unknown Host headers by default ("host is not allowed"). The
    // deployed dev server is reached over Tailscale MagicDNS (e.g.
    // teevee.tail612d5.ts.net), so allow any tailnet host (*.ts.net) + localhost.
    // Without this the UI fails to load in the browser though the server is running.
    allowedHosts: ['.ts.net', 'localhost']
  }
});
