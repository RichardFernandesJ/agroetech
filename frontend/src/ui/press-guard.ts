/**
 * Evita que uma atualização automática redesenhe o painel no meio de um clique
 * (o botão sumiria entre apertar e soltar o mouse e o clique seria perdido).
 *
 * Uso: no início de `render()`, `if (this.guard.defer()) return;`.
 * Ao soltar o mouse, o guard chama `flush` (um instante depois do clique).
 */
export class PressGuard {
  private pressed = false;
  private pending = false;

  constructor(
    root: HTMLElement,
    private readonly flush: () => void,
  ) {
    root.addEventListener("pointerdown", this.onDown);
    window.addEventListener("pointerup", this.onUp);
    window.addEventListener("pointercancel", this.onUp);
  }

  /** Verdadeiro quando o redesenho deve esperar (botão do mouse apertado). */
  defer(): boolean {
    if (this.pressed) {
      this.pending = true;
      return true;
    }
    this.pending = false;
    return false;
  }

  dispose(): void {
    window.removeEventListener("pointerup", this.onUp);
    window.removeEventListener("pointercancel", this.onUp);
  }

  private readonly onDown = (): void => {
    this.pressed = true;
  };

  private readonly onUp = (): void => {
    this.pressed = false;
    if (this.pending) {
      window.setTimeout(this.flush, 0);
    }
  };
}
