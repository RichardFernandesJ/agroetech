/**
 * Dados do mapa da ilha da fazenda.
 *
 * O mundo agora é uma ilha em pixel art cercada por oceano.
 * A visualização é estilo "God-view" / simulação rural, jogada através do mouse
 * com pan livre e zoom dinâmico.
 */

export const TILE_SIZE = 32;
export const MAP_COLUMNS = 40;
export const MAP_ROWS = 30;
export const WORLD_WIDTH = MAP_COLUMNS * TILE_SIZE;
export const WORLD_HEIGHT = MAP_ROWS * TILE_SIZE;

/** Centro da ilha / ponto focal padrão da câmera. */
export const ISLAND_CENTER = {
  x: WORLD_WIDTH / 2, // 640
  y: WORLD_HEIGHT / 2, // 480
} as const;

export const SPAWN = ISLAND_CENTER;

export interface WorldRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Interactable {
  id: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  radius: number;
  label: string;
  message: string;
}

export const HOUSE: WorldRect = { x: 544, y: 120, width: 192, height: 128 };
export const POND: WorldRect = { x: 224, y: 576, width: 160, height: 160 };
export const MARKET: WorldRect = { x: 928, y: 288, width: 128, height: 96 };
export const WELL = { x: 384, y: 384 } as const;
export const BOAT = { x: 1140, y: 380 } as const;

export const FENCE = {
  left: 512,
  right: 768,
  top: 480,
  bottom: 656,
  gateLeft: 608,
  gateRight: 672,
} as const;

export const PLOT_SIZE = 64;
export const PLOT_GAP = 16;
const PLOT_START_X = 528;
const PLOT_START_Y = 496;

export const BASE_PLOTS = 6;
export const MAX_PLOTS = 12;

/**
 * Os 6 primeiros talhões formam a grade 3x2. Cada melhoria da Casa da Fazenda
 * abre uma coluna nova (2 talhões), para o leste, onde ainda há terra firme
 * (ao sul fica a praia).
 */
export const PLOTS = Array.from({ length: MAX_PLOTS }, (_, index) => {
  const extra = index - BASE_PLOTS;
  const column = extra < 0 ? index % 3 : 3 + Math.floor(extra / 2);
  const row = extra < 0 ? Math.floor(index / 3) : extra % 2;
  return {
    index,
    x: PLOT_START_X + column * (PLOT_SIZE + PLOT_GAP),
    y: PLOT_START_Y + row * (PLOT_SIZE + PLOT_GAP),
  };
});

/** Cerca direita conforme os talhões liberados (3 colunas + 1 a cada 2 talhões extras). */
export function fenceRightFor(plotCount: number): number {
  const columns = 3 + Math.ceil(Math.max(0, plotCount - BASE_PLOTS) / 2);
  return PLOT_START_X + columns * (PLOT_SIZE + PLOT_GAP);
}

export const FENCE_MAX_RIGHT = fenceRightFor(MAX_PLOTS);

export const PIER_TILES = [
  { x: 33, y: 10 },
  { x: 34, y: 10 },
  { x: 35, y: 10 },
  { x: 35, y: 11 },
];

export type IslandTileType =
  | "ocean"
  | "shallow-water"
  | "sand"
  | "sand-decor"
  | "grass"
  | "grass-2"
  | "dirt"
  | "pond-water";

export function isDirtTile(tileX: number, tileY: number): boolean {
  const verticalPath = tileX >= 19 && tileX <= 20 && tileY >= 8 && tileY <= 15;
  const marketPath = tileY >= 10 && tileY <= 11 && tileX >= 21 && tileX <= 29;
  const wellPath = tileY >= 12 && tileY <= 13 && tileX >= 12 && tileX <= 19;
  const plotYard = tileX >= 16 && tileX <= 23 && tileY >= 15 && tileY <= 20;
  const pondRim =
    tileX >= 6 &&
    tileX <= 12 &&
    tileY >= 17 &&
    tileY <= 23 &&
    !(tileX >= 7 && tileX <= 11 && tileY >= 18 && tileY <= 22);

  return verticalPath || marketPath || wellPath || plotYard || pondRim;
}

