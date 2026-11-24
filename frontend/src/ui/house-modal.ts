import type { Property } from "@/services/property-service";

export interface HouseModalOptions {
  property: Property;
  farmerName: string;
  onLogout: () => void;
  onOpenBuildings: () => void;
  onClose: () => void;
}

export class HouseModal {
  private readonly root: HTMLDivElement;

  constructor(private readonly options: HouseModalOptions) {
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
    const { property, farmerName } = this.options;

    const formattedDate = new Date(property.created_at).toLocaleDateString("pt-BR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });

    this.root.innerHTML = `
      <section class="panel house-panel" role="dialog" aria-modal="true" aria-labelledby="house-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Sede da Fazenda</p>
            <h2 id="house-title">${property.name}</h2>
          </div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>

        <div class="farm-details">
          <div class="detail-row">
            <span class="detail-label">Fazendeiro(a):</span>
            <strong class="detail-value">${farmerName}</strong>
          </div>
          <div class="detail-row">
            <span class="detail-label">Talhões disponíveis:</span>
            <strong class="detail-value">${property.plot_count} talhões</strong>
          </div>
          <div class="detail-row">
            <span class="detail-label">Área da Ilha:</span>
            <strong class="detail-value">${property.area_hectares} hectares</strong>
          </div>
          <div class="detail-row">
            <span class="detail-label">Fundada em:</span>
            <span class="detail-value">${formattedDate}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">Produção Offline:</span>
            <span class="detail-value badge-active">Ativa (até 12h)</span>
          </div>
        </div>

        <div class="house-actions">
          <button type="button" class="btn btn-buildings">🏗️ Construções</button>
          <button type="button" class="btn btn-secondary btn-logout">Desconectar da Conta</button>
          <button type="button" class="btn btn-primary btn-close-modal">Continuar Cultivando</button>
        </div>
      </section>
    `;

    this.root.querySelector(".btn-close")?.addEventListener("click", () => {
      this.options.onClose();
    });

    this.root.querySelector(".btn-close-modal")?.addEventListener("click", () => {
      this.options.onClose();
    });

    this.root.querySelector(".btn-buildings")?.addEventListener("click", () => {
      this.options.onOpenBuildings();
    });

    this.root.querySelector(".btn-logout")?.addEventListener("click", () => {
      this.options.onLogout();
    });

    this.root.addEventListener("click", (e) => {
      if (e.target === this.root) {
        this.options.onClose();
      }
    });
  }
}
