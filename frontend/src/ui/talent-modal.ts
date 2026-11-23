import { ApiError } from "@/services/api-client";
import {
  talentService,
  type TalentCatalog,
  type TalentNode,
  type TalentState,
} from "@/services/talent-service";

import { TalentMap } from "./talents/talent-map";
import { TalentPresetsBar } from "./talents/talent-presets-bar";
import {
  branchMaxPath,
  buildContext,
  describeEffect,
  evaluateNode,
  spentInBranch,
  type EvaluationContext,
  type NodeStatus,
} from "./talents/talent-rules";
import { escapeHtml, TalentSidebar } from "./talents/talent-sidebar";

export interface TalentModalOptions {
  token: string;
  /** Chamado quando uma ação pode ter mexido na carteira (redefinição paga). */
  onWalletChange: () => void;
  onClose: () => void;
}

/**
 * Árvore de talentos: mapa interativo (pan/zoom), painel lateral com detalhes,
 * indicadores por ramo e presets. Todas as decisões são do servidor; aqui só
 * se exibe o estado e se enviam intenções (adquirir, trocar, redefinir).
 */
export class TalentModal {
  private readonly root: HTMLDivElement;
  private readonly onKeyDown: (event: KeyboardEvent) => void;
  private catalog?: TalentCatalog;
  private state?: TalentState;
  private ctx?: EvaluationContext;
  private map?: TalentMap;
  private sidebar?: TalentSidebar;
  private presetsBar?: TalentPresetsBar;
  private selectedId: string | null = null;
  private busy = false;
  private destroyed = false;

  constructor(private readonly options: TalentModalOptions) {
    this.root = document.createElement("div");
    this.root.className = "overlay talent-overlay";
    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);

    this.root.innerHTML = `
      <section class="talent-modal" role="dialog" aria-modal="true" aria-labelledby="talent-title">
        <header class="talent-header">
          <div class="talent-title">
            <p class="eyebrow">Mapa de especializações</p>
            <h2 id="talent-title">Árvore de Talentos</h2>
          </div>
          <div class="talent-points" aria-live="polite">
            <span class="talent-points-value">–</span>
            <span class="talent-points-label">pontos disponíveis</span>
          </div>
          <div class="talent-zoom">
            <button type="button" class="hud-btn hud-btn-zoom" data-zoom="in" title="Aproximar">+</button>
            <button type="button" class="hud-btn hud-btn-zoom" data-zoom="out" title="Afastar">−</button>
            <button type="button" class="hud-btn hud-btn-reset" data-zoom="fit" title="Centralizar nos talentos">⌂</button>
            <button type="button" class="hud-btn hud-btn-zoom" data-zoom="all" title="Ver o mapa inteiro">⤢</button>
          </div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </header>
        <div class="talent-branches" aria-label="Progresso por especialização"></div>
        <p class="talent-message" role="status" hidden></p>
        <div class="talent-body">
          <div class="talent-map-wrap"><p class="empty-list">Carregando o mapa...</p></div>
          <aside class="talent-sidebar"></aside>
        </div>
        <footer class="talent-footer"></footer>
        <div class="talent-tooltip" role="tooltip" hidden></div>
      </section>`;

    this.onKeyDown = (event) => {
      if (event.key === "Escape") {
        this.options.onClose();
      }
    };
    document.addEventListener("keydown", this.onKeyDown);

    this.root.addEventListener("click", (event) => {
      if (event.target === this.root) {
        this.options.onClose();
      }
    });
    this.root.querySelector(".btn-close")?.addEventListener("click", () => this.options.onClose());
    this.root.querySelectorAll<HTMLButtonElement>("[data-zoom]").forEach((button) => {
      button.addEventListener("click", () => {
        if (button.dataset.zoom === "in") this.map?.zoomBy(0.8);
        else if (button.dataset.zoom === "out") this.map?.zoomBy(1.25);
        else if (button.dataset.zoom === "all") this.map?.fitAll();
        else this.map?.fit();
      });
    });