export function getIslandTile(tileX: number, tileY: number): IslandTileType {
  // Lagoa interna de água doce
  if (tileX >= 7 && tileX <= 11 && tileY >= 18 && tileY <= 22) {
    return "pond-water";
  }

  const cx = 19.5;
  const cy = 14.5;
  const rx = 14.2;
  const ry = 10.6;

  const dx = (tileX - cx) / rx;
  const dy = (tileY - cy) / ry;
  const dist = Math.sqrt(dx * dx + dy * dy);

  // Variação angular para costa orgânica
  const angle = Math.atan2(dy, dx);
  const irregularity =
    0.09 * Math.sin(angle * 3 + 0.4) +
    0.06 * Math.cos(angle * 5 - 1.1) +
    0.04 * Math.sin(angle * 2 + 1.6);

  const edge = 1.0 + irregularity;

  if (dist > edge + 0.16) {
    return "ocean";
  }
  if (dist > edge + 0.03) {
    return "shallow-water";
  }
  if (dist > edge - 0.12) {
    const hash = (tileX * 73856093) ^ (tileY * 19349663);
    return (hash & 0x7) === 0 ? "sand-decor" : "sand";
  }

  // Caminhos de terra no interior da ilha
  if (isDirtTile(tileX, tileY)) {
    return "dirt";
  }

  // Variação de grama
  const hash = (tileX * 374761393) ^ (tileY * 668265263);
  return (hash & 0x3) === 0 ? "grass-2" : "grass";
}

export interface TreeSpot {
  x: number;
  y: number;
}

/** Palmeiras na orla de areia e praias da ilha */
export const PALM_TREES: TreeSpot[] = [
  { x: 300, y: 220 },
  { x: 860, y: 190 },
  { x: 1040, y: 440 },
  { x: 850, y: 740 },
  { x: 750, y: 770 },
  { x: 440, y: 750 },
  { x: 260, y: 440 },
  { x: 960, y: 210 },
  { x: 340, y: 680 },
];

/** Árvores de madeira/pomar no interior da ilha */
export const INLAND_TREES: TreeSpot[] = [
  { x: 450, y: 190 },
  { x: 790, y: 190 },
  { x: 840, y: 260 },
  { x: 460, y: 520 },
  { x: 420, y: 630 },
  { x: 820, y: 460 },
  { x: 1010, y: 455 },
  { x: 490, y: 310 },
  { x: 770, y: 320 },
];

function intersects(x: number, y: number, rect: WorldRect, padding = 0): boolean {
  return (
    x >= rect.x - padding &&
    x <= rect.x + rect.width + padding &&
    y >= rect.y - padding &&
    y <= rect.y + rect.height + padding
  );
}

/** Permite flores apenas em solo verdejante livre de construções. */
export function isDecorBlocked(x: number, y: number): boolean {
  const tileX = Math.floor(x / TILE_SIZE);
  const tileY = Math.floor(y / TILE_SIZE);
  const tileType = getIslandTile(tileX, tileY);

  if (tileType !== "grass" && tileType !== "grass-2") {
    return true;
  }

  if (intersects(x, y, HOUSE, 20) || intersects(x, y, POND, 20)) {
    return true;
  }
  if (intersects(x, y, MARKET, 20)) {
    return true;
  }
  if (Math.abs(x - WELL.x) < 40 && Math.abs(y - WELL.y) < 40) {
    return true;
  }
  if (
    x >= FENCE.left - 16 &&
    x <= FENCE_MAX_RIGHT + 16 &&
    y >= FENCE.top - 16 &&
    y <= FENCE.bottom + 16
  ) {
    return true;
  }

  return false;
}
