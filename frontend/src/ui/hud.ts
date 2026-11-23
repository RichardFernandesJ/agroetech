/**
 * HUD do mundo (visão da ilha).
 *
 * Usa DOM em vez de texto no canvas: fica nítido em qualquer resolução, é
 * acessível e não sofre com o zoom da câmera.
 */

export interface HudActions {
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  onResetView?: () => void;
  onHarvestAll?: () => void;
  onOpenMarket?: () => void;
}

export class Hud {
  private readonly root: HTMLDivElement;
  private readonly nameElement: HTMLHeadingElement;
  private readonly farmElement: HTMLParagraphElement;
  private readonly balanceElement: HTMLParagraphElement;
  private readonly promptElement: HTMLDivElement;
  private readonly promptLabel: HTMLSpanElement;
  private readonly toastElement: HTMLDivElement;
  private readonly harvestAllBtn: HTMLButtonElement;

  private promptValue: string | null = null;
  private toastTimer: number | undefined;

  constructor(characterName: string, actions?: HudActions) {
    this.root = document.createElement("div");
    this.root.className = "hud";

    const card = document.createElement("section");
    card.className = "hud-card";

    const eyebrow = document.createElement("p");
    eyebrow.className = "hud-eyebrow";
    eyebrow.textContent = "Fazenda na Ilha";

    this.nameElement = document.createElement("h1");
    this.nameElement.className = "hud-name";
    this.nameElement.textContent = characterName;

    this.farmElement = document.createElement("p");
    this.farmElement.className = "hud-farm";
    this.farmElement.textContent = "Carregando fazenda...";

    // Saldo clicável: atalho para o mercado (jogo 100% por mouse).
    this.balanceElement = document.createElement("p");
    this.balanceElement.className = "hud-balance";
    this.balanceElement.setAttribute("role", "button");
    this.balanceElement.tabIndex = 0;
    this.balanceElement.title = "Abrir o mercado";
    this.balanceElement.textContent = "🪙 — AGC";
    this.balanceElement.addEventListener("click", () => actions?.onOpenMarket?.());

    card.append(eyebrow, this.nameElement, this.farmElement, this.balanceElement);

    const hint = document.createElement("p");
    hint.className = "hud-hint";
    hint.textContent = "Arraste para mover · Roda do mouse para zoom · Clique para cultivar";

    // Controles de zoom e câmera na tela
    const cameraControls = document.createElement("div");
    cameraControls.className = "hud-camera-controls";

    // Botão de colheita geral (aparece quando há colheitas prontas)
    this.harvestAllBtn = document.createElement("button");
    this.harvestAllBtn.type = "button";
    this.harvestAllBtn.className = "hud-btn hud-btn-harvest";
    this.harvestAllBtn.title = "Colher todos os talhões prontos";
    this.harvestAllBtn.textContent = "🌾 Colher Tudo";
    this.harvestAllBtn.hidden = true;
    this.harvestAllBtn.addEventListener("click", () => actions?.onHarvestAll?.());

    const zoomInBtn = document.createElement("button");
    zoomInBtn.type = "button";
    zoomInBtn.className = "hud-btn hud-btn-zoom";
    zoomInBtn.title = "Aproximar zoom (+)";
    zoomInBtn.textContent = "+";
    zoomInBtn.addEventListener("click", () => actions?.onZoomIn?.());

    const zoomOutBtn = document.createElement("button");
    zoomOutBtn.type = "button";
    zoomOutBtn.className = "hud-btn hud-btn-zoom";
    zoomOutBtn.title = "Afastar zoom (-)";
    zoomOutBtn.textContent = "−";
    zoomOutBtn.addEventListener("click", () => actions?.onZoomOut?.());

    const resetViewBtn = document.createElement("button");
    resetViewBtn.type = "button";
    resetViewBtn.className = "hud-btn hud-btn-reset";
    resetViewBtn.title = "Centralizar na Ilha";
    resetViewBtn.textContent = "⌂ Centralizar";
    resetViewBtn.addEventListener("click", () => actions?.onResetView?.());

    cameraControls.append(this.harvestAllBtn, zoomInBtn, zoomOutBtn, resetViewBtn);

    // Prompt de interação
    this.promptElement = document.createElement("div");
    this.promptElement.className = "hud-prompt";
    this.promptElement.hidden = true;

    const icon = document.createElement("span");
    icon.className = "hud-prompt-icon";
    icon.textContent = "👆";

    this.promptLabel = document.createElement("span");

    this.promptElement.append(icon, this.promptLabel);

    this.toastElement = document.createElement("div");
    this.toastElement.className = "hud-toast";
    this.toastElement.setAttribute("role", "status");
    this.toastElement.hidden = true;

    this.root.append(card, hint, cameraControls, this.promptElement, this.toastElement);

    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);
  }

  setFarm(name: string, plotCount: number): void {
    this.farmElement.textContent = `${name} · ${plotCount} talhões`;
  }

  setBalance(balance: number): void {
    this.balanceElement.textContent = `🪙 ${balance.toLocaleString("pt-BR")} AGC`;
  }

  setReadyHarvestCount(readyCount: number): void {
    if (readyCount > 0) {
      this.harvestAllBtn.hidden = false;
      this.harvestAllBtn.textContent = `🌾 Colher Tudo (${readyCount})`;
    } else {
      this.harvestAllBtn.hidden = true;
    }
  }

  setPrompt(label: string | null): void {
    if (label === this.promptValue) {
      return;
    }
    this.promptValue = label;

    if (label === null) {
      this.promptElement.hidden = true;
      return;
    }
    this.promptLabel.textContent = `Clique: ${label}`;
    this.promptElement.hidden = false;
  }

  toast(message: string): void {
    if (this.toastTimer !== undefined) {
      window.clearTimeout(this.toastTimer);
    }

    this.toastElement.textContent = message;
    this.toastElement.hidden = false;
    this.toastElement.classList.add("visible");

    this.toastTimer = window.setTimeout(() => {
      this.toastElement.classList.remove("visible");
      this.toastElement.hidden = true;
      this.toastTimer = undefined;
    }, 3600);
  }

  destroy(): void {
    if (this.toastTimer !== undefined) {
      window.clearTimeout(this.toastTimer);
    }
    this.root.remove();
  }
}
