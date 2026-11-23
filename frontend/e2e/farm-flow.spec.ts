import { expect, test } from "@playwright/test";

test("cadastro, perfil, HUD da ilha e sessão persistente", async ({ page }) => {
  const id = Date.now().toString(36);
  await page.goto("/");

  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.locator('input[name="email"]').fill(`e2e_${id}@example.com`);
  await page.locator('input[name="username"]').fill(`e2e_${id}`);
  await page.locator('input[name="password"]').fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta e entrar" }).click();

  await page.locator('input[name="name"]').fill("Ana");
  await page.getByRole("button", { name: "Começar a cultivar" }).click();

  await expect(page.locator("canvas")).toBeVisible();
  await expect(page.locator(".hud-name")).toHaveText("Ana");
  await expect(page.locator(".hud-farm")).toContainText("talhões");
  await expect(page.locator(".hud-level-label")).toContainText("Nv 1");
  await expect(page.locator(".hud-btn-harvest")).toBeHidden(); // nada pronto ainda

  // Controles de câmera do HUD respondem sem erro.
  await page.locator(".hud-btn-zoom").first().click();
  await page.locator(".hud-btn-reset").click();

  // Economia (Fase 4): saldo inicial e compra de sementes só com cliques.
  await expect(page.locator(".hud-balance")).toContainText("100 AGC");
  await page.locator(".hud-balance").click();
  await page.getByRole("button", { name: "×1" }).first().click();
  await expect(page.locator(".market-balance")).toContainText("92");
  await expect(page.locator(".market-message")).toContainText("Comprou 1×");
  await page.getByRole("tab", { name: "Extrato" }).click();
  await expect(page.getByText("Compra de sementes")).toBeVisible();
  await page.getByRole("button", { name: "Fechar" }).click();
  await expect(page.locator(".hud-balance")).toContainText("92 AGC");

  // Sessão persiste após recarregar (JWT) e dispensa novo login.
  await page.reload();
  await expect(page.locator(".hud-name")).toHaveText("Ana");
});
