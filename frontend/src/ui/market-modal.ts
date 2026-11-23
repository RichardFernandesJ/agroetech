import type { InventoryItem } from "@/services/property-service";

export interface MarketModalOptions {
  items: InventoryItem[];
  onClose: () => void;
}

export class MarketModal {
  private readonly root: HTMLDivElement;

  constructor(private readonly options: MarketModalOptions) {
    this.root = document.createElement("div");
    this.root.className = "overlay";
    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);
    this.render();
  }

  destroy(): void {
    this.root.remove();
  }

  private render(): void {
    const { items } = this.options;

    const seeds = items.filter((i) => i.category === "seed" && i.quantity > 0);
    const products = items.filter((i) => i.category === "crop" && i.quantity > 0);

    const renderList = (list: InventoryItem[], emptyMsg: string) => {
      if (list.length === 0) {
        return `<p class="empty-list">${emptyMsg}</p>`;
      }
      return `
        <div class="inventory-grid">
          ${list
            .map(
              (item) => `
            <div class="inventory-card">
              <div class="inventory-card-top">
                <span class="inventory-icon">${item.category === "seed" ? "🌱" : "🌾"}</span>
                <strong class="inventory-card-title">${item.name}</strong>
              </div>
              <p class="inventory-card-desc">${item.description}</p>
              <div class="inventory-card-qty">
                Quantidade: <strong>${item.quantity}</strong>
              </div>
            </div>
          `,
            )
            .join("")}
        </div>
      `;
    };

    this.root.innerHTML = `
      <section class="panel market-panel" role="dialog" aria-modal="true" aria-labelledby="market-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Entreposto da Ilha</p>
            <h2 id="market-title">Mercado e Armazém</h2>
          </div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>

        <div class="market-section">
          <h3>Sementes para Plantio</h3>
          ${renderList(seeds, "Nenhuma semente em estoque no momento.")}
        </div>

        <div class="market-section">
          <h3>Colheitas e Produtos</h3>
          ${renderList(products, "Nenhuma safra colhida armazenada.")}
        </div>

        <div class="panel-actions">
          <button type="button" class="btn btn-primary btn-close-modal">Fechar</button>
        </div>
      </section>
    `;

    this.root.querySelector(".btn-close")?.addEventListener("click", () => {
      this.options.onClose();
    });

    this.root.querySelector(".btn-close-modal")?.addEventListener("click", () => {
      this.options.onClose();
    });

    this.root.addEventListener("click", (e) => {
      if (e.target === this.root) {
        this.options.onClose();
      }
    });
  }
}
