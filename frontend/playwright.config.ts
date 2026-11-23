import { defineConfig } from "@playwright/test";

// API em SQLite descartável + Vite: roda sem Docker. Em CI/produção o fluxo
// equivalente usa o Compose com PostgreSQL.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  workers: 1,
  use: { baseURL: "http://localhost:5173", headless: true },
  webServer: [
    {
      command: "python -m uvicorn app.main:app --port 8000",
      cwd: "../backend",
      url: "http://localhost:8000/health",
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        AGRO_DATABASE_URL: "sqlite+aiosqlite:///./e2e.sqlite3",
        AGRO_AUTO_CREATE_TABLES: "true",
        AGRO_JWT_SECRET: "e2e-secret-not-for-production",
      },
    },
    {
      command: "npm run dev",
      url: "http://localhost:5173",
      reuseExistingServer: false,
      timeout: 60_000,
    },
  ],
});
