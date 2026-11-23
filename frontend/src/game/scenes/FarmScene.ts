import Phaser from "phaser";

import { buildWorld, type WorldObjectInteractable } from "@/game/world/build-world";
import {
  ISLAND_CENTER,
  PLOTS,
  WORLD_HEIGHT,
  WORLD_WIDTH,
} from "@/game/world/map";
import { createWorldTextures } from "@/game/world/textures";
import { type Character } from "@/services/character-service";
import {
  propertyService,
  type CropCatalogItem,
  type InventoryItem,
  type Planting,
  type Property,
} from "@/services/property-service";
import { gameState } from "@/state/game-state";
import { session } from "@/state/session";
import { HouseModal } from "@/ui/house-modal";
import { Hud } from "@/ui/hud";
import { MarketModal } from "@/ui/market-modal";
import { economyService } from "@/services/economy-service";
import { PlantingModal } from "@/ui/planting-modal";

const MIN_ZOOM = 0.45;
const MAX_ZOOM = 2.2;
const DRAG_THRESHOLD = 6;
const SYNC_INTERVAL_MS = 4000;

/**
 * Cena principal da ilha da fazenda.
 *
 * Visão aérea / "God-view" com controle 100% pelo mouse:
 * - Arrastar para navegar livremente pela ilha.
 * - Roda do mouse (wheel) para zoom in e zoom out suave com ponto focal no cursor.
 * - Ciclo completo de agricultura por clique direto nos talhões (plantio, crescimento e colheita).
 * - Acesso às estruturas (Casa, Mercado, Poço) com painéis dedicados.
 */
export class FarmScene extends Phaser.Scene {
  private hud?: Hud;
  private property?: Property;
  private token?: string;
  private catalogCrops: CropCatalogItem[] = [];
  private plantingsByPlot = new Map<number, Planting>();
  private inventoryItems: InventoryItem[] = [];
  private balance = 0;

  // Sprites visuais sobre os talhões
  private cropSprites = new Map<number, Phaser.GameObjects.Image>();
  private badgeSprites = new Map<number, Phaser.GameObjects.Image>();

  private activeModal: { destroy: () => void } | null = null;
  private syncTimer?: Phaser.Time.TimerEvent;

  // Estado de navegação e pan
  private isDragging = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private cameraStartScrollX = 0;
  private cameraStartScrollY = 0;
  private hasDragged = false;

  constructor() {
    super("FarmScene");
  }

