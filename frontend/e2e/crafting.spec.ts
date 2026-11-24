import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";

const db = (...args: string[]): void => {
  execFileSync("python", ["e2e/support/e2e_db.py", ...args]);
};

// Com a janela fixa o zoom é determinístico: a oficina fica neste ponto da tela.
const VIEWPORT = { width: 1280, height: 800 };
const WORKSHOP = { x: 787, y: 232 };

test("fabricação: construir moinho, produzir, aguardar e coletar", async ({ page }) => {
  await page.setViewportSize(VIEWPORT);
  const id = `${Date.now().toString(36)}f`;
  await page.goto("/");
  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.locator('input[name="email"]').fill(`e2e_${id}@example.com`);
  await page.locator('input[name="username"]').fill(`e2e_${id}`);
  await page.locator('input[name="password"]').fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta e entrar" }).click();
  await page.locator('input[name="name"]').fill("Fábio");
  await page.getByRole("button", { name: "Começar a cultivar" }).click();
  await expect(page.locator(".hud-level-label")).toContainText("0/50 XP");
  await expect(page.locator(".hud-balance")).toContainText("100 AGC");
  db("boost", "2250", "3000"); // nível 10 e 3.000 AGC
  db("give", "crop_milho", "6");

  // Construir o moinho.
  await page.locator('[data-menu="buildings"]').click();
  await page.locator('[data-building="moinho"]').click();
  await expect(page.locator(".market-message")).toContainText("Moinho melhorada para o nível 1");
  await page.locator(".btn-close").click();

  // Clicar na oficina do mapa abre a fabricação.
  await page.mouse.move(WORKSHOP.x, WORKSHOP.y);
  await expect(page.locator(".hud-prompt")).toContainText("Oficina da Ilha");
  await page.mouse.click(WORKSHOP.x, WORKSHOP.y);
  await expect(page.getByRole("dialog", { name: "Fabricação" })).toBeVisible();
  await expect(page.locator(".station-card").first()).toContainText("vagas 0/1");

  // Produzir 2 lotes de farinha (6 milhos).
  await page.locator('[data-start="farinha"][data-batches="2"]').click();
  await expect(page.locator(".market-message")).toContainText("Produção iniciada: 2× Farinha de milho");
  await expect(page.locator(".job-row")).toContainText("2× Farinha de milho");
  await expect(page.locator(".station-card").first()).toContainText("vagas 1/1");
  await expect(page.locator('[data-action="collect"]')).toBeDisabled();

  // Passa o tempo: o painel recarrega sozinho e libera a coleta.
  db("finish");
  await expect(page.locator('[data-action="collect"]')).toBeEnabled({ timeout: 20_000 });
  await page.locator('[data-action="collect"]').click();
  await expect(page.locator(".market-message")).toContainText("Coletou 2× Farinha de milho");
  await expect(page.locator(".station-card").first()).toContainText("vagas 0/1");
});