    void this.load();
  }

  destroy(): void {
    this.destroyed = true;
    document.removeEventListener("keydown", this.onKeyDown);
    this.map?.destroy();
    this.root.remove();
  }

  // ---------------------------------------------------------------- carga
  private async load(): Promise<void> {
    try {
      const [catalog, state] = await Promise.all([
        talentService.getCatalog(),
        talentService.getState(this.options.token),
      ]);
      if (this.destroyed) {
        return;
      }
      this.catalog = catalog;
      this.state = state;
      this.mount();
    } catch (error) {
      this.showMessage(this.describe(error));
    }
  }

  private mount(): void {
    const catalog = this.catalog!;
    const wrap = this.root.querySelector<HTMLElement>(".talent-map-wrap")!;
    wrap.innerHTML = "";

    this.map = new TalentMap(wrap, {
      catalog,
      onSelect: (id) => this.select(id),
      onHover: (id, anchor) => this.showTooltip(id, anchor),
    });
    this.sidebar = new TalentSidebar(this.root.querySelector<HTMLElement>(".talent-sidebar")!, {
      onAllocate: (id) => void this.allocate(id),
    });
    this.presetsBar = new TalentPresetsBar(this.root.querySelector<HTMLElement>(".talent-footer")!, {
      onActivate: (id) => void this.run(() => talentService.activatePreset(id, this.options.token)),
      onCreate: () => void this.createPreset(),
      onRename: (id) => void this.renamePreset(id),
      onDelete: (id) => void this.deletePreset(id),
      onReset: () => void this.resetTalents(),
    });
    this.refresh(this.state!);
  }

  // -------------------------------------------------------------- exibição
  private refresh(state: TalentState): void {
    if (!this.catalog || this.destroyed) {
      return;
    }
    this.state = state;
    const active = state.presets.find((preset) => preset.is_active);
    const owned = new Set(active?.node_ids ?? []);
    this.ctx = buildContext(this.catalog, owned, state.level, state.points_available);

    const statuses = new Map<string, NodeStatus>();
    for (const node of this.catalog.nodes) {
      statuses.set(node.id, evaluateNode(node, this.ctx).status);
    }
    this.map?.setStatuses(statuses);
    this.map?.select(this.selectedId);

    this.root.querySelector(".talent-points-value")!.textContent = String(state.points_available);
    this.root.querySelector(".talent-points-label")!.textContent =
      `de ${state.points_total} · nível ${state.level}`;
    this.renderBranches();
    this.presetsBar?.render(state, this.busy);
    this.renderSelection();
  }

  private renderBranches(): void {
    if (!this.catalog || !this.ctx) {
      return;
    }
    const catalog = this.catalog;
    const ctx = this.ctx;
    const html = catalog.branches
      .map((branch) => {
        if (!branch.available) {
          return `<div class="branch-chip soon" title="${escapeHtml(branch.description)}">
            <span>${escapeHtml(branch.name)}</span><small>em breve</small></div>`;
        }
        const spent = spentInBranch(ctx, branch.id);
        const ratio = Math.min(1, spent / Math.max(1, branchMaxPath(catalog, branch.id)));
        return `<div class="branch-chip branch-${branch.id}" title="${escapeHtml(branch.description)}">
          <span>${escapeHtml(branch.name)}</span>
          <small>${spent} pt</small>
          <i class="branch-bar"><b style="width:${Math.round(ratio * 100)}%"></b></i></div>`;
      })
      .join("");
    this.root.querySelector(".talent-branches")!.innerHTML = html;
  }

  private select(nodeId: string | null): void {
    this.selectedId = nodeId;
    this.map?.select(nodeId);
    this.renderSelection();
  }

  private renderSelection(): void {
    if (!this.catalog || !this.ctx || !this.sidebar) {
      return;
    }
    const node = this.selectedId ? this.ctx.nodesById.get(this.selectedId) : undefined;
    if (!node) {
      this.sidebar.showEmpty();
      return;
    }
    const branchName = this.ctx.branchesById.get(node.branch)?.name ?? "Híbrido";
    this.sidebar.show(node, evaluateNode(node, this.ctx), this.busy, branchName);
  }

  private showTooltip(nodeId: string | null, anchor: DOMRect | null): void {
    const tooltip = this.root.querySelector<HTMLElement>(".talent-tooltip")!;
    const node: TalentNode | undefined = nodeId ? this.ctx?.nodesById.get(nodeId) : undefined;
    if (!node || !anchor || !this.ctx) {
      tooltip.hidden = true;
      return;
    }
    const evaluation = evaluateNode(node, this.ctx);
    const first = node.effects[0];
    tooltip.innerHTML = `
      <strong>${escapeHtml(node.name)}</strong>
      <small>${escapeHtml(node.tier_name)} · custo ${node.cost} pt · nível ${node.min_level}</small>
      ${first ? `<span>${escapeHtml(describeEffect(first.stat, first.value_bp, first.scope))}</span>` : ""}
      <em class="status-${evaluation.status}">${
        evaluation.status === "owned"
          ? "Adquirido"
          : evaluation.status === "available"
            ? "Clique para ver e adquirir"
            : "Bloqueado"
      }</em>`;
    tooltip.hidden = false;
    const width = tooltip.offsetWidth;
    const left = Math.min(window.innerWidth - width - 8, anchor.right + 8);
    const top = Math.min(window.innerHeight - tooltip.offsetHeight - 8, Math.max(8, anchor.top));
    tooltip.style.left = `${Math.max(8, left)}px`;
    tooltip.style.top = `${top}px`;
  }

  private showMessage(text: string): void {
    const element = this.root.querySelector<HTMLElement>(".talent-message");
    if (!element) {
      return;
    }
    element.textContent = text;
    element.hidden = text.length === 0;
  }

  private describe(error: unknown): string {
    return error instanceof ApiError ? error.message : "Não foi possível falar com o servidor.";
  }

  // ---------------------------------------------------------------- ações
  private async run(action: () => Promise<TalentState>, flashId?: string): Promise<boolean> {
    if (this.busy) {
      return false;
    }
    this.busy = true;
    this.showMessage("");
    this.presetsBar?.render(this.state!, true);
    try {
      const state = await action();
      this.busy = false;
      this.refresh(state);
      if (flashId) {
        this.map?.flash(flashId);
      }
      return true;
    } catch (error) {
      this.busy = false;
      this.showMessage(this.describe(error));
      if (this.state) {
        this.refresh(this.state);
      }
      return false;
    }
  }

  private async allocate(nodeId: string): Promise<void> {
    const node = this.ctx?.nodesById.get(nodeId);
    const ok = await this.run(() => talentService.allocate(nodeId, this.options.token), nodeId);
    if (ok && node) {
      this.showMessage(`Talento adquirido: ${node.name}.`);
    }
  }

  private async createPreset(): Promise<void> {
    const suggested = `Build ${(this.state?.presets.length ?? 0) + 1}`;
    const name = window.prompt("Nome da nova build:", suggested)?.trim();
    if (name) {
      await this.run(() => talentService.createPreset(name, this.options.token));
    }
  }

  private async renamePreset(id: string): Promise<void> {
    const current = this.state?.presets.find((preset) => preset.id === id)?.name ?? "";
    const name = window.prompt("Novo nome da build:", current)?.trim();
    if (name && name !== current) {
      await this.run(() => talentService.renamePreset(id, name, this.options.token));
    }
  }

  private async deletePreset(id: string): Promise<void> {
    const preset = this.state?.presets.find((entry) => entry.id === id);
    if (preset && window.confirm(`Excluir a build «${preset.name}»?`)) {
      await this.run(() => talentService.deletePreset(id, this.options.token));
    }
  }

  private async resetTalents(): Promise<void> {
    if (!this.state) {
      return;
    }
    const price = this.state.reset_is_free
      ? "A primeira redefinição é gratuita."
      : `Isso custa ${this.state.reset_cost} AGC.`;
    if (!window.confirm(`Redefinir todos os talentos da build ativa? ${price}`)) {
      return;
    }
    const ok = await this.run(async () => {
      const result = await talentService.reset(this.options.token);
      return result.state;
    });
    if (ok) {
      this.options.onWalletChange();
      this.showMessage("Talentos redefinidos. Distribua seus pontos novamente.");
    }
  }
}
