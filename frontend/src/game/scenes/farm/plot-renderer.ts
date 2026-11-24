import Phaser from "phaser";

import { PLOTS } from "@/game/world/map";
import type { Planting } from "@/services/property-service";

import { isPlantingReady, type FarmState } from "./farm-state";

/** Desenha o que cresce em cada talhão: broto, planta, planta madura e selo de colheita. */
export class PlotRenderer {
  private readonly cropSprites = new Map<number, Phaser.GameObjects.Image>();
  private readonly badgeSprites = new Map<number, Phaser.GameObjects.Image>();

  constructor(
    private readonly scene: Phaser.Scene,
    private readonly state: FarmState,
  ) {}

  renderAll(): void {
    for (let index = 0; index < PLOTS.length; index += 1) {
      this.render(index, this.state.plantings.get(index));
    }
  }

  render(plotIndex: number, planting?: Planting): void {
    const plot = PLOTS[plotIndex];
    if (!plot) {
      return;
    }

    this.cropSprites.get(plotIndex)?.destroy();
    this.cropSprites.delete(plotIndex);
    this.badgeSprites.get(plotIndex)?.destroy();
    this.badgeSprites.delete(plotIndex);

    if (!planting || planting.status === "exhausted") {
      return;
    }

    const ready = isPlantingReady(planting);
    const image = this.scene.add
      .image(plot.x, plot.y, this.textureFor(planting, ready))
      .setOrigin(0, 0)
      .setDepth(plot.y + 4);
    this.cropSprites.set(plotIndex, image);

    if (ready) {
      const badge = this.scene.add
        .image(plot.x + 32, plot.y - 4, "ready-badge")
        .setOrigin(0.5, 0.5)
        .setDepth(plot.y + 20);
      this.scene.tweens.add({
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

  /** Texto dourado que sobe e some (recompensa da colheita). */
  floatingReward(x: number, y: number, text: string): void {
    const label = this.scene.add
      .text(x, y, text, {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "14px",
        color: "#f7e27e",
        stroke: "#261608",
        strokeThickness: 3,
      })
      .setOrigin(0.5, 0.5)
      .setDepth(y + 100);

    this.scene.tweens.add({
      targets: label,
      y: y - 36,
      alpha: 0,
      duration: 1800,
      ease: "Cubic.easeOut",
      onComplete: () => label.destroy(),
    });
  }

  private textureFor(planting: Planting, ready: boolean): string {
    if (ready) {
      const mature = `crop-mature-${planting.crop_id}`;
      return this.scene.textures.exists(mature) ? mature : "crop-growing";
    }
    // Depois da metade do tempo, a planta já aparece crescida.
    const total = this.state.crops.find((crop) => crop.id === planting.crop_id)?.grow_seconds ?? 300;
    return (planting.seconds_until_ready ?? 0) < total * 0.5 ? "crop-growing" : "crop-sprout";
  }
}
