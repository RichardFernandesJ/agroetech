import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";

import { signUp } from "./support/players";

const db = (...args: string[]): void => {
  execFileSync("python", ["e2e/support/e2e_db.py", ...args]);
};

test("praça: uma jogadora anuncia e outro jogador compra, com taxa e histórico", async ({ browser }) => {
  // Vendedora: nível 10 e 20 milhos.
  const { page: seller } = await signUp(browser, "v", "Vendedora");
  db("boost", "2250", "100");
  db("give", "crop_milho", "20");

  await seller.locator('[data-menu="exchange"]').click();
  await expect(seller.getByRole("dialog", { name: "Praça dos Jogadores" })).toBeVisible();
  await seller.getByRole("tab", { name: "Anunciar" }).click();
  await seller.locator('[data-pick="crop_milho"]').click();
  await seller.locator('[data-setqty]').last().click(); // Tudo (20)
  await expect(seller.locator('[data-testid="sell-qty"]')).toHaveText("20");
  await seller.locator('[data-setprice]').nth(1).click(); // Referência (5 AGC)
  await expect(seller.locator(".sell-summary")).toContainText("Total 100 AGC · taxa 5 AGC · você recebe 95 AGC");
  await seller.locator('[data-action="create"]').click();
  await expect(seller.locator(".market-message")).toContainText("Anunciou 20× Milho a 5 AGC cada");
  await expect(seller.locator(".tab.active")).toContainText("Meus anúncios (1)");

  // Comprador: nível 10, procura o anúncio e compra 5 unidades.
  const { page: buyer } = await signUp(browser, "c", "Comprador");
  db("boost", "2250", "100");
  await buyer.locator('[data-menu="exchange"]').click();
  await expect(buyer.locator(".listing-row")).toHaveCount(1);
  await expect(buyer.locator(".listing-row")).toContainText("Milho");
  await expect(buyer.locator(".listing-row")).toContainText("por e2e_");
  await buyer.locator('[data-buy][data-qty="5"]').click();
  await expect(buyer.locator(".market-message")).toContainText("Comprou 5× Milho por 25 AGC");
  await buyer.locator(".btn-close").click();
  await expect(buyer.locator(".hud-balance")).toContainText("75 AGC");

  // Vendedora vê a venda no histórico: 25 AGC - taxa de 2 (1,25 arredondado para cima) = +23.
  await seller.reload();
  await expect(seller.locator(".hud-balance")).toContainText("123 AGC");
  await seller.locator('[data-menu="exchange"]').click();
  await seller.getByRole("tab", { name: "Histórico" }).click();
  await expect(seller.locator(".ledger-row").first()).toContainText("Venda · 5× Milho");
  await expect(seller.locator(".ledger-row").first()).toContainText("+23 AGC");
  await seller.getByRole("tab", { name: /Meus anúncios/ }).click();
  await expect(seller.locator(".listing-row").first()).toContainText("15/20");

  // Cancelar devolve o que sobrou.
  await seller.locator("[data-cancel]").first().click();
  await expect(seller.locator(".market-message")).toContainText("15× Milho devolvidos");
});
