import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";

/** Nível 10 (2.250 XP) e 1.000 AGC direto no banco SQLite do E2E. */
function boostPlayer(): void {
  execFileSync("python", [
    "-c",
    "import sqlite3;c=sqlite3.connect('../backend/e2e.sqlite3');" +
      "c.execute('update player_progress set xp=2250');" +
      "c.execute('update wallets set balance=1000');c.commit()",
  ]);
}

test("construções: melhorar o poço e a casa por cliques", async ({ page }) => {
  const id = `${Date.now().toString(36)}b`;
  await page.goto("/");
  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.locator('input[name="email"]').fill(`e2e_${id}@example.com`);
  await page.locator('input[name="username"]').fill(`e2e_${id}`);
  await page.locator('input[name="password"]').fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta e entrar" }).click();
  await page.locator('input[name="name"]').fill("Caio");
  await page.getByRole("button", { name: "Começar a cultivar" }).click();

  // Progresso e carteira só existem depois que o HUD os carrega.
  await expect(page.locator(".hud-level-label")).toContainText("0/50 XP");
  await expect(page.locator(".hud-balance")).toContainText("100 AGC");
  await expect(page.locator(".hud-farm")).toContainText("6 talhões");
  boostPlayer();

  await page.locator('[data-menu="buildings"]').click();
  await expect(page.locator(".building-card")).toHaveCount(2);
  await expect(page.locator(".building-card").nth(1)).toContainText("Nível 0 de 3");

  // Poço nível 1.
  await page.locator('[data-building="poco"]').click();
  await expect(page.locator(".market-message")).toContainText("Poço da Ilha melhorada para o nível 1");
  await expect(page.locator(".buildings-panel .market-balance")).toContainText("940");

  // Casa nível 2: libera 2 talhões e o HUD mostra 8.
  await page.locator('[data-building="sede"]').click();
  await expect(page.locator(".market-message")).toContainText("nível 2");
  await expect(page.locator(".buildings-panel .market-balance")).toContainText("790");
  await page.locator(".btn-close").click();
  await expect(page.locator(".hud-farm")).toContainText("8 talhões");
  await expect(page.locator(".hud-balance")).toContainText("790 AGC");
});
