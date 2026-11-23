import type { CropCatalogItem, InventoryItem } from "@/services/property-service";

export interface PlantingModalOptions {
  plotIndex: number;
  seeds: InventoryItem[];
  crops: CropCatalogItem[];
  onSelectCrop: (cropId: string) => void;
  onClose: () => void;
}

export class PlantingModal {
  private readonly root: HTMLDivElement;

  constructor(private readonly options: PlantingModalOptions) {
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
    const { plotIndex, seeds, crops } = this.options;

    // Filtra as culturas para as quais o jogador possui sementes (> 0)
    const available = crops
      .map((crop) => {
        const seedItem = seeds.find((s) => s.item_id === crop.seed_item);
        const quantity = seedItem?.quantity ?? 0;
        return { crop, quantity };
      })
      .filter((item) => item.quantity > 0);

    const formatMinutes = (seconds: number): string => {
      const min = Math.round(seconds / 60);
      return `${min} min`;
    };

    let contentHtml = "";
    if (available.length === 0) {
      contentHtml = `
        <div class="empty-state">
          <p>Você não possui sementes no inventário para cultivar neste talhão.</p>
          <p class="empty-hint">Novas sementes retornam a cada colheita ou no mercado da ilha.</p>
        </div>
      `;
    } else {
      contentHtml = `
        <ul class="crop-list">
          ${available
            .map(
              ({ crop, quantity }) => `
            <li class="crop-item">
              <div class="crop-info">
                <div class="crop-name-row">
                  <span class="crop-icon">🌱</span>
                  <strong class="crop-name">${crop.name}</strong>
                  <span class="crop-qty">x${quantity} sementes</span>
                </div>
                <p class="crop-meta">Tempo de colheita: ${formatMinutes(crop.grow_seconds)} · Rendimento: ${crop.yield_quantity} produtos</p>
              </div>
              <button type="button" class="btn btn-plant" data-crop-id="${crop.id}">
                Plantar
              </button>
            </li>
          `,
            )
            .join("")}
        </ul>
      `;
    }

    this.root.innerHTML = `
      <section class="panel planting-panel" role="dialog" aria-modal="true" aria-labelledby="planting-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Talhão ${plotIndex + 1}</p>
            <h2 id="planting-title">Escolha o que plantar</h2>
          </div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>

        ${contentHtml}

        <div class="panel-actions">
          <button type="button" class="btn btn-secondary btn-cancel">Cancelar</button>
        </div>
      </section>
    `;

    // Eventos
    this.root.querySelector(".btn-close")?.addEventListener("click", () => {
      this.options.onClose();
    });

    this.root.querySelector(".btn-cancel")?.addEventListener("click", () => {
      this.options.onClose();
    });

    this.root.querySelectorAll(".btn-plant").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        const cropId = (e.currentTarget as HTMLButtonElement).dataset.cropId;
        if (cropId) {
          this.options.onSelectCrop(cropId);
        }
      });
    });

    // Fechar ao clicar fora do painel
    this.root.addEventListener("click", (e) => {
      if (e.target === this.root) {
        this.options.onClose();
      }
    });
  }
}
