import { expect, test } from "@playwright/test";

// Com a janela fixa, o zoom inicial é determinístico e o talhão 1 fica neste ponto.
const VIEWPORT = { width: 1280, height: 800 };
const PLOT_1 = { x: 578, y: 437 };

test("plantio por clique direto no talhão do mapa", async ({ page }) => {
  await page.setViewportSize(VIEWPORT);
  const id = `${Date.now().toString(36)}p`;
  await page.goto("/");
  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.locator('input[name="email"]').fill(`e2e_${id}@example.com`);
  await page.locator('input[name="username"]').fill(`e2e_${id}`);
  await page.locator('input[name="password"]').fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta e entrar" }).click();
  await page.locator('input[name="name"]').fill("Duda");
  await page.getByRole("button", { name: "Começar a cultivar" }).click();
  await expect(page.locator(".hud-level-label")).toContainText("0/50 XP");

  // Passar o mouse mostra a dica do talhão vazio.
  await page.mouse.move(PLOT_1.x, PLOT_1.y);
  await expect(page.locator(".hud-prompt")).toContainText("Talhão 1 (Vazio");

  // Clicar abre o seletor; plantar com 1 clique.
  await page.mouse.click(PLOT_1.x, PLOT_1.y);
  await expect(page.getByRole("dialog", { name: "Escolha o que plantar" })).toBeVisible();
  await page.getByRole("button", { name: "Plantar" }).first().click();

  await expect(page.locator(".hud-toast")).toContainText("Plantou Milho no Talhão 1");
  await expect(page.locator(".hud-level-label")).toContainText("2/50 XP");

  // O talhão agora mostra o crescimento.
  await page.mouse.move(PLOT_1.x + 200, PLOT_1.y + 200);
  await page.mouse.move(PLOT_1.x, PLOT_1.y);
  await expect(page.locator(".hud-prompt")).toContainText("Milho (Crescendo");
});
