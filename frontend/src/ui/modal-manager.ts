/** Qualquer painel DOM que a cena possa abrir e fechar. */
export interface ClosableModal {
  destroy(): void;
}

/**
 * Garante um único painel aberto por vez e centraliza o ciclo de vida.
 *
 * Cada painel recebe uma função `close` para se fechar sem conhecer a cena.
 * Novos painéis (talentos, guilda, fábrica...) só precisam de um construtor
 * que aceite `onClose`; a cena não repete lógica de abrir/fechar.
 */
export class ModalManager {
  private active: ClosableModal | null = null;

  get isOpen(): boolean {
    return this.active !== null;
  }

  open<T extends ClosableModal>(factory: (close: () => void) => T): T {
    this.close();
    const modal = factory(() => this.closeIf(modal));
    this.active = modal;
    return modal;
  }

  close(): void {
    const current = this.active;
    this.active = null;
    current?.destroy();
  }

  private closeIf(modal: ClosableModal): void {
    if (this.active === modal) {
      this.close();
    }
  }
}
