import Phaser from "phaser";

import { buildWorld } from "@/game/world/build-world";
import { createWorldTextures } from "@/game/world/textures";
import { gameState } from "@/state/game-state";
import { session } from "@/state/session";
import { Hud } from "@/ui/hud";

import { CameraController } from "./farm/camera-controller";
import { FarmController } from "./farm/farm-controller";
import { FarmPanels } from "./farm/farm-panels";
import { FarmState } from "./farm/farm-state";
import { PlotRenderer } from "./farm/plot-renderer";
import { bindWorldInteractions } from "./farm/world-interactions";

const SYNC_INTERVAL_MS = 4000;

/**
 * Cena principal da ilha: apenas monta os módulos e cuida do ciclo de vida.
 *
 * Visão aérea ("God-view"), 100% pelo mouse. Cada responsabilidade vive em
 * `game/scenes/farm/`:
 * - `CameraController`: pan, zoom e filtro de eventos do mundo.
 * - `PlotRenderer`: o que cresce em cada talhão.
 * - `FarmController`: dados, plantio, colheita e sincronização com o servidor.
 * - `FarmPanels`: painéis (plantio, casa, mercado, construções, talentos).
 * - `bindWorldInteractions`: hover e cliques nos objetos do mundo.
 */
export class FarmScene extends Phaser.Scene {
  private hud?: Hud;
  private panels?: FarmPanels;
  private controller?: FarmController;
  private syncTimer?: Phaser.Time.TimerEvent;

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

    createWorldTextures(this);
    const world = buildWorld(this);

    const state = new FarmState();
    state.token = token;

    const camera = new CameraController(this, () => this.panels?.modals.isOpen ?? false);
    const hud = new Hud(character.name, {
      onZoomIn: () => camera.zoomIn(),
      onZoomOut: () => camera.zoomOut(),
      onResetView: () => camera.resetView(),
      onHarvestAll: () => void this.controller?.harvestAll(),
    });
    this.hud = hud;

    const renderer = new PlotRenderer(this, state);
    const controller = new FarmController({
      state,
      hud,
      renderer,
      onPropertyChange: (property) => {
        hud.setFarm(property.name, property.plot_count);
        world.setPlotCount(property.plot_count);
      },
    });
    this.controller = controller;

    const panels = new FarmPanels({ scene: this, state, hud, controller });
    this.panels = panels;
    hud.setMenu(panels.menuItems());

    bindWorldInteractions({
      interactables: world.interactables,
      camera,
      hud,
      state,
      controller,
      panels,
    });

    void controller.initialize(character);

    // Sincronização periódica da produção em segundo plano.
    this.syncTimer = this.time.addEvent({
      delay: SYNC_INTERVAL_MS,
      loop: true,
      callback: () => void controller.syncPlantings(),
    });

    this.events.once(Phaser.Scenes.Events.SHUTDOWN, this.handleShutdown, this);
  }

  private handleShutdown(): void {
    this.syncTimer?.remove();
    this.panels?.closeAll();
    this.hud?.destroy();
    this.hud = undefined;
    this.panels = undefined;
    this.controller = undefined;
  }
}