  create(): void {
    const character = gameState.currentCharacter;
    const token = session.accessToken;
    if (!character || !token) {
      this.scene.start("BootScene");
      return;
    }

    this.token = token;

    createWorldTextures(this);

    const world = buildWorld(this);

    // Configuração de câmera livre
    const camera = this.cameras.main;
    camera.setBackgroundColor("#14354f");
    camera.setBounds(-240, -200, WORLD_WIDTH + 480, WORLD_HEIGHT + 400);
    camera.setRoundPixels(true);

    const initialZoom = this.calculateOptimalZoom();
    camera.setZoom(initialZoom);
    camera.centerOn(ISLAND_CENTER.x, ISLAND_CENTER.y);

    this.setupCameraControls();
    this.setupWorldInteractions(world.interactables);

    this.hud = new Hud(character.name, {
      onZoomIn: () => this.zoomIn(),
      onZoomOut: () => this.zoomOut(),
      onResetView: () => this.resetView(),
      onHarvestAll: () => this.harvestAllPlots(),
      onOpenMarket: () => this.openMarketModal(),
    });

    void this.initializeGameData(character);

    // Sincronização periódica da produção em segundo plano
    this.syncTimer = this.time.addEvent({
      delay: SYNC_INTERVAL_MS,
      loop: true,
      callback: () => this.syncPlantings(),
    });

    this.scale.on(Phaser.Scale.Events.RESIZE, this.handleResize, this);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, this.handleShutdown, this);
  }

  private calculateOptimalZoom(): number {
    const { width, height } = this.scale;
    const fitZoom = Math.min(width / (WORLD_WIDTH + 80), height / (WORLD_HEIGHT + 60));
    return Phaser.Math.Clamp(Math.round(fitZoom * 100) / 100, 0.75, 1.25);
  }

  private setupCameraControls(): void {
    const camera = this.cameras.main;

    // Zoom suave pela roda do mouse com foco na posição do ponteiro
    this.input.on(
      "wheel",
      (
        pointer: Phaser.Input.Pointer,
        _gameObjects: unknown[],
        _deltaX: number,
        deltaY: number,
      ) => {
        const zoomDelta = deltaY < 0 ? 0.12 : -0.12;
        this.applyZoomAt(camera.zoom + zoomDelta, pointer.x, pointer.y);
      },
    );

    // Pan (arrastar a tela)
    this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      this.isDragging = true;
      this.hasDragged = false;
      this.dragStartX = pointer.x;
      this.dragStartY = pointer.y;
      this.cameraStartScrollX = camera.scrollX;
      this.cameraStartScrollY = camera.scrollY;
    });

    this.input.on("pointermove", (pointer: Phaser.Input.Pointer) => {
      if (!this.isDragging || !pointer.isDown) {
        return;
      }

      const dx = pointer.x - this.dragStartX;
      const dy = pointer.y - this.dragStartY;

      if (!this.hasDragged && Math.hypot(dx, dy) > DRAG_THRESHOLD) {
        this.hasDragged = true;
      }

      if (this.hasDragged) {
        camera.scrollX = this.cameraStartScrollX - dx / camera.zoom;
        camera.scrollY = this.cameraStartScrollY - dy / camera.zoom;
      }
    });

    this.input.on("pointerup", () => {
      this.isDragging = false;
    });
  }

  private applyZoomAt(targetZoom: number, screenX: number, screenY: number): void {
    const camera = this.cameras.main;
    const clampedZoom = Phaser.Math.Clamp(targetZoom, MIN_ZOOM, MAX_ZOOM);
    if (Math.abs(clampedZoom - camera.zoom) < 0.001) {
      return;
    }

    const worldPointBefore = camera.getWorldPoint(screenX, screenY);
    camera.setZoom(clampedZoom);
    const worldPointAfter = camera.getWorldPoint(screenX, screenY);

    camera.scrollX += worldPointBefore.x - worldPointAfter.x;
    camera.scrollY += worldPointBefore.y - worldPointAfter.y;
  }

  public zoomIn(): void {
    const camera = this.cameras.main;
    this.applyZoomAt(camera.zoom * 1.2, this.scale.width / 2, this.scale.height / 2);
  }

  public zoomOut(): void {
    const camera = this.cameras.main;
    this.applyZoomAt(camera.zoom / 1.2, this.scale.width / 2, this.scale.height / 2);
  }

  public resetView(): void {
    const camera = this.cameras.main;
    const optimalZoom = this.calculateOptimalZoom();
    this.tweens.add({
      targets: camera,
      zoom: optimalZoom,
      scrollX: ISLAND_CENTER.x - (this.scale.width / 2) / optimalZoom,
      scrollY: ISLAND_CENTER.y - (this.scale.height / 2) / optimalZoom,
      duration: 350,
      ease: "Cubic.easeOut",
    });
  }

  private setupWorldInteractions(interactables: WorldObjectInteractable[]): void {
    for (const item of interactables) {
      const obj = item.gameObject;

      obj.on("pointerover", () => {
        if ("setTint" in obj && typeof obj.setTint === "function") {
          obj.setTint(0xfff5d0);
        }
        this.updateInteractiveHoverPrompt(item);
      });

      obj.on("pointerout", () => {
        if ("clearTint" in obj && typeof obj.clearTint === "function") {
          obj.clearTint();
        }
        this.hud?.setPrompt(null);
      });

      obj.on("pointerup", () => {
        if (this.hasDragged) {
          return;
        }
        this.handleInteractiveClick(item);
      });
    }
  }

  private updateInteractiveHoverPrompt(item: WorldObjectInteractable): void {
    if (item.id.startsWith("plot-")) {
      const plotIndex = Number.parseInt(item.id.replace("plot-", ""), 10);
      const planting = this.plantingsByPlot.get(plotIndex);
      if (!planting) {
        this.hud?.setPrompt(`Talhão ${plotIndex + 1} (Vazio · Clique para plantar)`);
      } else if (planting.status === "ready" || planting.seconds_until_ready === 0) {
        this.hud?.setPrompt(`Talhão ${plotIndex + 1}: ${planting.crop_name} (PRONTO! Clique para colher)`);
      } else {
        const sec = planting.seconds_until_ready ?? 0;
        const timeStr = sec > 60 ? `${Math.ceil(sec / 60)} min` : `${sec}s`;
        this.hud?.setPrompt(`Talhão ${plotIndex + 1}: ${planting.crop_name} (Crescendo · ${timeStr})`);
      }
      return;
    }

    this.hud?.setPrompt(item.label);
  }

  private handleInteractiveClick(item: WorldObjectInteractable): void {
    if (item.id.startsWith("plot-")) {
      const plotIndex = Number.parseInt(item.id.replace("plot-", ""), 10);
      this.handlePlotClick(plotIndex);
      return;
    }

    if (item.id === "house") {
      this.openHouseModal();
      return;
    }

    if (item.id === "market") {
      this.openMarketModal();
      return;
    }

    if (item.id === "well") {
      this.hud?.toast("💧 Poço artesiano da Ilha: água cristalina garantindo a irrigação permanente das suas culturas.");
      return;
    }

    if (item.id === "boat") {
      this.hud?.toast("⛵ Barco no píer: transporte de mercadorias e comércio marítimo entre ilhas na Fase 6.");
      return;
    }

    this.hud?.toast(item.message);
  }

  private handlePlotClick(plotIndex: number): void {
    const planting = this.plantingsByPlot.get(plotIndex);

    // Caso 1: Talhão pronto para colheita
    if (planting && (planting.status === "ready" || planting.seconds_until_ready === 0)) {
      void this.harvestPlot(planting);
      return;
    }

    // Caso 2: Talhão em crescimento
    if (planting) {
      const sec = planting.seconds_until_ready ?? 0;
      const timeStr = sec > 60 ? `${Math.ceil(sec / 60)} minutos` : `${sec} segundos`;
      this.hud?.toast(`🌱 ${planting.crop_name} crescendo no Talhão ${plotIndex + 1}. Ficará pronto em cerca de ${timeStr}.`);
      return;
    }

    // Caso 3: Talhão vazio -> abrir seletor de plantio
    this.openPlantingModal(plotIndex);
  }

  private openPlantingModal(plotIndex: number): void {
    this.activeModal?.destroy();

    const seeds = this.inventoryItems.filter((i) => i.category === "seed");

    this.activeModal = new PlantingModal({
      plotIndex,
      seeds,
      crops: this.catalogCrops,
      onSelectCrop: (cropId) => {
        this.activeModal?.destroy();
        this.activeModal = null;
        void this.executePlant(plotIndex, cropId);
      },
      onClose: () => {
        this.activeModal?.destroy();
        this.activeModal = null;
      },
    });
  }

  private openHouseModal(): void {
    const character = gameState.currentCharacter;
    if (!this.property || !character) {
      return;
    }

    this.activeModal?.destroy();
    this.activeModal = new HouseModal({
      property: this.property,
      farmerName: character.name,
      onLogout: () => {
        session.clear();
        this.scene.start("BootScene");
      },
      onClose: () => {
        this.activeModal?.destroy();
        this.activeModal = null;
      },
    });
  }

  private openMarketModal(): void {
    if (!this.property || !this.token) {
      return;
    }

    this.activeModal?.destroy();
    this.activeModal = new MarketModal({
      propertyId: this.property.id,
      token: this.token,
      balance: this.balance,
      onChange: (balance, items) => {
        this.balance = balance;
        this.inventoryItems = items;
        this.hud?.setBalance(balance);
      },
      onClose: () => {
        this.activeModal?.destroy();
        this.activeModal = null;
      },
    });
  }

  private async executePlant(plotIndex: number, cropId: string): Promise<void> {
    if (!this.property || !this.token) {
      return;
    }

    try {
      const newPlanting = await propertyService.plant(
        this.property.id,
        { plot_index: plotIndex, crop_id: cropId },
        this.token,
      );

      this.plantingsByPlot.set(plotIndex, newPlanting);
      this.renderPlotVisual(plotIndex, newPlanting);
      this.hud?.toast(`🌱 Plantou ${newPlanting.crop_name} no Talhão ${plotIndex + 1}!`);

      // Atualiza o inventário local
      await this.refreshInventory();
    } catch {
      this.hud?.toast("Não foi possível plantar. Verifique se possui sementes disponíveis.");
    }
  }

  private async harvestPlot(planting: Planting): Promise<void> {
    if (!this.token) {
      return;
    }

    try {
      const outcome = await propertyService.harvest(planting.id, this.token);
      this.plantingsByPlot.delete(planting.plot_index);
      this.renderPlotVisual(planting.plot_index, undefined);

      // Animação de colheita flutuante
      const plot = PLOTS[planting.plot_index];
      if (plot) {
        this.spawnFloatingReward(plot.x + 32, plot.y + 16, `+${outcome.product_quantity} ${outcome.product_name}`);
      }

      this.hud?.toast(
        `🌾 Colheita realizada! +${outcome.product_quantity} ${outcome.product_name} (+${outcome.seed_quantity} ${outcome.seed_name})`,
      );

      await this.syncPlantings();
      await this.refreshInventory();
    } catch {
      this.hud?.toast("Falha ao colher. Tente novamente.");
    }
  }

  private async harvestAllPlots(): Promise<void> {
    if (!this.property || !this.token) {
      return;
    }

    try {
      const outcome = await propertyService.harvestAll(this.property.id, this.token);
      const totalHarvests = outcome.harvests.length;

      if (totalHarvests === 0) {
        this.hud?.toast("Nenhum talhão pronto para colheita no momento.");
        return;
      }

      const productsSummary = Object.entries(outcome.products)
        .map(([name, qty]) => `+${qty} ${name}`)
        .join(", ");

      this.hud?.toast(`🎉 Safra colhida com sucesso (${totalHarvests} talhões): ${productsSummary}!`);

      await this.syncPlantings();
      await this.refreshInventory();
    } catch {
      this.hud?.toast("Erro ao colher todos os talhões.");
    }
  }

  private spawnFloatingReward(x: number, y: number, text: string): void {
    const label = this.add
      .text(x, y, text, {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "14px",
        color: "#f7e27e",
        stroke: "#261608",
        strokeThickness: 3,
      })
      .setOrigin(0.5, 0.5)
      .setDepth(y + 100);

    this.tweens.add({
      targets: label,
      y: y - 36,
      alpha: 0,
      duration: 1800,
      ease: "Cubic.easeOut",
      onComplete: () => {
        label.destroy();
      },
    });
  }

  private renderPlotVisual(plotIndex: number, planting?: Planting): void {
    const plot = PLOTS[plotIndex];
    if (!plot) {
      return;
    }

    // Limpa sprites anteriores desse talhão
    this.cropSprites.get(plotIndex)?.destroy();
    this.cropSprites.delete(plotIndex);

    this.badgeSprites.get(plotIndex)?.destroy();
    this.badgeSprites.delete(plotIndex);

    if (!planting || planting.status === "exhausted") {
      return;
    }

    const isReady = planting.status === "ready" || planting.seconds_until_ready === 0;

    let textureKey = "crop-sprout";
    if (isReady) {
      const matureKey = `crop-mature-${planting.crop_id}`;
      textureKey = this.textures.exists(matureKey) ? matureKey : "crop-growing";
    } else {
      // Se já passou mais da metade do tempo, usa a textura de planta crescendo
      const cropInfo = this.catalogCrops.find((c) => c.id === planting.crop_id);
      const totalSeconds = cropInfo?.grow_seconds ?? 300;
      const remaining = planting.seconds_until_ready ?? 0;
      if (remaining < totalSeconds * 0.5) {
        textureKey = "crop-growing";
      }
    }

    const cropImage = this.add
      .image(plot.x, plot.y, textureKey)
      .setOrigin(0, 0)
      .setDepth(plot.y + 4);

    this.cropSprites.set(plotIndex, cropImage);

    // Se estiver pronto para colher, adiciona indicador flutuante pulsante
    if (isReady) {
      const badge = this.add
        .image(plot.x + 32, plot.y - 4, "ready-badge")
        .setOrigin(0.5, 0.5)
        .setDepth(plot.y + 20);

      this.tweens.add({
        targets: badge,
        y: plot.y - 10,
        yoyo: true,
        repeat: -1,
        duration: 700,
        ease: "Sine.easeInOut",
      });

      this.badgeSprites.set(plotIndex, badge);
    }
  }

  private async initializeGameData(character: Character): Promise<void> {
    if (!this.token) {
      return;
    }

    try {
      const [property, crops] = await Promise.all([
        propertyService.get(character.property_id, this.token),
        propertyService.getCrops(),
      ]);

      this.property = property;
      this.catalogCrops = crops;
      this.hud?.setFarm(property.name, property.plot_count);

      await Promise.all([this.syncPlantings(), this.refreshInventory(), this.refreshBalance()]);
    } catch {
      this.hud?.setFarm("Fazenda da Ilha", 6);
    }
  }

  private async syncPlantings(): Promise<void> {
    if (!this.property || !this.token) {
      return;
    }

    try {
      const plantings = await propertyService.getPlantings(this.property.id, this.token);
      this.plantingsByPlot.clear();

      let readyCount = 0;
      for (const p of plantings) {
        this.plantingsByPlot.set(p.plot_index, p);
        if (p.status === "ready" || p.seconds_until_ready === 0) {
          readyCount += 1;
        }
      }

      // Atualiza os visuais de todos os talhões
      for (let i = 0; i < PLOTS.length; i += 1) {
        this.renderPlotVisual(i, this.plantingsByPlot.get(i));
      }

      this.hud?.setReadyHarvestCount(readyCount);
    } catch {
      // Ignora falhas temporárias de sincronização
    }
  }

  private async refreshBalance(): Promise<void> {
    if (!this.token) {
      return;
    }

    try {
      this.balance = (await economyService.getWallet(this.token)).balance;
      this.hud?.setBalance(this.balance);
    } catch {
      // Mantém o último saldo conhecido
    }
  }

  private async refreshInventory(): Promise<void> {
    if (!this.property || !this.token) {
      return;
    }

    try {
      const inv = await propertyService.getInventory(this.property.id, this.token);
      this.inventoryItems = inv.items;
    } catch {
      // Ignora falha de inventário
    }
  }

  private handleResize(): void {
    // Atualização responsiva
  }

  private handleShutdown(): void {
    this.syncTimer?.remove();
    this.activeModal?.destroy();
    this.scale.off(Phaser.Scale.Events.RESIZE, this.handleResize, this);
    this.hud?.destroy();
    this.hud = undefined;
  }
}
