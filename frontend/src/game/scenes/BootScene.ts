import Phaser from "phaser";

import { env } from "@/config/env";
import { systemService } from "@/services/system-service";

export class BootScene extends Phaser.Scene {
  constructor() {
    super("BootScene");
  }

  create(): void {
    const { width, height } = this.scale;

    this.add
      .text(width / 2, height / 2 - 36, env.gameTitle, {
        fontFamily: "Georgia, 'Times New Roman', serif",
        fontSize: "46px",
        color: "#f4e4b5",
      })
      .setOrigin(0.5);

    const statusLabel = this.add
      .text(width / 2, height / 2 + 24, "Preparando a fazenda...", {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "16px",
        color: "#9fb8a2",
      })
      .setOrigin(0.5);

    this.add
      .text(width / 2, height - 36, `API: ${env.apiUrl}`, {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "12px",
        color: "#5f7a63",
      })
      .setOrigin(0.5);

    void this.checkBackend(statusLabel);

    this.time.delayedCall(1600, () => {
      this.scene.start("FarmScene");
    });
  }

  private async checkBackend(label: Phaser.GameObjects.Text): Promise<void> {
    try {
      const health = await systemService.health();
      if (label.active) {
        label.setText(`Servidor: ${health.status}`);
      }
    } catch {
      if (label.active) {
        label.setText("Servidor indisponível — verifique o Docker");
      }
    }
  }
}
