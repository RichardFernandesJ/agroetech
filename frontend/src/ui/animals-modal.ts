import { ApiError } from "@/services/api-client";
import { animalService, type Animal, type AnimalsState, type Species } from "@/services/animal-service";
import { propertyService } from "@/services/property-service";

import { formatDuration } from "./format";
import { escapeHtml } from "./talents/talent-sidebar";

export interface AnimalsModalOptions {
  propertyId: string;
  token: string;
  /** Após qualquer ação: o mundo atualiza inventário, saldo e XP. */
  onChange: () => void;
  onOpenBuildings: () => void;
  onClose: () => void;
}

const ICONS: Record<string, string> = { galinha: "🐔", vaca: "🐄", ovelha: "🐑" };
const PRODUCT_ICONS: Record<string, string> = { animal_ovo: "🥚", animal_leite: "🥛", animal_la: "🧶" };
const REFRESH_MS = 5000;

/**
 * Curral: abrigos, animais (alimentar, ver produção) e compra de novos.
 * Tudo por clique; o servidor calcula a produção offline.
 */
export class AnimalsModal {
  private readonly root: HTMLDivElement;
  private state: AnimalsState | null = null;
  private stock = new Map<string, number>();
  private message = "";
  private busy = false;
  private destroyed = false;
  private pressed = false;
  private pendingRender = false;
  private readonly timer: number;

  constructor(private readonly options: AnimalsModalOptions) {
    this.root = document.createElement("div");
    this.root.className = "overlay";
    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);

    this.root.addEventListener("click", (event) => {
      if (event.target === this.root) {
        this.options.onClose();
      }
    });

    this.root.addEventListener("pointerdown", () => {
      this.pressed = true;
    });
    window.addEventListener("pointerup", this.releasePointer);
    window.addEventListener("pointercancel", this.releasePointer);

