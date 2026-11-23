import type { Character } from "@/services/character-service";

/** Estado de jogo compartilhado entre as cenas e a UI. */
class GameState {
  private character: Character | null = null;

  get currentCharacter(): Character | null {
    return this.character;
  }

  setCharacter(character: Character): void {
    this.character = character;
  }

  updatePosition(x: number, y: number, facing: Character["facing"]): void {
    if (!this.character) {
      return;
    }
    this.character = {
      ...this.character,
      position_x: x,
      position_y: y,
      facing,
    };
  }

  clear(): void {
    this.character = null;
  }
}

export const gameState = new GameState();
