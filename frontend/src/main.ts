import Phaser from "phaser";

import { GAME_CONFIG } from "@/config/game";
import "@/styles/main.css";

const game = new Phaser.Game(GAME_CONFIG);

// Evita instâncias duplicadas do jogo durante o hot reload do Vite.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    game.destroy(true);
  });
}
