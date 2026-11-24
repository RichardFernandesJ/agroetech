import { ApiError } from "@/services/api-client";
import {
  craftingService,
  type CraftingJob,
  type CraftingState,
  type Recipe,
  type Station,
} from "@/services/crafting-service";

import { formatDuration } from "./format";
import { PressGuard } from "./press-guard";
import { escapeHtml } from "./talents/talent-sidebar";

export interface CraftingModalOptions {
  propertyId: string;
  token: string;
  /** Após iniciar ou coletar: o mundo atualiza inventário e XP. */
  onChange: () => void;
  onOpenBuildings: () => void;
  onClose: () => void;
}

const STATION_ICONS: Record<string, string> = { moinho: "🌾", padaria: "🍞", queijaria: "🧀" };
const ITEM_ICONS: Record<string, string> = {
  processed_farinha: "🌾",
  processed_pao: "🍞",
  processed_bolo: "🎂",
  processed_queijo: "🧀",
  processed_manteiga: "🧈",
};
const REFRESH_MS = 10_000;

/**
 * Oficina: estações (moinho, padaria, queijaria), receitas e trabalhos em andamento.
 * A contagem regressiva roda no cliente; o servidor decide quando está pronto.
 */
export class CraftingModal {
  private readonly root: HTMLDivElement;
  private readonly guard: PressGuard;
  private state: CraftingState | null = null;
  private message = "";
  private busy = false;
  private destroyed = false;
  private notifiedReady = false;
  private readonly refreshTimer: number;
  private readonly tickTimer: number;

  constructor(private readonly options: CraftingModalOptions) {
    this.root = document.createElement("div");
    this.root.className = "overlay";
    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);

    this.root.addEventListener("click", (event) => {
      if (event.target === this.root) {
        this.options.onClose();
      }
    });
    this.guard = new PressGuard(this.root, () => this.render());

