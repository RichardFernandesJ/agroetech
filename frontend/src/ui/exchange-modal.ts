import { ApiError } from "@/services/api-client";
import { economyService } from "@/services/economy-service";
import {
  estimateFee,
  exchangeService,
  type ExchangeInfo,
  type HistoryEntry,
  type Listing,
  type PriceInfo,
} from "@/services/exchange-service";
import { propertyService, type InventoryItem } from "@/services/property-service";

import { formatDuration } from "./format";
import { PressGuard } from "./press-guard";
import { escapeHtml } from "./talents/talent-sidebar";

type Tab = "buy" | "sell" | "mine" | "history";

export interface ExchangeModalOptions {
  propertyId: string;
  token: string;
  /** Após comprar, anunciar ou cancelar: o mundo atualiza inventário e saldo. */
  onChange: () => void;
  onClose: () => void;
}

const REFRESH_MS = 15_000;

/**
 * Praça dos Jogadores: mercado entre jogadores. Tudo por clique: quantidades e preço
 * usam botões (±, presets), sem digitar. O servidor valida faixa de preço, taxa e estoque.
 */
export class ExchangeModal {
  private readonly root: HTMLDivElement;
  private readonly guard: PressGuard;
  private readonly timer: number;
  private tab: Tab = "buy";
  private info: ExchangeInfo | null = null;
  private listings: Listing[] = [];
  private mine: Listing[] = [];
  private history: HistoryEntry[] = [];
  private inventory: InventoryItem[] = [];
  private balance: number | null = null;
  private filter = "";
  private message = "";
  private busy = false;
  private destroyed = false;

  // Formulário "Anunciar"
  private itemId = "";
  private quantity = 1;
  private price = 0;

  constructor(private readonly options: ExchangeModalOptions) {
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
    this.timer = window.setInterval(() => {
      if (!this.busy && this.tab === "buy") {
        void this.load();
      }
    }, REFRESH_MS);
  }

  destroy(): void {
    this.destroyed = true;
    this.guard.dispose();
    window.clearInterval(this.timer);
    this.root.remove();
  }

  // ---------------------------------------------------------------- dados
  private async load(): Promise<void> {
    const { token, propertyId } = this.options;
    try {
      const [info, listings, mine, history, inventory, wallet] = await Promise.all([
        exchangeService.getInfo(token),
        exchangeService.browse(token, this.filter || undefined),
        exchangeService.mine(token),
        exchangeService.history(token),
        propertyService.getInventory(propertyId, token),
        economyService.getWallet(token),
      ]);
      this.balance = wallet.balance;
      this.info = info;
      this.listings = listings;
      this.mine = mine;
      this.history = history;
      this.inventory = inventory.items;
    } catch (error) {
      this.message = this.describe(error);
    }
    this.render();
  }

  private async run(action: () => Promise<string>): Promise<void> {
    if (this.busy) {
      return;
    }
    this.busy = true;
    this.message = "";
    this.render();
    try {
      this.message = await action();
      await this.load();
      this.options.onChange();
    } catch (error) {
      this.message = this.describe(error);
    } finally {
      this.busy = false;
      if (!this.destroyed) {
        this.render();
      }
    }
  }

  private describe(error: unknown): string {
    return error instanceof ApiError ? error.message : "Não foi possível falar com o servidor.";
  }

  private priceOf(itemId: string): PriceInfo | undefined {
    return this.info?.prices.find((entry) => entry.item_id === itemId);
  }

  private sellable(): InventoryItem[] {
    const tradable = new Set(this.info?.prices.map((entry) => entry.item_id) ?? []);
    return this.inventory.filter((item) => item.quantity > 0 && tradable.has(item.item_id));
  }

  // ------------------------------------------------------------- exibição
  private expiresIn(listing: Listing): string {
    return formatDuration((Date.parse(listing.expires_at) - Date.now()) / 1000);
  }

