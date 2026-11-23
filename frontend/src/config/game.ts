import Phaser from "phaser";

import { BootScene } from "@/game/scenes/BootScene";
import { FarmScene } from "@/game/scenes/FarmScene";

/**
 * Configuração central do Phaser.
 *
 * A cena inicial apenas valida a integração com a API; as cenas de login,
 * inventário, plantio e produção serão adicionadas nas próximas etapas.
 */
export const GAME_CONFIG: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: "game-container",
  backgroundColor: "#0f1a12",
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: 1280,
    height: 720,
  },
  render: {
    antialias: true,
    roundPixels: true,
  },
  scene: [BootScene, FarmScene],
};
