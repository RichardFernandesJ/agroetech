import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";

/** Eleva o jogador direto no banco SQLite do E2E (nível 10 = 2.250 XP, 9 pontos). */
function grantLevelTen(): void {
  execFileSync(
    "python",
    [
      "-c",
      "import sqlite3;c=sqlite3.connect('../backend/e2e.sqlite3');c.execute('update player_progress set xp=2250');c.commit()",
    ],
    { cwd: process.cwd() },
  );
}

test("árvore de talentos: mapa, aquisição e presets", async ({ page }) => {
  const id = `${Date.now().toString(36)}t`;
  await page.goto("/");
  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.locator('input[name="email"]').fill(`e2e_${id}@example.com`);
  await page.locator('input[name="username"]').fill(`e2e_${id}`);
  await page.locator('input[name="password"]').fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta e entrar" }).click();
  await page.locator('input[name="name"]').fill("Bia");
  await page.getByRole("button", { name: "Começar a cultivar" }).click();
  // O registro de progresso só existe depois que o HUD carrega o XP.
  await expect(page.locator(".hud-level-label")).toContainText("0/50 XP");

  grantLevelTen();

  // Abre o mapa pelo menu do HUD (só cliques).
  await page.locator('[data-menu="talents"]').click();
  await expect(page.locator(".talent-modal")).toBeVisible();
  await expect(page.locator(".talent-node")).toHaveCount(27);
  await expect(page.locator(".talent-points-value")).toHaveText("9");

  // Detalhes ao clicar no talento.
  const node = page.locator('[data-id="agro_solo_fertil"]');
  await node.click();
  await expect(page.locator(".talent-sidebar h3")).toHaveText("Solo Fértil");
  await expect(page.locator(".talent-effects")).toContainText("Produção das colheitas +2%");

  // Talento de camada alta continua bloqueado e explica o motivo.
  await page.locator('[data-id="agro_mestre_terra"]').click();
  await expect(page.locator(".talent-buy")).toBeDisabled();
  await expect(page.locator(".talent-missing")).toBeVisible();

  // Adquire e confere pontos, status e barra do ramo.
  await node.click();
  await page.locator(".talent-buy").click();
  await expect(page.locator(".talent-points-value")).toHaveText("8");
  await expect(node).toHaveClass(/status-owned/);
  await expect(page.locator(".preset-chip.active")).toContainText("1 pt");

  // Zoom e ajuste do mapa respondem.
  await page.locator('[data-zoom="in"]').click();
  await page.locator('[data-zoom="fit"]').click();

  // Cria um segundo preset (nível 10 libera 2 espaços).
  page.once("dialog", (dialog) => void dialog.accept("Comerciante"));
  await page.getByRole("button", { name: "＋ Nova build" }).click();
  await expect(page.locator(".preset-chip")).toHaveCount(2);
  await expect(page.locator(".preset-chip").nth(1)).toContainText("Comerciante");

  // Escape fecha o painel.
  await page.keyboard.press("Escape");
  await expect(page.locator(".talent-modal")).toHaveCount(0);
});
