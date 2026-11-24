import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";

import { signUp } from "./support/players";

const db = (...args: string[]): void => {
  execFileSync("python", ["e2e/support/e2e_db.py", ...args]);
};

test("trocas: uma jogadora propõe, a outra aceita e os dois lados se trocam", async ({ browser }) => {
  // Cada conta fica nível 10 logo depois de criada (o utilitário age no jogador mais recente).
  const { page: ana } = await signUp(browser, "a", "Ana");
  db("boost", "2250", "100");
  db("give", "crop_milho", "20");
  const { page: bia, username: biaName } = await signUp(browser, "b", "Bia");
  db("boost", "2250", "100");
  db("give", "animal_leite", "5");

  // Ana monta a proposta: 2 milhos (valor 10) por 1 leite (valor 9).
  await ana.locator('[data-menu="trades"]').click();
  await expect(ana.getByRole("dialog", { name: "Trocas" })).toBeVisible();
  await ana.getByRole("tab", { name: "Nova troca" }).click();
  await ana.locator('[data-testid="player-search"]').fill(biaName);
  await ana.locator('[data-testid="player-search"]').press("Enter");
  await ana.locator(`[data-player="${biaName}"]`).click();
  await ana.locator('[data-add="offer:crop_milho"]').click();
  await ana.locator('[data-add="offer:crop_milho"]').click();
  await ana.locator('[data-add="request:animal_leite"]').click();
  await expect(ana.locator(".sell-summary")).toContainText("oferece 10");
  await expect(ana.locator(".sell-summary")).toContainText("pede 9");
  await ana.locator('[data-action="send"]').click();
  await expect(ana.locator(".market-message")).toContainText("Proposta enviada");
  await expect(ana.locator(".trade-card")).toContainText("Pendente");

  // Bia vê a proposta recebida e aceita.
  await bia.locator('[data-menu="trades"]').click();
  await expect(bia.locator(".trade-card")).toHaveCount(1);
  await expect(bia.locator(".trade-card")).toContainText("2× Milho");
  await bia.locator("[data-accept]").click();
  await expect(bia.locator(".market-message")).toContainText("Troca concluída");
  await expect(bia.locator(".trade-card")).toContainText("Aceita");

  // Taxas de 1 AGC para cada um (2% de ~10 e de 9, arredondado para cima).
  await bia.locator(".btn-close").click();
  await expect(bia.locator(".hud-balance")).toContainText("99 AGC");
  await ana.reload();
  await expect(ana.locator(".hud-balance")).toContainText("99 AGC");
  await ana.locator('[data-menu="trades"]').click();
  await ana.getByRole("tab", { name: /Enviadas/ }).click();
  await expect(ana.locator(".trade-card").first()).toContainText("Aceita");
});