    this.render();
    void this.load();
    this.refreshTimer = window.setInterval(() => {
      if (!this.busy) {
        void this.load();
      }
    }, REFRESH_MS);
    this.tickTimer = window.setInterval(() => this.tick(), 1000);
  }

  destroy(): void {
    this.destroyed = true;
    this.guard.dispose();
    window.clearInterval(this.refreshTimer);
    window.clearInterval(this.tickTimer);
    this.root.remove();
  }

  // ---------------------------------------------------------------- dados
  private async load(): Promise<void> {
    try {
      this.state = await craftingService.getState(this.options.propertyId, this.options.token);
      this.notifiedReady = false;
    } catch (error) {
      this.message = this.describeError(error);
    }
    this.render();
  }

  private async run(action: () => Promise<CraftingState>, success: (s: CraftingState) => string) {
    if (this.busy) {
      return;
    }
    this.busy = true;
    this.message = "";
    this.render();
    try {
      const next = await action();
      this.state = next;
      this.notifiedReady = false;
      this.message = success(next);
      this.options.onChange();
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

  /** Atualiza só os contadores (sem redesenhar) e recarrega quando algo termina. */
  private tick(): void {
    let finishedNow = false;
    this.root.querySelectorAll<HTMLElement>("[data-finish]").forEach((element) => {
      const start = Date.parse(element.dataset.began ?? "");
      const finish = Date.parse(element.dataset.finish ?? "");
      const left = Math.max(0, Math.round((finish - Date.now()) / 1000));
      const bar = element.querySelector<HTMLElement>(".job-fill");
      const label = element.querySelector<HTMLElement>(".job-time");
      const total = Math.max(1, finish - start);
      if (bar) {
        bar.style.width = `${Math.min(100, Math.round(((Date.now() - start) / total) * 100))}%`;
      }
      if (label) {
        label.textContent = left === 0 ? "Pronto!" : formatDuration(left);
      }
      if (left === 0 && element.dataset.ready !== "1") {
        finishedNow = true;
      }
    });
    if (finishedNow && !this.notifiedReady && !this.busy) {
      this.notifiedReady = true;
      void this.load();
    }
  }

  // -------------------------------------------------------------- exibição
  private jobRow(job: CraftingJob): string {
    return `
      <div class="job-row" data-finish="${job.finish_at}" data-began="${job.started_at}" data-ready="${job.ready ? 1 : 0}">
        <span>${ITEM_ICONS[job.output_item] ?? "📦"} ${job.batches}× ${escapeHtml(job.recipe_name)}
          <small>→ ${job.output_quantity} ${escapeHtml(job.output_name)}</small></span>
        <span class="job-bar"><i class="job-fill" style="width:${job.ready ? 100 : 0}%"></i></span>
        <span class="job-time">${job.ready ? "Pronto!" : formatDuration(job.seconds_left)}</span>
      </div>`;
  }

  private recipeRow(recipe: Recipe, station: Station): string {
    const inputs = recipe.inputs
      .map((i) => `${i.per_batch}× ${escapeHtml(i.name)} <small>(tem ${i.have})</small>`)
      .join(" + ");
    const seconds = Math.round(recipe.duration_seconds * (1 + station.time_bonus_bp / 10_000));
    const button = (label: string, batches: number) =>
      `<button type="button" class="btn-trade" data-start="${recipe.id}" data-batches="${batches}"
        ${recipe.can_craft && batches >= 1 && batches <= recipe.max_batches && !this.busy ? "" : "disabled"}>${label}</button>`;
    return `
      <div class="recipe-row ${recipe.can_craft ? "" : "blocked"}">
        <div>
          <strong>${ITEM_ICONS[recipe.output_item] ?? "📦"} ${escapeHtml(recipe.name)}</strong>
          <p>${inputs} → <b>${recipe.output_quantity}× ${escapeHtml(recipe.output_name)}</b></p>
          <small class="recipe-meta">${formatDuration(seconds)} por lote · +${recipe.xp} XP · nível ${recipe.min_player_level}</small>
          ${recipe.blocked_reason ? `<small class="recipe-meta building-blocked">${escapeHtml(recipe.blocked_reason)}</small>` : ""}
        </div>
        <span class="trade-actions">
          ${button("×1", 1)}${button("×5", 5)}${button(`Máx (${recipe.max_batches})`, recipe.max_batches)}
        </span>
      </div>`;
  }

  private stationCard(station: Station, recipes: Recipe[]): string {
    const built = station.job_slots > 0;
    const speed =
      station.time_bonus_bp < 0 ? ` · ${Math.abs(station.time_bonus_bp) / 100}% mais rápido` : "";
    const jobs = station.jobs.map((job) => this.jobRow(job)).join("");
    const mine = recipes.filter((recipe) => recipe.station === station.building_id);
    return `
      <article class="station-card ${built ? "" : "unbuilt"}">
        <div class="building-head">
          <span class="building-icon">${STATION_ICONS[station.building_id] ?? "🏭"}</span>
          <div>
            <h3>${escapeHtml(station.name)}</h3>
            <small>${
              built
                ? `Nível ${station.level} · vagas ${station.used_slots}/${station.job_slots}${speed}`
                : "Não construída — use 🏗️ Construções"
            }</small>
          </div>
        </div>
        ${jobs}
        ${mine.map((recipe) => this.recipeRow(recipe, station)).join("")}
      </article>`;
  }

  private render(): void {
    if (this.destroyed || this.guard.defer()) {
      return;
    }
    const state = this.state;
    const ready = state?.stations.reduce((sum, s) => sum + s.jobs.filter((j) => j.ready).length, 0) ?? 0;
    const cards = state
      ? state.stations.map((station) => this.stationCard(station, state.recipes)).join("")
      : `<p class="empty-list">Carregando a oficina...</p>`;

    this.root.innerHTML = `
      <section class="panel crafting-panel" role="dialog" aria-modal="true" aria-labelledby="crafting-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Oficina da Ilha</p>
            <h2 id="crafting-title">Fabricação</h2>
          </div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>
        <div class="animals-actions">
          <button type="button" class="primary-button" data-action="collect" ${ready > 0 && !this.busy ? "" : "disabled"}>
            🧺 Coletar prontos (${ready})</button>
          <button type="button" class="btn-trade" data-action="buildings">🏗️ Construções</button>
        </div>
        <p class="market-message" role="status" ${this.message ? "" : "hidden"}>${escapeHtml(this.message)}</p>
        <div class="stations-list">${cards}</div>
      </section>`;

    this.bind();
  }

  private bind(): void {
    const { propertyId, token } = this.options;
    this.root.querySelector(".btn-close")?.addEventListener("click", () => this.options.onClose());
    this.root.querySelector('[data-action="buildings"]')?.addEventListener("click", () =>
      this.options.onOpenBuildings(),
    );
    this.root.querySelector('[data-action="collect"]')?.addEventListener("click", () => {
      void this.run(
        () => craftingService.collect(propertyId, token),
        (s) => {
          const items = Object.entries(s.collected)
            .map(([item, qty]) => `${qty}× ${this.itemName(item)}`)
            .join(", ");
          return `Coletou ${items} (+${s.xp_gained} XP).`;
        },
      );
    });
    this.root.querySelectorAll<HTMLButtonElement>("[data-start]").forEach((button) => {
      button.addEventListener("click", () => {
        const recipe = this.state?.recipes.find((r) => r.id === button.dataset.start);
        const batches = Number(button.dataset.batches);
        void this.run(
          () => craftingService.start(propertyId, button.dataset.start ?? "", batches, token),
          () => `Produção iniciada: ${batches}× ${recipe?.name ?? "receita"}.`,
        );
      });
    });
  }

  private itemName(itemId: string): string {
    return this.state?.recipes.find((r) => r.output_item === itemId)?.output_name ?? itemId;
  }
}
