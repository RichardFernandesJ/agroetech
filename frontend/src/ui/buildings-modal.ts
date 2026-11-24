import { ApiError } from "@/services/api-client";
import {
  buildingService,
  type Building,
  type BuildingLevel,
  type BuildingsState,
} from "@/services/building-service";

import { describeEffect } from "./talents/talent-rules";
import { escapeHtml } from "./talents/talent-sidebar";

export interface BuildingsModalOptions {
  propertyId: string;
  token: string;
  /** Construção a destacar ao abrir (ex.: ao clicar no poço). */
  focus?: string;
  /** Após uma melhoria: o mundo atualiza talhões e saldo. */
  onChange: (state: BuildingsState) => void;
  onClose: () => void;
}

const ICONS: Record<string, string> = { sede: "🏡", poco: "💧", galinheiro: "🐔", estabulo: "🐄", moinho: "🌾", padaria: "🍞", queijaria: "🧀" };

/** Lista as construções, o que cada nível entrega e permite melhorar com um clique. */
export class BuildingsModal {
  private readonly root: HTMLDivElement;
  private state: BuildingsState | null = null;
  private message = "";
  private busy = false;
  private destroyed = false;

  constructor(private readonly options: BuildingsModalOptions) {
    this.root = document.createElement("div");
    this.root.className = "overlay";
    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);

    this.root.addEventListener("click", (event) => {
      if (event.target === this.root) {
        this.options.onClose();
      }
    });

    this.render();
    void this.load();
  }

  destroy(): void {
    this.destroyed = true;
    this.root.remove();
  }

  private async load(): Promise<void> {
    try {
      this.state = await buildingService.getState(this.options.propertyId, this.options.token);
    } catch (error) {
      this.message = this.describeError(error);
    }
    this.render();
  }

  private async upgrade(buildingId: string): Promise<void> {
    if (this.busy) {
      return;
    }
    this.busy = true;
    this.message = "";
    this.render();
    try {
      const next = await buildingService.upgrade(
        this.options.propertyId,
        buildingId,
        this.options.token,
      );
      const name = next.buildings.find((b) => b.id === buildingId)?.name ?? "Construção";
      const level = next.buildings.find((b) => b.id === buildingId)?.level ?? 0;
      this.state = next;
      this.message = `${name} melhorada para o nível ${level}!`;
      this.options.onChange(next);
    } catch (error) {
      this.message = this.describeError(error);
    } finally {
      this.busy = false;
      if (!this.destroyed) {
        this.render();
      }
    }
  }

  private describeError(error: unknown): string {
    return error instanceof ApiError ? error.message : "Não foi possível falar com o servidor.";
  }

  private benefits(info: BuildingLevel | null): string {
    if (!info) {
      return "Ainda não construído";
    }
    const lines: string[] = [];
    if (info.plots !== null) {
      lines.push(`${info.plots} talhões`);
    }
    if (info.capacity !== null) {
      lines.push(`abriga ${info.capacity} animais`);
    }
    if (info.job_slots !== null) {
      lines.push(`${info.job_slots} vaga(s) de produção`);
    }
    for (const effect of info.effects) {
      lines.push(describeEffect(effect.stat, effect.value_bp, effect.scope));
    }
    return lines.length > 0 ? lines.map(escapeHtml).join(" · ") : "—";
  }

  private card(building: Building): string {
    const focused = this.options.focus === building.id ? " focused" : "";
    const next = building.next;
    const upgradeBlock = next
      ? `
        <div class="building-next">
          <p class="building-next-title">Próximo nível (${next.level})</p>
          <p>${this.benefits(next)}</p>
          <p class="building-cost">
            Custo: <strong>${next.cost} AGC</strong> · Nível de jogador ${next.min_player_level}
          </p>
          <button type="button" class="primary-button building-upgrade"
            data-building="${building.id}" ${building.can_upgrade && !this.busy ? "" : "disabled"}>
            ${this.busy ? "Aguarde..." : `Melhorar por ${next.cost} AGC`}
          </button>
          ${
            building.blocked_reason
              ? `<p class="building-blocked">${escapeHtml(building.blocked_reason)}</p>`
              : ""
          }
        </div>`
      : `<p class="building-max">✔ Nível máximo alcançado</p>`;

    return `
      <article class="building-card${focused}">
        <div class="building-head">
          <span class="building-icon">${ICONS[building.id] ?? "🏗️"}</span>
          <div>
            <h3>${escapeHtml(building.name)}</h3>
            <small>Nível ${building.level} de ${building.max_level}</small>
          </div>
        </div>
        <p class="building-desc">${escapeHtml(building.description)}</p>
        <p class="building-now"><span>Agora:</span> ${this.benefits(building.current)}</p>
        ${upgradeBlock}
      </article>`;
  }

  private render(): void {
    if (this.destroyed) {
      return;
    }
    const body = this.state
      ? this.state.buildings.map((building) => this.card(building)).join("")
      : `<p class="empty-list">Carregando construções...</p>`;

    this.root.innerHTML = `
      <section class="panel buildings-panel" role="dialog" aria-modal="true" aria-labelledby="buildings-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Fazenda na Ilha</p>
            <h2 id="buildings-title">Construções</h2>
          </div>
          <div class="market-balance" aria-label="Saldo">🪙 <strong>${this.state?.balance ?? "–"}</strong> AGC</div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>
        <p class="market-message" role="status" ${this.message ? "" : "hidden"}>${escapeHtml(this.message)}</p>
        <div class="buildings-list">${body}</div>
      </section>`;

    this.root.querySelector(".btn-close")?.addEventListener("click", () => this.options.onClose());
    this.root.querySelectorAll<HTMLButtonElement>(".building-upgrade").forEach((button) => {
      button.addEventListener("click", () => void this.upgrade(button.dataset.building ?? ""));
    });
  }
}