  private buyTab(): string {
    const chips = [
      `<button type="button" class="chip ${this.filter === "" ? "active" : ""}" data-filter="">Todos</button>`,
      ...(this.info?.prices ?? [])
        .filter((entry) => entry.lowest_listing !== null || entry.item_id === this.filter)
        .map(
          (entry) =>
            `<button type="button" class="chip ${this.filter === entry.item_id ? "active" : ""}" data-filter="${entry.item_id}">${escapeHtml(entry.name)} <small>${entry.lowest_listing ?? "—"} AGC</small></button>`,
        ),
    ].join("");

    const rows = this.listings.length
      ? this.listings
          .map((listing) => {
            const max = listing.quantity_remaining;
            const affordable = Math.floor((this.balance ?? 0) / listing.unit_price);
            const button = (label: string, quantity: number) =>
              `<button type="button" class="btn-trade" data-buy="${listing.id}" data-qty="${quantity}"
                ${listing.is_mine || this.busy || quantity < 1 || quantity > max ? "disabled" : ""}>${label}</button>`;
            return `
              <div class="trade-row listing-row">
                <div class="trade-info"><div>
                  <strong>${escapeHtml(listing.item_name)} <small>×${max}</small></strong>
                  <small>${listing.is_mine ? "Seu anúncio" : `por ${escapeHtml(listing.seller_name)}`} · expira em ${this.expiresIn(listing)}</small>
                </div></div>
                <span class="trade-price">${listing.unit_price} AGC<small>/un</small></span>
                <div class="trade-actions">
                  ${button("×1", 1)}${button("×5", Math.min(5, max))}${button(`Tudo (${max})`, max)}
                </div>
                ${affordable < max && !listing.is_mine ? `<small class="listing-hint">Seu saldo paga ${affordable} un.</small>` : ""}
              </div>`;
          })
          .join("")
      : `<p class="empty-list">Nenhum anúncio${this.filter ? " deste item" : ""} no momento. Que tal anunciar o seu?</p>`;
    return `<div class="chip-row">${chips}</div><div class="trade-list">${rows}</div>`;
  }

  private sellTab(): string {
    const items = this.sellable();
    if (items.length === 0) {
      return `<p class="empty-list">Você não tem itens negociáveis no inventário.</p>`;
    }
    if (!items.some((item) => item.item_id === this.itemId)) {
      this.selectItem(items[0]!.item_id);
    }
    const selected = items.find((item) => item.item_id === this.itemId)!;
    const bounds = this.priceOf(this.itemId);
    const fee = estimateFee(this.price * this.quantity, this.info?.fee_basis_points ?? 500);
    const gross = this.price * this.quantity;
    const outOfRange = bounds ? this.price < bounds.minimum || this.price > bounds.maximum : false;
    const full = (this.info?.active_listings ?? 0) >= (this.info?.max_active_listings ?? 20);

    const itemButtons = items
      .map(
        (item) =>
          `<button type="button" class="chip ${item.item_id === this.itemId ? "active" : ""}" data-pick="${item.item_id}">${escapeHtml(item.name)} <small>×${item.quantity}</small></button>`,
      )
      .join("");
    const qtyButton = (label: string, value: number) =>
      `<button type="button" class="btn-trade" data-setqty="${value}">${label}</button>`;
    const priceButton = (label: string, value: number) =>
      `<button type="button" class="btn-trade" data-setprice="${value}">${label}</button>`;

    return `
      <div class="chip-row">${itemButtons}</div>
      <div class="sell-form">
        <div class="stepper"><span>Quantidade</span>
          <button type="button" class="btn-trade" data-stepqty="-1" aria-label="Menos">−</button>
          <strong data-testid="sell-qty">${this.quantity}</strong>
          <button type="button" class="btn-trade" data-stepqty="1" aria-label="Mais">+</button>
          ${qtyButton("×5", Math.min(5, selected.quantity))}${qtyButton("×10", Math.min(10, selected.quantity))}${qtyButton(`Tudo (${selected.quantity})`, selected.quantity)}
        </div>
        <div class="stepper"><span>Preço por unidade</span>
          <button type="button" class="btn-trade" data-stepprice="-1" aria-label="Menos">−</button>
          <strong data-testid="sell-price">${this.price} AGC</strong>
          <button type="button" class="btn-trade" data-stepprice="1" aria-label="Mais">+</button>
          ${bounds ? `${priceButton("Mín", bounds.minimum)}${priceButton("Referência", bounds.reference)}${priceButton("Máx", bounds.maximum)}${bounds.lowest_listing ? priceButton("Mais barato", bounds.lowest_listing) : ""}` : ""}
        </div>
        ${bounds ? `<p class="trade-note">Faixa permitida: ${bounds.minimum} a ${bounds.maximum} AGC (referência ${bounds.reference}${bounds.last_price ? ` · última venda ~${bounds.last_price}` : ""}).</p>` : ""}
        <p class="sell-summary">Total <strong>${gross} AGC</strong> · taxa ${fee} AGC · você recebe <strong>${gross - fee} AGC</strong></p>
        <button type="button" class="primary-button" data-action="create"
          ${this.busy || outOfRange || full || this.quantity < 1 ? "disabled" : ""}>
          ${full ? "Limite de anúncios atingido" : `Anunciar ${this.quantity}× ${escapeHtml(selected.name)}`}</button>
        <p class="trade-note">Os itens ficam em custódia até vender, cancelar ou expirar (${this.info?.listing_hours ?? 48} h).</p>
      </div>`;
  }

