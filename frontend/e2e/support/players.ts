import { expect, type Browser, type Page } from "@playwright/test";

/** Jogador de teste: a página (sessão própria) e o nome de usuário criado. */
export interface Player {
  page: Page;
  username: string;
}

/** Cria uma conta nova em um contexto isolado (cada jogador tem a própria sessão). */
export async function signUp(browser: Browser, label: string, display: string): Promise<Player> {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } });
  const page = await context.newPage();
  const id = `${Date.now().toString(36)}${label}`;
  await page.goto("/");
  await page.getByRole("tab", { name: "Criar conta" }).click();
  await page.locator('input[name="email"]').fill(`e2e_${id}@example.com`);
  await page.locator('input[name="username"]').fill(`e2e_${id}`);
  await page.locator('input[name="password"]').fill("senha-forte-123");
  await page.getByRole("button", { name: "Criar conta e entrar" }).click();
  await page.locator('input[name="name"]').fill(display);
  await page.getByRole("button", { name: "Começar a cultivar" }).click();
  await expect(page.locator(".hud-level-label")).toContainText("0/50 XP");
  await expect(page.locator(".hud-balance")).toContainText("100 AGC");
  return { page, username: `e2e_${id}` };
}
