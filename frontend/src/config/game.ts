import Phaser from "phaser";

import { BootScene } from "@/game/scenes/BootScene";
import { FarmScene } from "@/game/scenes/FarmScene";

/**
 * Configuração central do Phaser.
 *
 * `pixelArt` desliga a suavização para manter os tiles nítidos. O mundo usa
 * Arcade Physics apenas para colisão e movimento; nenhuma regra de jogo roda
 * no cliente.
 */
export const GAME_CONFIG: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: "game-container",
  backgroundColor: "#0f1a12",
  pixelArt: true,
  scale: {
    mode: Phaser.Scale.RESIZE,
    autoCenter: Phaser.Scale.CENTER_BOTH,
    width: 1280,
    height: 720,
  },
  physics: {
    default: "arcade",
    arcade: {
      gravity: { x: 0, y: 0 },
      debug: false,
    },
  },
  render: {
    roundPixels: true,
  },
  scene: [BootScene, FarmScene],
};
