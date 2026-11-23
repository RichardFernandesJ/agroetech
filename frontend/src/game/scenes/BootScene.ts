import Phaser from "phaser";

import { env } from "@/config/env";
import { ApiError } from "@/services/api-client";
import { characterService, type Character } from "@/services/character-service";
import { systemService } from "@/services/system-service";
import { gameState } from "@/state/game-state";
import { session } from "@/state/session";
import { AuthPanel } from "@/ui/auth-panel";
import { CharacterPanel } from "@/ui/character-panel";

interface OverlayPanel {
  destroy(): void;
}

/**
 * Cena de entrada.
 *
 * Orquestra a sessão: verifica o servidor, restaura o token, pede login ou
 * criação de personagem e só então entrega o controle para o mundo.
 */
export class BootScene extends Phaser.Scene {
  private panel: OverlayPanel | null = null;
  private statusLabel?: Phaser.GameObjects.Text;
  private retryTimer?: Phaser.Time.TimerEvent;
  private booting = false;

  constructor() {
    super("BootScene");
  }

  create(): void {
    const { width, height } = this.scale;

    this.add
      .text(width / 2, height / 2 - 58, env.gameTitle, {
        fontFamily: "Georgia, 'Times New Roman', serif",
        fontSize: "46px",
        color: "#f4e4b5",
      })
      .setOrigin(0.5);

    this.add
      .text(width / 2, height / 2 - 18, "Um RPG de fazenda para navegador", {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "14px",
        color: "#9fb8a2",
      })
      .setOrigin(0.5);

    this.statusLabel = this.add
      .text(width / 2, height / 2 + 28, "Preparando a fazenda...", {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "15px",
        color: "#d9b96a",
        align: "center",
        wordWrap: { width: Math.max(280, width - 64) },
      })
      .setOrigin(0.5);

    this.add
      .text(width / 2, height - 36, `API: ${env.apiUrl}`, {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "12px",
        color: "#5f7a63",
      })
      .setOrigin(0.5);

    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this.retryTimer?.remove();
      this.panel?.destroy();
      this.panel = null;
    });

    void this.bootstrap();
  }

  private async bootstrap(): Promise<void> {
    if (this.booting) {
      return;
    }
    this.booting = true;
    this.retryTimer?.remove();
    this.retryTimer = undefined;

    this.setStatus("Verificando servidor...");
    try {
      await systemService.health();
    } catch {
      this.setStatus("Servidor indisponível. Tentando novamente em alguns segundos...");
      this.scheduleRetry();
      this.booting = false;
      return;
    }

    this.setStatus("Restaurando sessão...");
    const restored = await session.restore();
    this.booting = false;

    if (restored) {
      await this.loadCharacter();
    } else {
      this.showAuth();
    }
  }

  private async loadCharacter(): Promise<void> {
    const token = session.accessToken;
    if (!token) {
      this.showAuth();
      return;
    }

    this.setStatus("Carregando personagem...");
    try {
      const character = await characterService.getMine(token);
      this.enterFarm(character);
    } catch (error) {
      if (error instanceof ApiError && error.status === 404) {
        this.showCharacterCreation();
        return;
      }
      if (error instanceof ApiError && error.status === 401) {
        session.clear();
        this.showAuth();
        return;
      }
      this.setStatus("Não foi possível carregar o personagem. Tentando novamente...");
      this.scheduleRetry();
    }
  }

  private showAuth(): void {
    this.setStatus("Entre para começar a cultivar.");
    this.panel?.destroy();
    this.panel = new AuthPanel({
      onAuthenticated: () => {
        this.panel?.destroy();
        this.panel = null;
        void this.loadCharacter();
      },
    });
  }

  private showCharacterCreation(): void {
    this.setStatus("Crie seu personagem para entrar no mundo.");
    this.panel?.destroy();
    this.panel = new CharacterPanel({
      onCreated: (character) => {
        this.panel?.destroy();
        this.panel = null;
        this.enterFarm(character);
      },
    });
  }

  private enterFarm(character: Character): void {
    gameState.setCharacter(character);
    this.panel?.destroy();
    this.panel = null;
    this.scene.start("FarmScene");
  }

  private scheduleRetry(): void {
    if (this.retryTimer) {
      return;
    }
    this.retryTimer = this.time.addEvent({
      delay: 5000,
      callback: () => {
        this.retryTimer = undefined;
        void this.bootstrap();
      },
    });
  }

  private setStatus(message: string): void {
    if (this.statusLabel?.active) {
      this.statusLabel.setText(message);
    }
  }
}
