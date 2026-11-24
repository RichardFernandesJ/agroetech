import Phaser from "phaser";

import { ISLAND_CENTER, WORLD_HEIGHT, WORLD_WIDTH } from "@/game/world/map";

const MIN_ZOOM = 0.45;
const MAX_ZOOM = 2.2;
const DRAG_THRESHOLD = 6;

/**
 * Câmera livre da ilha: arrastar (pan), roda do mouse (zoom com foco no cursor)
 * e os atalhos do HUD. Também decide se um evento do mouse pertence ao mundo.
 */
export class CameraController {
  private isDragging = false;
  private hasDragged = false;
  private dragStartX = 0;
  private dragStartY = 0;
  private cameraStartScrollX = 0;
  private cameraStartScrollY = 0;

  /** ``isBlocked``: verdadeiro quando um painel está aberto sobre o mundo. */
  constructor(
    private readonly scene: Phaser.Scene,
    private readonly isBlocked: () => boolean,
  ) {
    this.frameIsland();
    this.bindInput();
  }

  /** Houve arrasto no clique atual (então não conta como clique em objeto). */
  get dragged(): boolean {
    return this.hasDragged;
  }

  /**
   * O Phaser também escuta o mouse na janela inteira. Sem este filtro, clicar
   * num botão de painel que esteja sobre um talhão "vazava" para o mundo.
   * Só vale evento que nasceu no canvas e sem painel aberto.
   */
  isWorldPointer(pointer: Phaser.Input.Pointer): boolean {
    if (this.isBlocked()) {
      return false;
    }
    const target = pointer.event?.target;
    return target === undefined || target === null || target === this.scene.game.canvas;
  }

  zoomIn(): void {
    const camera = this.scene.cameras.main;
    this.applyZoomAt(camera.zoom * 1.2, this.scene.scale.width / 2, this.scene.scale.height / 2);
  }

  zoomOut(): void {
    const camera = this.scene.cameras.main;
    this.applyZoomAt(camera.zoom / 1.2, this.scene.scale.width / 2, this.scene.scale.height / 2);
  }

  resetView(): void {
    const camera = this.scene.cameras.main;
    const zoom = this.optimalZoom();
    this.scene.tweens.add({
      targets: camera,
      zoom,
      scrollX: ISLAND_CENTER.x - this.scene.scale.width / 2 / zoom,
      scrollY: ISLAND_CENTER.y - this.scene.scale.height / 2 / zoom,
      duration: 350,
      ease: "Cubic.easeOut",
    });
  }

  private frameIsland(): void {
    const camera = this.scene.cameras.main;
    camera.setBackgroundColor("#14354f");
    camera.setBounds(-240, -200, WORLD_WIDTH + 480, WORLD_HEIGHT + 400);
    camera.setRoundPixels(true);
    camera.setZoom(this.optimalZoom());
    camera.centerOn(ISLAND_CENTER.x, ISLAND_CENTER.y);
  }

  private optimalZoom(): number {
    const { width, height } = this.scene.scale;
    const fit = Math.min(width / (WORLD_WIDTH + 80), height / (WORLD_HEIGHT + 60));
    return Phaser.Math.Clamp(Math.round(fit * 100) / 100, 0.75, 1.25);
  }

  private bindInput(): void {
    const camera = this.scene.cameras.main;
    const input = this.scene.input;

    input.on(
      "wheel",
      (
        pointer: Phaser.Input.Pointer,
        _objects: unknown[],
        _deltaX: number,
        deltaY: number,
      ) => {
        this.applyZoomAt(camera.zoom + (deltaY < 0 ? 0.12 : -0.12), pointer.x, pointer.y);
      },
    );

    input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      if (!this.isWorldPointer(pointer)) {
        return;
      }
      this.isDragging = true;
      this.hasDragged = false;
      this.dragStartX = pointer.x;
      this.dragStartY = pointer.y;
      this.cameraStartScrollX = camera.scrollX;
      this.cameraStartScrollY = camera.scrollY;
    });

    input.on("pointermove", (pointer: Phaser.Input.Pointer) => {
      if (!this.isDragging || !pointer.isDown) {
        return;
      }
      const dx = pointer.x - this.dragStartX;
      const dy = pointer.y - this.dragStartY;
      if (!this.hasDragged && Math.hypot(dx, dy) > DRAG_THRESHOLD) {
        this.hasDragged = true;
      }
      if (this.hasDragged) {
        camera.scrollX = this.cameraStartScrollX - dx / camera.zoom;
        camera.scrollY = this.cameraStartScrollY - dy / camera.zoom;
      }
    });

    input.on("pointerup", () => {
      this.isDragging = false;
    });
  }

  private applyZoomAt(targetZoom: number, screenX: number, screenY: number): void {
    const camera = this.scene.cameras.main;
    const zoom = Phaser.Math.Clamp(targetZoom, MIN_ZOOM, MAX_ZOOM);
    if (Math.abs(zoom - camera.zoom) < 0.001) {
      return;
    }
    const before = camera.getWorldPoint(screenX, screenY);
    camera.setZoom(zoom);
    const after = camera.getWorldPoint(screenX, screenY);
    camera.scrollX += before.x - after.x;
    camera.scrollY += before.y - after.y;
  }
}
