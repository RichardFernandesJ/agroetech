import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";

const db = (...args: string[]): void => {
  execFileSync("python", ["e2e/support/e2e_db.py", ...args]);
};

// Com a janela fixa o zoom é determinístico: o curral fica neste ponto da tela.
const VIEWPORT = { width: 1280, height: 800 };
const BARN = { x: 428, y: 254 };

test("animais: construir abrigo, comprar, alimentar, esperar offline e coletar", async ({ page }) => {
  await page.setViewportSize(VIEWPORT);
  const id = `${Date.now().toString(36)}a`;
  await page.goto("/");
  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.locator('input[name="email"]').fill(`e2e_${id}@example.com`);
  await page.locator('input[name="username"]').fill(`e2e_${id}`);
  await page.locator('input[name="password"]').fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta e entrar" }).click();
  await page.locator('input[name="name"]').fill("Eva");
  await page.getByRole("button", { name: "Começar a cultivar" }).click();
  await expect(page.locator(".hud-level-label")).toContainText("0/50 XP");
  await expect(page.locator(".hud-balance")).toContainText("100 AGC");
  db("boost", "2250", "2000"); // nível 10 e 2.000 AGC
  db("give", "crop_milho", "10");

  // Construir o galinheiro (abrigo das galinhas).
  await page.locator('[data-menu="buildings"]').click();
  await page.locator('[data-building="galinheiro"]').click();
  await expect(page.locator(".market-message")).toContainText("Galinheiro melhorada para o nível 1");
  await page.locator(".btn-close").click();

  // Clicar no curral do mapa abre o painel de animais.
  await page.mouse.move(BARN.x, BARN.y);
  await expect(page.locator(".hud-prompt")).toContainText("Curral da Ilha");
  await page.mouse.click(BARN.x, BARN.y);
  await expect(page.getByRole("dialog", { name: "Animais" })).toBeVisible();

  // Comprar uma galinha.
  await page.locator('[data-buy="galinha"]').click();
  await expect(page.locator(".market-message")).toContainText("Você comprou uma galinha");
  await expect(page.locator(".animal-card").first()).toContainText("Com fome");

  // Alimentar (4 porções = 2 horas) com ração do inventário.
  await page.locator('[data-feed][data-units="4"]').first().click();
  await expect(page.locator(".animal-card").first()).toContainText("Alimentada por");

  // Duas horas "offline": 2 h / 15 min = 8 ovos, calculados pelo servidor.
  db("rewind", "2");
  await expect(page.locator(".animal-stored").first()).toContainText("8/32", { timeout: 15_000 });

  await page.locator('[data-action="collect"]').click();
  await expect(page.locator(".market-message")).toContainText("Coletou 8×");
  await expect(page.locator(".animal-stored").first()).toContainText("0/32");
});
