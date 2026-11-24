import Phaser from "phaser";

import type { WorldObjectInteractable } from "@/game/world/build-world";
import type { Hud } from "@/ui/hud";

import type { CameraController } from "./camera-controller";
import type { FarmController } from "./farm-controller";
import type { FarmPanels } from "./farm-panels";
import { formatRemaining, isPlantingReady, type FarmState } from "./farm-state";

export interface WorldInteractionDeps {
  interactables: WorldObjectInteractable[];
  camera: CameraController;
  hud: Hud;
  state: FarmState;
  controller: FarmController;
  panels: FarmPanels;
}

/**
 * Liga o mouse aos objetos do mundo: destaque e dica ao passar, ação ao clicar.
 * Para uma estrutura nova basta mapear o `id` dela em `handleClick`.
 */
export function bindWorldInteractions(deps: WorldInteractionDeps): void {
  const { camera, hud } = deps;

  for (const item of deps.interactables) {
    const object = item.gameObject;

    object.on("pointerover", (pointer: Phaser.Input.Pointer) => {
      if (!camera.isWorldPointer(pointer)) {
        return;
      }
      if ("setTint" in object && typeof object.setTint === "function") {
        object.setTint(0xfff5d0);
      }
      hud.setPrompt(hoverPrompt(deps, item));
    });

    object.on("pointerout", () => {
      if ("clearTint" in object && typeof object.clearTint === "function") {
        object.clearTint();
      }
      hud.setPrompt(null);
    });

    object.on("pointerup", (pointer: Phaser.Input.Pointer) => {
      if (camera.dragged || !camera.isWorldPointer(pointer)) {
        return;
      }
      handleClick(deps, item);
    });
  }
}

function plotIndexOf(item: WorldObjectInteractable): number | null {
  return item.id.startsWith("plot-") ? Number.parseInt(item.id.replace("plot-", ""), 10) : null;
}

function hoverPrompt(deps: WorldInteractionDeps, item: WorldObjectInteractable): string {
  const plotIndex = plotIndexOf(item);
  if (plotIndex === null) {
    return item.label;
  }

  const planting = deps.state.plantings.get(plotIndex);
  const label = `Talhão ${plotIndex + 1}`;
  if (!planting) {
    return `${label} (Vazio · Clique para plantar)`;
  }
  if (isPlantingReady(planting)) {
    return `${label}: ${planting.crop_name} (PRONTO! Clique para colher)`;
  }
  return `${label}: ${planting.crop_name} (Crescendo · ${formatRemaining(planting.seconds_until_ready ?? 0)})`;
}

function handleClick(deps: WorldInteractionDeps, item: WorldObjectInteractable): void {
  const { hud, panels } = deps;

  const plotIndex = plotIndexOf(item);
  if (plotIndex !== null) {
    handlePlotClick(deps, plotIndex);
    return;
  }

  switch (item.id) {
    case "house":
      panels.openHouse();
      return;
    case "market":
      panels.openMarket();
      return;
    case "barn":
      panels.openAnimals();
      return;
    case "well":
      panels.openBuildings("poco");
      return;
    case "boat":
      hud.toast("⛵ Barco no píer: transporte de mercadorias e comércio marítimo entre ilhas na Fase 6.");
      return;
    default:
      hud.toast(item.message);
  }
}

function handlePlotClick(deps: WorldInteractionDeps, plotIndex: number): void {
  const planting = deps.state.plantings.get(plotIndex);

  if (planting && isPlantingReady(planting)) {
    void deps.controller.harvest(planting);
    return;
  }

  if (planting) {
    const time = formatRemaining(planting.seconds_until_ready ?? 0, true);
    deps.hud.toast(
      `🌱 ${planting.crop_name} crescendo no Talhão ${plotIndex + 1}. Ficará pronto em cerca de ${time}.`,
    );
    return;
  }

  deps.panels.openPlanting(plotIndex);
}
