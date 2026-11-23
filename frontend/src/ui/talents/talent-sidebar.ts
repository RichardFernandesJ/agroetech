import type { TalentNode } from "@/services/talent-service";

import { describeEffect, type NodeEvaluation } from "./talent-rules";

export function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
}

export interface SidebarHandlers {
  onAllocate: (nodeId: string) => void;
}

const STATUS_LABELS: Record<string, string> = {
  owned: "Adquirido",
  available: "Disponível",
  locked: "Bloqueado",
  exclusive: "Indisponível (outro mestre escolhido)",
  unavailable: "Em breve",
};

/** Painel lateral com os detalhes do talento selecionado. */
export class TalentSidebar {
  constructor(
    private readonly root: HTMLElement,
    private readonly handlers: SidebarHandlers,
  ) {
    this.showEmpty();
  }

  showEmpty(): void {
    this.root.innerHTML = `
      <p class="eyebrow">Talentos</p>
      <h3>Escolha um caminho</h3>
      <p class="talent-hint">
        Clique em um talento do mapa para ver custo, requisitos e benefícios.
        Arraste para mover o mapa e use a roda do mouse para aproximar.
      </p>
      <ul class="talent-legend">
        <li><span class="dot owned"></span> Adquirido</li>
        <li><span class="dot available"></span> Pode adquirir agora</li>
        <li><span class="dot locked"></span> Bloqueado</li>
      </ul>`;
  }

  show(node: TalentNode, evaluation: NodeEvaluation, busy: boolean, branchName: string): void {
    const effects = node.effects
      .map((effect) => `<li>${escapeHtml(describeEffect(effect.stat, effect.value_bp, effect.scope))}</li>`)
      .join("");
    const requirements =
      evaluation.status === "owned"
        ? ""
        : evaluation.missing.length > 0
          ? `<h4>Ainda falta</h4><ul class="talent-missing">${evaluation.missing
              .map((text) => `<li>${escapeHtml(text)}</li>`)
              .join("")}</ul>`
          : `<p class="talent-ready">Todos os requisitos cumpridos.</p>`;

    const canBuy = evaluation.status === "available" && !busy;
    this.root.innerHTML = `
      <p class="eyebrow">${escapeHtml(branchName)} · ${escapeHtml(node.tier_name)}</p>
      <h3>${escapeHtml(node.name)}</h3>
      <p class="talent-status status-${evaluation.status}">${STATUS_LABELS[evaluation.status] ?? ""}</p>
      <p class="talent-desc">${escapeHtml(node.description)}</p>
      <div class="talent-facts">
        <span>Custo: <strong>${node.cost}</strong> pt</span>
        <span>Nível mín.: <strong>${node.min_level}</strong></span>
      </div>
      <h4>Benefícios</h4>
      <ul class="talent-effects">${effects}</ul>
      ${requirements}
      <button type="button" class="primary-button talent-buy" ${canBuy ? "" : "disabled"}>
        ${evaluation.status === "owned" ? "Já adquirido" : "Adquirir talento"}
      </button>`;

    this.root.querySelector<HTMLButtonElement>(".talent-buy")?.addEventListener("click", () => {
      this.handlers.onAllocate(node.id);
    });
  }
}