  private mineTab(): string {
    if (this.mine.length === 0) {
      return `<p class="empty-list">Você ainda não anunciou nada.</p>`;
    }
    const labels: Record<string, string> = {
      active: "Ativo",
      sold: "Vendido",
      cancelled: "Cancelado",
      expired: "Expirado",
    };
    return `<div class="trade-list">${this.mine
      .map(
        (listing) => `
        <div class="trade-row listing-row">
          <div class="trade-info"><div>
            <strong>${escapeHtml(listing.item_name)} <small>${listing.quantity_remaining}/${listing.quantity_initial}</small></strong>
            <small>${labels[listing.status] ?? listing.status}${listing.status === "active" ? ` · expira em ${this.expiresIn(listing)}` : ""}</small>
          </div></div>
          <span class="trade-price">${listing.unit_price} AGC<small>/un</small></span>
          <div class="trade-actions">
            <button type="button" class="btn-trade" data-cancel="${listing.id}"
              ${listing.status === "active" && !this.busy ? "" : "disabled"}>Cancelar</button>
          </div>
        </div>`,
      )
      .join("")}</div>`;
  }

  private historyTab(): string {
    if (this.history.length === 0) {
      return `<p class="empty-list">Nenhuma negociação ainda.</p>`;
    }
    return `<div class="trade-list">${this.history
      .map(
        (entry) => `
        <div class="trade-row ledger-row">
          <div class="trade-info"><div>
            <strong>${entry.role === "buyer" ? "Compra" : "Venda"} · ${entry.quantity}× ${escapeHtml(entry.item_name)}</strong>
            <small>${entry.role === "buyer" ? "de" : "para"} ${escapeHtml(entry.counterpart)} · ${new Date(entry.created_at).toLocaleString("pt-BR")}${entry.role === "seller" ? ` · taxa ${entry.fee}` : ""}</small>
          </div></div>
          <span class="trade-price ${entry.amount >= 0 ? "gain" : "loss"}">${entry.amount >= 0 ? "+" : ""}${entry.amount} AGC</span>
          <span class="ledger-balance">${entry.unit_price} AGC/un</span>
        </div>`,
      )
      .join("")}</div>`;
  }

  private selectItem(itemId: string): void {
    this.itemId = itemId;
    const bounds = this.priceOf(itemId);
    this.quantity = 1;
    this.price = bounds?.lowest_listing ?? bounds?.reference ?? 1;
  }

