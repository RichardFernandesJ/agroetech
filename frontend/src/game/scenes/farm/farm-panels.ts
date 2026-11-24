import Phaser from "phaser";

import { gameState } from "@/state/game-state";
import { session } from "@/state/session";
import { AnimalsModal } from "@/ui/animals-modal";
import { BuildingsModal } from "@/ui/buildings-modal";
import { HouseModal } from "@/ui/house-modal";
import type { Hud, HudMenuItem } from "@/ui/hud";
import { MarketModal } from "@/ui/market-modal";
import { ModalManager } from "@/ui/modal-manager";
import { PlantingModal } from "@/ui/planting-modal";
import { TalentModal } from "@/ui/talent-modal";

import type { FarmController } from "./farm-controller";
import type { FarmState } from "./farm-state";

export interface FarmPanelsDeps {
  scene: Phaser.Scene;
  state: FarmState;
  hud: Hud;
  controller: FarmController;
}

/**
 * Painéis DOM da fazenda (plantio, casa, mercado, construções, talentos).
 * Um sistema novo entra com um método `open...` aqui e um item em `menuItems()`.
 */
export class FarmPanels {
  readonly modals = new ModalManager();

  constructor(private readonly deps: FarmPanelsDeps) {}

  /** Itens do menu principal do HUD. */
  menuItems(): HudMenuItem[] {
    return [
      {
        id: "market",
        label: "🏪 Mercado",
        title: "Comprar sementes e vender safras",
        onClick: () => this.openMarket(),
      },
      {
        id: "buildings",
        label: "🏗️ Construções",
        title: "Melhorar a casa, o poço e outras construções",
        onClick: () => this.openBuildings(),
      },
      {
        id: "animals",
        label: "🐔 Animais",
        title: "Criar, alimentar e coletar produtos dos animais",
        onClick: () => this.openAnimals(),
      },
      {
        id: "talents",
        label: "🌳 Talentos",
        title: "Árvore de talentos e builds",
        onClick: () => this.openTalents(),
      },
    ];
  }

  closeAll(): void {
    this.modals.close();
  }

  openPlanting(plotIndex: number): void {
    const { state, controller } = this.deps;
    const seeds = state.inventory.filter((item) => item.category === "seed");

    this.modals.open(
      (close) =>
        new PlantingModal({
          plotIndex,
          seeds,
          crops: state.crops,
          onSelectCrop: (cropId) => {
            close();
            void controller.plant(plotIndex, cropId);
          },
          onClose: close,
        }),
    );
  }

  openHouse(): void {
    const character = gameState.currentCharacter;
    const property = this.deps.state.property;
    if (!property || !character) {
      return;
    }

    this.modals.open(
      (close) =>
        new HouseModal({
          property,
          farmerName: character.name,
          onOpenBuildings: () => this.openBuildings("sede"),
          onLogout: () => {
            session.clear();
            this.deps.scene.scene.start("BootScene");
          },
          onClose: close,
        }),
    );
  }

  openMarket(): void {
    const { state, controller } = this.deps;
    if (!state.property || !state.token) {
      return;
    }

    const propertyId = state.property.id;
    const token = state.token;
    this.modals.open(
      (close) =>
        new MarketModal({
          propertyId,
          token,
          balance: state.balance,
          onChange: (balance, items) => {
            state.inventory = items;
            controller.applyBalance(balance);
          },
          onClose: close,
        }),
    );
  }

  openBuildings(focus?: string): void {
    const { state, controller } = this.deps;
    if (!state.property || !state.token) {
      return;
    }

    const propertyId = state.property.id;
    const token = state.token;
    this.modals.open(
      (close) =>
        new BuildingsModal({
          propertyId,
          token,
          focus,
          onChange: (result) => {
            controller.applyBalance(result.balance);
            controller.updatePlotCount(result.plot_count);
          },
          onClose: close,
        }),
    );
  }

  openAnimals(): void {
    const { state, controller } = this.deps;
    if (!state.property || !state.token) {
      return;
    }

    const propertyId = state.property.id;
    const token = state.token;
    this.modals.open(
      (close) =>
        new AnimalsModal({
          propertyId,
          token,
          onChange: () => {
            void controller.refreshInventory();
            void controller.refreshBalance();
            void controller.refreshProgress(true);
          },
          onOpenBuildings: () => this.openBuildings(),
          onClose: close,
        }),
    );
  }

  openTalents(): void {
    const { state, controller } = this.deps;
    const token = state.token;
    if (!token) {
      return;
    }

    this.modals.open(
      (close) =>
        new TalentModal({
          token,
          onWalletChange: () => void controller.refreshBalance(),
          onClose: close,
        }),
    );
  }
}
