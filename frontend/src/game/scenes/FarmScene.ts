import Phaser from "phaser";

/**
 * Cena placeholder da fazenda.
 *
 * O objetivo nesta etapa é validar o boot do Phaser e o layout responsivo.
 * A grade abaixo representa os talhões; interação, plantio e inventário serão
 * conectados à API nas próximas etapas.
 */
export class FarmScene extends Phaser.Scene {
  private readonly columns = 4;
  private readonly rows = 3;

  constructor() {
    super("FarmScene");
  }

  create(): void {
    this.cameras.main.setBackgroundColor("#142418");
    this.draw();

    this.scale.on(Phaser.Scale.Events.RESIZE, this.draw, this);
    this.events.once(Phaser.Scenes.Events.SHUTDOWN, () => {
      this.scale.off(Phaser.Scale.Events.RESIZE, this.draw, this);
    });
  }

  private draw(): void {
    this.children.removeAll(true);

    const { width, height } = this.scale;
    const titleY = Math.max(48, height * 0.1);

    this.add
      .text(width / 2, titleY, "Fazenda Boa Vista", {
        fontFamily: "Georgia, 'Times New Roman', serif",
        fontSize: "34px",
        color: "#f4e4b5",
      })
      .setOrigin(0.5);

    this.add
      .text(width / 2, titleY + 40, "Estrutura inicial — talhões aguardando cultivo", {
        fontFamily: "ui-monospace, Consolas, monospace",
        fontSize: "14px",
        color: "#9fb8a2",
      })
      .setOrigin(0.5);

    this.drawPlots(width, height);

    this.add
      .text(
        width / 2,
        height - 32,
        "Login, inventário e produção offline serão conectados à API nas próximas etapas.",
        {
          fontFamily: "ui-monospace, Consolas, monospace",
          fontSize: "12px",
          color: "#5f7a63",
          align: "center",
          wordWrap: { width: Math.max(320, width - 64) },
        },
      )
      .setOrigin(0.5);
  }

  private drawPlots(width: number, height: number): void {
    const gap = 14;
    const availableWidth = Math.max(280, Math.min(width - 96, 760));
    const availableHeight = Math.max(200, height - 300);
    const plotSize = Math.max(
      56,
      Math.min(
        120,
        (availableWidth - gap * (this.columns - 1)) / this.columns,
        (availableHeight - gap * (this.rows - 1)) / this.rows,
      ),
    );

    const gridWidth = this.columns * plotSize + (this.columns - 1) * gap;
    const gridHeight = this.rows * plotSize + (this.rows - 1) * gap;
    const startX = (width - gridWidth) / 2;
    const startY = Math.max(170, (height - gridHeight) / 2 + 24);

    const graphics = this.add.graphics();

    for (let row = 0; row < this.rows; row += 1) {
      for (let column = 0; column < this.columns; column += 1) {
        const x = startX + column * (plotSize + gap);
        const y = startY + row * (plotSize + gap);

        graphics.fillStyle(0x3a2a1a, 1);
        graphics.fillRoundedRect(x, y, plotSize, plotSize, 10);
        graphics.lineStyle(2, 0x7a5a36, 1);
        graphics.strokeRoundedRect(x, y, plotSize, plotSize, 10);

        this.add
          .text(x + plotSize / 2, y + plotSize / 2, `${row * this.columns + column + 1}`, {
            fontFamily: "ui-monospace, Consolas, monospace",
            fontSize: "14px",
            color: "#8d6f48",
          })
          .setOrigin(0.5);
      }
    }
  }
}
