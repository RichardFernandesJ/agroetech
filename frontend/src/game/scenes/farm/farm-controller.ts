import { PLOTS } from "@/game/world/map";
import type { Character } from "@/services/character-service";
import { economyService } from "@/services/economy-service";
import { progressService } from "@/services/progress-service";
import { propertyService, type Planting, type Property } from "@/services/property-service";
import type { Hud } from "@/ui/hud";

import { isPlantingReady, type FarmState } from "./farm-state";
import type { PlotRenderer } from "./plot-renderer";

export interface FarmControllerDeps {
  state: FarmState;
  hud: Hud;
  renderer: PlotRenderer;
  /** O mundo reage a mudanças da fazenda (nome, talhões liberados). */
  onPropertyChange: (property: Property) => void;
}

/**
 * Regras de uso da fazenda no cliente: carrega dados, planta, colhe e mantém
 * HUD e talhões em sincronia com o servidor. O servidor continua sendo a
 * autoridade; aqui só se envia a intenção e se mostra o resultado.
 */
export class FarmController {
  constructor(private readonly deps: FarmControllerDeps) {}

  private get state(): FarmState {
    return this.deps.state;
  }

  private get hud(): Hud {
    return this.deps.hud;
  }

  // ---------------------------------------------------------------- carga
  async initialize(character: Character): Promise<void> {
    const token = this.state.token;
    if (!token) {
      return;
    }

    try {
      const [property, crops] = await Promise.all([
        propertyService.get(character.property_id, token),
        propertyService.getCrops(),
      ]);
      this.state.crops = crops;
      this.setProperty(property);

      await Promise.all([
        this.syncPlantings(),
        this.refreshInventory(),
        this.refreshBalance(),
        this.refreshProgress(false),
      ]);
    } catch {
      this.hud.setFarm("Fazenda da Ilha", 6);
    }
  }

  setProperty(property: Property): void {
    this.state.property = property;
    this.deps.onPropertyChange(property);
  }

  /** Chamado após uma melhoria da Casa da Fazenda. */
  updatePlotCount(plotCount: number): void {
    if (this.state.property) {
      this.setProperty({ ...this.state.property, plot_count: plotCount });
    }
  }

  // ------------------------------------------------------- sincronização
  async syncPlantings(): Promise<void> {
    const { property, token } = this.state;
    if (!property || !token) {
      return;
    }

    try {
      const plantings = await propertyService.getPlantings(property.id, token);
      this.state.plantings.clear();
      let ready = 0;
      for (const planting of plantings) {
        this.state.plantings.set(planting.plot_index, planting);
        if (isPlantingReady(planting)) {
          ready += 1;
        }
      }
      this.deps.renderer.renderAll();
      this.hud.setReadyHarvestCount(ready);
    } catch {
      // Falhas temporárias de sincronização são ignoradas.
    }
  }

  async refreshInventory(): Promise<void> {
    const { property, token } = this.state;
    if (!property || !token) {
      return;
    }
    try {
      this.state.inventory = (await propertyService.getInventory(property.id, token)).items;
    } catch {
      // Mantém o último inventário conhecido.
    }
  }

  async refreshBalance(): Promise<void> {
    if (!this.state.token) {
      return;
    }
    try {
      this.state.balance = (await economyService.getWallet(this.state.token)).balance;
      this.hud.setBalance(this.state.balance);
    } catch {
      // Mantém o último saldo conhecido.
    }
  }

  /** Atualiza nível/XP no HUD; com ``announce`` avisa quando o nível sobe. */
  async refreshProgress(announce: boolean): Promise<void> {
    if (!this.state.token) {
      return;
    }
    try {
      const progress = await progressService.get(this.state.token);
      const leveledUp = announce && this.state.level > 0 && progress.level > this.state.level;
      this.state.level = progress.level;
      this.hud.setProgress(progress);
      if (leveledUp) {
        this.hud.toast(`⭐ Você alcançou o nível ${progress.level}!`);
      }
    } catch {
      // Mantém o último progresso conhecido.
    }
  }

  /** Saldo e inventário vindos de um painel (mercado, construções). */
  applyBalance(balance: number): void {
    this.state.balance = balance;
    this.hud.setBalance(balance);
  }

  // ---------------------------------------------------------------- ações
  async plant(plotIndex: number, cropId: string): Promise<void> {
    const { property, token } = this.state;
    if (!property || !token) {
      return;
    }

    try {
      const planting = await propertyService.plant(
        property.id,
        { plot_index: plotIndex, crop_id: cropId },
        token,
      );
      this.state.plantings.set(plotIndex, planting);
      this.deps.renderer.render(plotIndex, planting);
      this.hud.toast(`🌱 Plantou ${planting.crop_name} no Talhão ${plotIndex + 1}!`);
      await this.refreshInventory();
      await this.refreshProgress(true);
    } catch {
      this.hud.toast("Não foi possível plantar. Verifique se possui sementes disponíveis.");
    }
  }

  async harvest(planting: Planting): Promise<void> {
    if (!this.state.token) {
      return;
    }

    try {
      const outcome = await propertyService.harvest(planting.id, this.state.token);
      this.state.plantings.delete(planting.plot_index);
      this.deps.renderer.render(planting.plot_index, undefined);

      const plot = PLOTS[planting.plot_index];
      if (plot) {
        this.deps.renderer.floatingReward(
          plot.x + 32,
          plot.y + 16,
          `+${outcome.product_quantity} ${outcome.product_name}`,
        );
      }
      this.hud.toast(
        `🌾 Colheita realizada! +${outcome.product_quantity} ${outcome.product_name} (+${outcome.seed_quantity} ${outcome.seed_name}) · +${outcome.xp_gained} XP`,
      );

      await this.syncPlantings();
      await this.refreshInventory();
      await this.refreshProgress(true);
    } catch {
      this.hud.toast("Falha ao colher. Tente novamente.");
    }
  }

  async harvestAll(): Promise<void> {
    const { property, token } = this.state;
    if (!property || !token) {
      return;
    }

    try {
      const outcome = await propertyService.harvestAll(property.id, token);
      if (outcome.harvests.length === 0) {
        this.hud.toast("Nenhum talhão pronto para colheita no momento.");
        return;
      }

      const summary = Object.entries(outcome.products)
        .map(([name, quantity]) => `+${quantity} ${name}`)
        .join(", ");
      this.hud.toast(
        `🎉 Safra colhida com sucesso (${outcome.harvests.length} talhões): ${summary}!`,
      );

      await this.syncPlantings();
      await this.refreshInventory();
      await this.refreshProgress(true);
    } catch {
      this.hud.toast("Erro ao colher todos os talhões.");
    }
  }
}