  private render(): void {
    if (this.destroyed || this.guard.defer()) {
      return;
    }
    const gate =
      this.info && this.info.player_level < this.info.min_level
        ? `<p class="market-message">O mercado entre jogadores exige nível ${this.info.min_level} (você está no ${this.info.player_level}).</p>`
        : "";
    const body =
      this.tab === "buy"
        ? this.buyTab()
        : this.tab === "sell"
          ? this.sellTab()
          : this.tab === "mine"
            ? this.mineTab()
            : this.historyTab();
    const tabButton = (tab: Tab, label: string) =>
      `<button type="button" class="tab ${this.tab === tab ? "active" : ""}" data-tab="${tab}" role="tab" aria-selected="${this.tab === tab}">${label}</button>`;

    this.root.innerHTML = `
      <section class="panel exchange-panel" role="dialog" aria-modal="true" aria-labelledby="exchange-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Mercado entre jogadores</p>
            <h2 id="exchange-title">Praça dos Jogadores</h2>
          </div>
          <div class="market-balance" aria-label="Taxa">Taxa do vendedor: <strong>${(this.info?.fee_basis_points ?? 500) / 100}%</strong></div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>
        ${gate}
        <div class="tabs" role="tablist">
          ${tabButton("buy", "Comprar")}${tabButton("sell", "Anunciar")}${tabButton("mine", `Meus anúncios (${this.mine.filter((l) => l.status === "active").length})`)}${tabButton("history", "Histórico")}
        </div>
        <p class="market-message" role="status" ${this.message ? "" : "hidden"}>${escapeHtml(this.message)}</p>
        <div class="market-section">${body}</div>
      </section>`;
    this.bind();
  }

  private bind(): void {
    const { token } = this.options;
    const $$ = <T extends HTMLElement>(selector: string) =>
      this.root.querySelectorAll<T>(selector);

    this.root.querySelector(".btn-close")?.addEventListener("click", () => this.options.onClose());
    $$("[data-tab]").forEach((button) =>
      button.addEventListener("click", () => {
        this.tab = button.dataset.tab as Tab;
        this.message = "";
        this.render();
        void this.load();
      }),
    );
    $$("[data-filter]").forEach((button) =>
      button.addEventListener("click", () => {
        this.filter = button.dataset.filter ?? "";
        void this.load();
      }),
    );

    $$("[data-buy]").forEach((button) =>
      button.addEventListener("click", () => {
        const quantity = Number(button.dataset.qty);
        void this.run(async () => {
          const trade = await exchangeService.buy(button.dataset.buy ?? "", quantity, token);
          this.balance = trade.balance;
          return `Comprou ${trade.quantity}× ${trade.item_name} por ${trade.gross} AGC.`;
        });
      }),
    );
    $$("[data-cancel]").forEach((button) =>
      button.addEventListener("click", () =>
        void this.run(async () => {
          const listing = await exchangeService.cancel(button.dataset.cancel ?? "", token);
          return `Anúncio cancelado: ${listing.quantity_remaining}× ${listing.item_name} devolvidos.`;
        }),
      ),
    );

    // Formulário de anúncio
    $$("[data-pick]").forEach((button) =>
      button.addEventListener("click", () => {
        this.selectItem(button.dataset.pick ?? "");
        this.render();
      }),
    );
    const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
    const stock = () => this.inventory.find((item) => item.item_id === this.itemId)?.quantity ?? 1;
    $$("[data-stepqty]").forEach((button) =>
      button.addEventListener("click", () => {
        this.quantity = clamp(this.quantity + Number(button.dataset.stepqty), 1, stock());
        this.render();
      }),
    );
    $$("[data-setqty]").forEach((button) =>
      button.addEventListener("click", () => {
        this.quantity = clamp(Number(button.dataset.setqty), 1, stock());
        this.render();
      }),
    );
    $$("[data-stepprice]").forEach((button) =>
      button.addEventListener("click", () => {
        const bounds = this.priceOf(this.itemId);
        this.price = clamp(
          this.price + Number(button.dataset.stepprice),
          bounds?.minimum ?? 1,
          bounds?.maximum ?? 1_000_000,
        );
        this.render();
      }),
    );
    $$("[data-setprice]").forEach((button) =>
      button.addEventListener("click", () => {
        this.price = Number(button.dataset.setprice);
        this.render();
      }),
    );
    this.root.querySelector('[data-action="create"]')?.addEventListener("click", () =>
      void this.run(async () => {
        const created = await exchangeService.create(
          { item_id: this.itemId, quantity: this.quantity, unit_price: this.price },
          token,
        );
        this.tab = "mine";
        return `Anunciou ${created.quantity_initial}× ${created.item_name} a ${created.unit_price} AGC cada.`;
      }),
    );
  }
}