    this.render();
    void this.load();
    this.timer = window.setInterval(() => {
      if (!this.busy) {
        void this.load();
      }
    }, REFRESH_MS);
  }

  /** Solta o ponteiro e, se houve atualização no meio do clique, desenha depois dele. */
  private readonly releasePointer = (): void => {
    this.pressed = false;
    if (this.pendingRender) {
      window.setTimeout(() => this.render(), 0);
    }
  };

  destroy(): void {
    this.destroyed = true;
    window.removeEventListener("pointerup", this.releasePointer);
    window.removeEventListener("pointercancel", this.releasePointer);
    window.clearInterval(this.timer);
    this.root.remove();
  }

  // ---------------------------------------------------------------- dados
  private async load(): Promise<void> {
    try {
      const [state, inventory] = await Promise.all([
        animalService.getState(this.options.propertyId, this.options.token),
        propertyService.getInventory(this.options.propertyId, this.options.token),
      ]);
      this.state = state;
      this.stock = new Map(inventory.items.map((item) => [item.item_id, item.quantity]));
    } catch (error) {
      this.message = this.describeError(error);
    }
    this.render();
  }

  private async run(action: () => Promise<AnimalsState>, success: (s: AnimalsState) => string) {
    if (this.busy) {
      return;
    }
    this.busy = true;
    this.message = "";
    this.render();
    try {
      const next = await action();
      this.state = next;
      this.message = success(next);
      const inventory = await propertyService.getInventory(
        this.options.propertyId,
        this.options.token,
      );
      this.stock = new Map(inventory.items.map((item) => [item.item_id, item.quantity]));
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

  private get ids(): { propertyId: string; token: string } {
    return { propertyId: this.options.propertyId, token: this.options.token };
  }

  // -------------------------------------------------------------- exibição
  private animalCard(animal: Animal, species: Species | undefined): string {
    const stock = species ? (this.stock.get(species.feed_item) ?? 0) : 0;
    const disabled = this.busy || stock === 0 ? "disabled" : "";
    const status = animal.is_fed
      ? `😋 Alimentada por ${formatDuration(animal.fed_seconds_left)}`
      : "😟 Com fome";
    const next =
      animal.seconds_to_next !== null
        ? `Próximo ${escapeHtml(animal.product_name.toLowerCase())} em ${formatDuration(animal.seconds_to_next)}`
        : animal.stored >= animal.max_stored
          ? "Estoque cheio: colete!"
          : "Sem produção (alimente)";
    const feedName = species ? escapeHtml(species.feed_name) : "ração";
    return `
      <article class="animal-card ${animal.is_fed ? "" : "hungry"}">
        <div class="animal-head">
          <span class="animal-icon">${ICONS[animal.species] ?? "🐾"}</span>
          <div>
            <strong>${escapeHtml(animal.species_name)}</strong>
            <small>${status}</small>
          </div>
          <span class="animal-stored">${PRODUCT_ICONS[animal.product_item] ?? "📦"} ${animal.stored}/${animal.max_stored}</span>
        </div>
        <p class="animal-next">${next}</p>
        <div class="animal-feed">
          <span>Ração: ${feedName} (você tem ${stock})</span>
          <span class="trade-actions">
            <button type="button" class="btn-trade" data-feed="${animal.id}" data-units="1" ${disabled}>×1</button>
            <button type="button" class="btn-trade" data-feed="${animal.id}" data-units="4" ${disabled}>×4</button>
            <button type="button" class="btn-trade" data-feed="${animal.id}" data-units="64" ${disabled}>Máx</button>
          </span>
        </div>
      </article>`;
  }

  private speciesCard(species: Species): string {
    const reason = species.blocked_reason
      ? `<p class="building-blocked">${escapeHtml(species.blocked_reason)}</p>`
      : "";
    return `
      <article class="animal-card species">
        <div class="animal-head">
          <span class="animal-icon">${ICONS[species.id] ?? "🐾"}</span>
          <div>
            <strong>${escapeHtml(species.name)}</strong>
            <small>Você tem ${species.owned} · Nível ${species.min_player_level}</small>
          </div>
        </div>
        <p class="animal-next">${escapeHtml(species.description)}</p>
        <p class="animal-next">
          1 ${escapeHtml(species.product_name.toLowerCase())} a cada ${formatDuration(species.produce_seconds)}
          (vale ${species.sell_price} AGC) · come ${escapeHtml(species.feed_name.toLowerCase())}
        </p>
        <button type="button" class="primary-button" data-buy="${species.id}"
          ${species.can_buy && !this.busy ? "" : "disabled"}>Comprar por ${species.price} AGC</button>
        ${reason}
      </article>`;
  }

  private render(): void {
    if (this.destroyed) {
      return;
    }
    if (this.pressed) {
      this.pendingRender = true;
      return;
    }
    this.pendingRender = false;
    const state = this.state;
    const speciesById = new Map((state?.species ?? []).map((s) => [s.id, s]));
    const readyTotal = state?.animals.reduce((sum, a) => sum + a.stored, 0) ?? 0;
    const hasAnimals = (state?.animals.length ?? 0) > 0;

    const housings = (state?.housings ?? [])
      .map(
        (h) => `<span class="housing-chip ${h.capacity === 0 ? "empty" : ""}">
          ${escapeHtml(h.name)}: ${h.capacity === 0 ? "não construído" : `${h.used}/${h.capacity}`}
        </span>`,
      )
      .join("");

    const animals = hasAnimals
      ? state!.animals.map((a) => this.animalCard(a, speciesById.get(a.species))).join("")
      : `<p class="empty-list">Você ainda não tem animais. Construa um abrigo e compre o primeiro!</p>`;

    this.root.innerHTML = `
      <section class="panel animals-panel" role="dialog" aria-modal="true" aria-labelledby="animals-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Curral da Ilha</p>
            <h2 id="animals-title">Animais</h2>
          </div>
          <div class="market-balance" aria-label="Saldo">🪙 <strong>${state?.balance ?? "–"}</strong> AGC</div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>

        <div class="housing-row">
          ${housings}
          <button type="button" class="btn-trade" data-action="buildings">🏗️ Construções</button>
        </div>

        <p class="market-message" role="status" ${this.message ? "" : "hidden"}>${escapeHtml(this.message)}</p>

        <div class="animals-actions">
          <button type="button" class="primary-button" data-action="collect"
            ${readyTotal > 0 && !this.busy ? "" : "disabled"}>🧺 Coletar tudo (${readyTotal})</button>
          <button type="button" class="btn-trade" data-action="feed-all" ${hasAnimals && !this.busy ? "" : "disabled"}>
            Alimentar todos (×4)</button>
        </div>

        <h3 class="animals-subtitle">Seus animais</h3>
        <div class="animals-list">${animals}</div>

        <h3 class="animals-subtitle">Comprar animais</h3>
        <div class="animals-list">${(state?.species ?? []).map((s) => this.speciesCard(s)).join("")}</div>
      </section>`;

    this.bind();
  }

  private bind(): void {
    const { propertyId, token } = this.ids;
    this.root.querySelector(".btn-close")?.addEventListener("click", () => this.options.onClose());
    this.root.querySelector('[data-action="buildings"]')?.addEventListener("click", () =>
      this.options.onOpenBuildings(),
    );

    this.root.querySelector('[data-action="collect"]')?.addEventListener("click", () => {
      void this.run(
        () => animalService.collect(propertyId, token),
        (s) => {
          const items = Object.entries(s.products)
            .map(([item, qty]) => `${qty}× ${PRODUCT_ICONS[item] ?? ""} ${this.productName(item)}`)
            .join(", ");
          return `Coletou ${items} (+${s.xp_gained} XP).`;
        },
      );
    });

    this.root.querySelector('[data-action="feed-all"]')?.addEventListener("click", () => {
      void this.run(
        () => animalService.feedAll(propertyId, 4, token),
        (s) => `Animais alimentados (${Object.values(s.units_fed).reduce((a, b) => a + b, 0)} porções).`,
      );
    });

    this.root.querySelectorAll<HTMLButtonElement>("[data-feed]").forEach((button) => {
      button.addEventListener("click", () => {
        const units = Number(button.dataset.units);
        void this.run(
          () => animalService.feed(propertyId, button.dataset.feed ?? "", units, token),
          (s) => `Alimentado (${Object.values(s.units_fed).reduce((a, b) => a + b, 0)} porções).`,
        );
      });
    });

    this.root.querySelectorAll<HTMLButtonElement>("[data-buy]").forEach((button) => {
      button.addEventListener("click", () => {
        const species = this.state?.species.find((s) => s.id === button.dataset.buy);
        void this.run(
          () => animalService.buy(propertyId, button.dataset.buy ?? "", token),
          () => `Você comprou ${species ? `uma ${species.name.toLowerCase()}` : "um animal"}!`,
        );
      });
    });
  }

  private productName(itemId: string): string {
    return this.state?.species.find((s) => s.product_item === itemId)?.product_name ?? itemId;
  }
}
