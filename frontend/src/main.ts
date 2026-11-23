import Phaser from "phaser";

import { GAME_CONFIG } from "@/config/game";
import "@/styles/main.css";
import "@/styles/talents.css";

const game = new Phaser.Game(GAME_CONFIG);

// Apenas em desenvolvimento: facilita depuração e testes de integração no
// console do navegador. O bloco é removido da build de produção.
if (import.meta.env.DEV) {
  (window as Window & { __AGRO_GAME__?: Phaser.Game }).__AGRO_GAME__ = game;
}

// Evita instâncias duplicadas do jogo durante o hot reload do Vite.
if (import.meta.hot) {
  import.meta.hot.dispose(() => {
    game.destroy(true);
  });
}
