export type TouchDirection = "up" | "down" | "left" | "right";

/**
 * Controles de toque.
 *
 * Um direcional fixo é mais previsível que joystick virtual em telas pequenas.
 * Os botões só aparecem em dispositivos com ponteiro grosseiro (CSS).
 */
export class TouchControls {
  private readonly root: HTMLDivElement;
  private readonly pressed = new Set<TouchDirection>();

  constructor(onAction: () => void) {
    this.root = document.createElement("div");
    this.root.className = "touch-controls";

    const pad = document.createElement("div");
    pad.className = "touch-pad";

    const directions: Array<{ direction: TouchDirection; label: string; area: string }> = [
      { direction: "up", label: "▲", area: "up" },
      { direction: "left", label: "◀", area: "left" },
      { direction: "down", label: "▼", area: "down" },
      { direction: "right", label: "▶", area: "right" },
    ];

    for (const item of directions) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `touch-button touch-${item.area}`;
      button.textContent = item.label;
      button.setAttribute("aria-label", `Mover para ${item.area}`);
      button.addEventListener("pointerdown", (event) => {
        event.preventDefault();
        this.pressed.add(item.direction);
      });
      const release = (): void => {
        this.pressed.delete(item.direction);
      };
      button.addEventListener("pointerup", release);
      button.addEventListener("pointerleave", release);
      button.addEventListener("pointercancel", release);
      button.addEventListener("contextmenu", (event) => event.preventDefault());
      pad.append(button);
    }

    const action = document.createElement("button");
    action.type = "button";
    action.className = "touch-button touch-action";
    action.textContent = "E";
    action.setAttribute("aria-label", "Interagir");
    action.addEventListener("click", (event) => {
      event.preventDefault();
      onAction();
    });

    this.root.append(pad, action);

    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);

    window.addEventListener("blur", this.releaseAll);
  }

  vector(): { x: number; y: number } {
    const x = (this.pressed.has("right") ? 1 : 0) - (this.pressed.has("left") ? 1 : 0);
    const y = (this.pressed.has("down") ? 1 : 0) - (this.pressed.has("up") ? 1 : 0);
    return { x, y };
  }

  destroy(): void {
    window.removeEventListener("blur", this.releaseAll);
    this.pressed.clear();
    this.root.remove();
  }

  private readonly releaseAll = (): void => {
    this.pressed.clear();
  };
}
