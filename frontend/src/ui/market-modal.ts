import { ApiError } from "@/services/api-client";
import {
  economyService,
  type LedgerEntry,
  type MarketOffer,
  type MarketOffers,
} from "@/services/economy-service";
import { propertyService, type InventoryItem } from "@/services/property-service";

type Tab = "buy" | "sell" | "ledger";

export interface MarketModalOptions {
  propertyId: string;
  token: string;
  balance: number;
  /** Chamado após cada operação para o mundo/HUD atualizar saldo e inventário. */
  onChange: (balance: number, items: InventoryItem[]) => void;
  onClose: () => void;
}

const KIND_LABELS: Record<string, string> = {
  initial_grant: "Crédito inicial",
  seed_purchase: "Compra de sementes",
  crop_sale: "Venda de safra",
};

function escapeHtml(value: string): string {
  return value.replace(/[&<>"']/g, (char) => `&#${char.charCodeAt(0)};`);
}

/**
 * Entreposto da ilha. Toda a interação é por cliques: cada linha oferece
 * botões ×1, ×5 e Máx/Tudo, sem digitação de quantidades.
 */
export class MarketModal {
  private readonly root: HTMLDivElement;
  private tab: Tab = "buy";
  private balance: number;
  private items: InventoryItem[] = [];
  private offers: MarketOffers | null = null;
  private ledger: LedgerEntry[] = [];
  private message = "";
  private busy = false;
  private destroyed = false;

  constructor(private readonly options: MarketModalOptions) {
    this.balance = options.balance;
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
      const [offers, inventory, wallet] = await Promise.all([
        economyService.getOffers(this.options.token),
        propertyService.getInventory(this.options.propertyId, this.options.token),
        economyService.getWallet(this.options.token),
      ]);
      this.offers = offers;
      this.items = inventory.items;
      this.balance = wallet.balance;
    } catch (error) {
      this.message = this.describe(error);
    }
    this.render();
  }

  private async loadLedger(): Promise<void> {
    try {
      this.ledger = (await economyService.getLedger(this.options.token, 30)).entries;
    } catch (error) {
      this.message = this.describe(error);
    }
    this.render();
  }

  private quantityOf(itemId: string): number {
    return this.items.find((item) => item.item_id === itemId)?.quantity ?? 0;
  }

  private describe(error: unknown): string {
    return error instanceof ApiError ? error.message : "Não foi possível falar com o servidor.";
  }

  private async trade(mode: "buy" | "sell", itemId: string, quantity: number): Promise<void> {
    if (this.busy || quantity < 1) {
      return;
    }
    this.busy = true;
    this.message = "";
    this.render();

    try {
      const { propertyId, token } = this.options;
      const result =
        mode === "buy"
          ? await economyService.buy(propertyId, { item_id: itemId, quantity }, token)
          : await economyService.sell(propertyId, { item_id: itemId, quantity }, token);

      this.balance = result.balance;
      this.items = (await propertyService.getInventory(propertyId, token)).items;
      this.message =
        mode === "buy"
          ? `Comprou ${result.quantity}× ${result.item_name} por ${-result.amount} AGC.`
          : `Vendeu ${result.quantity}× ${result.item_name}: +${result.amount} AGC (taxa ${result.fee}).`;
      this.options.onChange(this.balance, this.items);
    } catch (error) {
      this.message = this.describe(error);
    } finally {
      this.busy = false;
      if (!this.destroyed) {
        this.render();
      }
    }
  }

  private maxBuy(offer: MarketOffer): number {
    if (!offer.buy_price) {
      return 0;
    }
    return Math.min(999, Math.floor(this.balance / offer.buy_price));
  }

  private renderBuy(): string {
    const rows = (this.offers?.offers ?? []).filter((offer) => offer.buy_price !== null);
    if (rows.length === 0) {
      return `<p class="empty-list">Carregando ofertas...</p>`;
    }
    return `<div class="trade-list">${rows
      .map((offer) => {
        const max = this.maxBuy(offer);
        const disabled = this.busy ? "disabled" : "";
        const btn = (qty: number, label: string) =>
          `<button type="button" class="btn-trade" data-mode="buy" data-item="${offer.item_id}" data-qty="${qty}" ${
            this.busy || qty < 1 || qty > max ? "disabled" : ""
          }>${label}</button>`;
        return `
          <div class="trade-row">
            <div class="trade-info">
              <span class="inventory-icon">🌱</span>
              <div><strong>${escapeHtml(offer.name)}</strong>
              <small>Em estoque: ${this.quantityOf(offer.item_id)}</small></div>
            </div>
            <span class="trade-price">${offer.buy_price} AGC</span>
            <div class="trade-actions" ${disabled ? 'aria-busy="true"' : ""}>
              ${btn(1, "×1")}${btn(5, "×5")}${btn(max, `Máx (${max})`)}
            </div>
          </div>`;
      })
      .join("")}</div>`;
  }

  private renderSell(): string {
    const fee = (this.offers?.fee_basis_points ?? 0) / 100;
    const rows = (this.offers?.offers ?? []).filter(
      (offer) => offer.sell_price !== null && this.quantityOf(offer.item_id) > 0,
    );
    if (rows.length === 0) {
      return `<p class="empty-list">Nenhuma safra para vender. Colha seus talhões primeiro!</p>`;
    }
    return `
      <p class="trade-note">Taxa do entreposto: ${fee}% sobre cada venda.</p>
      <div class="trade-list">${rows
        .map((offer) => {
          const owned = this.quantityOf(offer.item_id);
          const btn = (qty: number, label: string) =>
            `<button type="button" class="btn-trade" data-mode="sell" data-item="${offer.item_id}" data-qty="${qty}" ${
              this.busy || qty < 1 || qty > owned ? "disabled" : ""
            }>${label}</button>`;
          return `
            <div class="trade-row">
              <div class="trade-info">
                <span class="inventory-icon">🌾</span>
                <div><strong>${escapeHtml(offer.name)}</strong><small>Você tem: ${owned}</small></div>
              </div>
              <span class="trade-price">${offer.sell_price} AGC</span>
              <div class="trade-actions">${btn(1, "×1")}${btn(5, "×5")}${btn(owned, `Tudo (${owned})`)}</div>
            </div>`;
        })
        .join("")}</div>`;
  }

  private renderLedger(): string {
    if (this.ledger.length === 0) {
      return `<p class="empty-list">Nenhuma movimentação ainda.</p>`;
    }
    return `<div class="trade-list">${this.ledger
      .map((entry) => {
        const label = KIND_LABELS[entry.kind] ?? entry.kind;
        const detail = entry.item_name ? ` · ${entry.quantity}× ${escapeHtml(entry.item_name)}` : "";
        const sign = entry.amount >= 0 ? "+" : "";
        return `
          <div class="trade-row ledger-row">
            <div class="trade-info"><div><strong>${label}${detail}</strong>
            <small>${new Date(entry.created_at).toLocaleString("pt-BR")}${
              entry.fee ? ` · taxa ${entry.fee}` : ""
            }</small></div></div>
            <span class="trade-price ${entry.amount >= 0 ? "gain" : "loss"}">${sign}${entry.amount} AGC</span>
            <span class="ledger-balance">Saldo ${entry.balance_after}</span>
          </div>`;
      })
      .join("")}</div>`;
  }

  private render(): void {
    if (this.destroyed) {
      return;
    }
    const body =
      this.tab === "buy" ? this.renderBuy() : this.tab === "sell" ? this.renderSell() : this.renderLedger();
    const tabBtn = (tab: Tab, label: string) =>
      `<button type="button" class="tab ${this.tab === tab ? "active" : ""}" data-tab="${tab}" role="tab" aria-selected="${
        this.tab === tab
      }">${label}</button>`;

    this.root.innerHTML = `
      <section class="panel market-panel" role="dialog" aria-modal="true" aria-labelledby="market-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Entreposto da Ilha</p>
            <h2 id="market-title">Mercado</h2>
          </div>
          <div class="market-balance" aria-label="Saldo">🪙 <strong>${this.balance}</strong> AGC</div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>

        <div class="tabs" role="tablist">
          ${tabBtn("buy", "Comprar sementes")}${tabBtn("sell", "Vender safras")}${tabBtn("ledger", "Extrato")}
        </div>

        <p class="market-message" role="status" ${this.message ? "" : "hidden"}>${escapeHtml(this.message)}</p>
        <div class="market-section">${body}</div>
      </section>
    `;

    this.root.querySelector(".btn-close")?.addEventListener("click", () => this.options.onClose());

    this.root.querySelectorAll<HTMLButtonElement>(".tab").forEach((button) => {
      button.addEventListener("click", () => {
        this.tab = button.dataset.tab as Tab;
        this.message = "";
        this.render();
        if (this.tab === "ledger") {
          void this.loadLedger();
        }
      });
    });

    this.root.querySelectorAll<HTMLButtonElement>(".btn-trade").forEach((button) => {
      button.addEventListener("click", () => {
        void this.trade(
          button.dataset.mode as "buy" | "sell",
          button.dataset.item ?? "",
          Number(button.dataset.qty),
        );
      });
    });
  }
}
