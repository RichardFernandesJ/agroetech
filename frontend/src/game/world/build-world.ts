import Phaser from "phaser";

import {
  BOAT,
  FENCE,
  HOUSE,
  INLAND_TREES,
  MAP_COLUMNS,
  MAP_ROWS,
  MARKET,
  PALM_TREES,
  PIER_TILES,
  PLOTS,
  POND,
  TILE_SIZE,
  WELL,
  WORLD_HEIGHT,
  WORLD_WIDTH,
  getIslandTile,
  isDecorBlocked,
} from "./map";

export interface WorldObjectInteractable {
  id: string;
  label: string;
  message: string;
  gameObject: Phaser.GameObjects.GameObject;
  x: number;
  y: number;
}

export interface WorldBuild {
  interactables: WorldObjectInteractable[];
  plotSprites: Phaser.GameObjects.Image[];
}

const GROUND_DEPTH = -20;
const PIER_DEPTH = -10;
const FLOWER_DEPTH = 1;

function seededRandom(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function drawGround(scene: Phaser.Scene): void {
  for (let tileY = 0; tileY < MAP_ROWS; tileY += 1) {
    for (let tileX = 0; tileX < MAP_COLUMNS; tileX += 1) {
      const x = tileX * TILE_SIZE + TILE_SIZE / 2;
      const y = tileY * TILE_SIZE + TILE_SIZE / 2;

      const tileType = getIslandTile(tileX, tileY);
      let texture = "tile-grass";

      switch (tileType) {
        case "ocean":
          texture = "tile-ocean";
          break;
        case "shallow-water":
          texture = "tile-shallow-water";
          break;
        case "sand":
          texture = "tile-sand";
          break;
        case "sand-decor":
          texture = "tile-sand-decor";
          break;
        case "dirt":
          texture = "tile-dirt";
          break;
        case "pond-water":
          texture = "tile-water";
          break;
        case "grass-2":
          texture = "tile-grass-2";
          break;
        case "grass":
        default:
          texture = "tile-grass";
          break;
      }

      scene.add.image(x, y, texture).setDepth(GROUND_DEPTH);
    }
  }

  // Píer de madeira que avança sobre a praia/água na costa leste
  for (const pier of PIER_TILES) {
    const x = pier.x * TILE_SIZE + TILE_SIZE / 2;
    const y = pier.y * TILE_SIZE + TILE_SIZE / 2;
    scene.add.image(x, y, "tile-pier").setDepth(PIER_DEPTH);
  }
}

function drawFlowers(scene: Phaser.Scene): void {
  const random = seededRandom(77);
  const textures = ["flower-a", "flower-b", "flower-c"] as const;
  let placed = 0;
  let attempts = 0;

  while (placed < 60 && attempts < 600) {
    attempts += 1;
    const x = 32 + random() * (WORLD_WIDTH - 64);
    const y = 32 + random() * (WORLD_HEIGHT - 64);
    if (isDecorBlocked(x, y)) {
      continue;
    }
    const texture = textures[Math.floor(random() * textures.length)] ?? "flower-a";
    scene.add.image(x, y, texture).setDepth(FLOWER_DEPTH).setAlpha(0.9);
    placed += 1;
  }
}

function drawFences(scene: Phaser.Scene): void {
  const graphics = scene.add.graphics().setDepth(FENCE.top + 4);

  const horizontal = (from: number, to: number, y: number): void => {
    graphics.fillStyle(0x8f6a42, 1);
    graphics.fillRect(from, y + 7, to - from, 3);
    graphics.fillRect(from, y + 15, to - from, 3);
    graphics.fillStyle(0x6f4e30, 1);
    for (let x = from; x <= to; x += 32) {
      graphics.fillRect(x + 13, y + 2, 6, 20);
    }
  };

  const vertical = (x: number, from: number, to: number): void => {
    graphics.fillStyle(0x8f6a42, 1);
    graphics.fillRect(x + 7, from, 3, to - from);
    graphics.fillRect(x + 15, from, 3, to - from);
    graphics.fillStyle(0x6f4e30, 1);
    for (let y = from; y <= to; y += 32) {
      graphics.fillRect(x + 2, y + 13, 20, 6);
    }
  };

  horizontal(FENCE.left, FENCE.gateLeft, FENCE.top);
  horizontal(FENCE.gateRight, FENCE.right, FENCE.top);
  horizontal(FENCE.left, FENCE.right, FENCE.bottom);
  vertical(FENCE.left, FENCE.top, FENCE.bottom);
  vertical(FENCE.right, FENCE.top, FENCE.bottom);
}

export function buildWorld(scene: Phaser.Scene): WorldBuild {
  drawGround(scene);
  drawFlowers(scene);

  const interactables: WorldObjectInteractable[] = [];
  const plotSprites: Phaser.GameObjects.Image[] = [];

  // Casa da fazenda
  const house = scene.add
    .image(HOUSE.x, HOUSE.y, "house")
    .setOrigin(0, 0)
    .setDepth(HOUSE.y + HOUSE.height)
    .setInteractive({ useHandCursor: true });

  interactables.push({
    id: "house",
    label: "Casa da Fazenda",
    message: "Casa da fazenda: sua fazenda na ilha fica salva com segurança no servidor.",
    gameObject: house,
    x: HOUSE.x + HOUSE.width / 2,
    y: HOUSE.y + HOUSE.height / 2,
  });

  // Lagoa interna de água doce
  const pondTiles = Math.ceil(POND.width / TILE_SIZE);
  for (let row = 0; row < pondTiles; row += 1) {
    for (let column = 0; column < pondTiles; column += 1) {
      scene.add
        .image(
          POND.x + column * TILE_SIZE + TILE_SIZE / 2,
          POND.y + row * TILE_SIZE + TILE_SIZE / 2,
          "tile-water",
        )
        .setDepth(GROUND_DEPTH + 1);
    }
  }

  // Talhões agrícolas (clicáveis para cultivo direto)
  for (const plot of PLOTS) {
    const plotSprite = scene.add
      .image(plot.x, plot.y, "plot")
      .setOrigin(0, 0)
      .setDepth(plot.y)
      .setInteractive({ useHandCursor: true });

    plotSprites.push(plotSprite);

    interactables.push({
      id: `plot-${plot.index}`,
      label: `Talhão ${plot.index + 1}`,
      message: `Talhão ${plot.index + 1}: clique para gerenciar o cultivo ou colher.`,
      gameObject: plotSprite,
      x: plot.x + 32,
      y: plot.y + 32,
    });
  }

  drawFences(scene);

  // Mercado da Ilha
  const market = scene.add
    .image(MARKET.x + MARKET.width / 2, MARKET.y + MARKET.height, "market")
    .setOrigin(0.5, 1)
    .setDepth(MARKET.y + MARKET.height)
    .setInteractive({ useHandCursor: true });

  interactables.push({
    id: "market",
    label: "Mercado da Ilha",
    message: "Mercado da Ilha: compre sementes e comercialize suas colheitas por AgroCoin.",
    gameObject: market,
    x: MARKET.x + MARKET.width / 2,
    y: MARKET.y + MARKET.height / 2,
  });

  // Poço artesiano
  const well = scene.add
    .image(WELL.x, WELL.y + 24, "well")
    .setOrigin(0.5, 1)
    .setDepth(WELL.y + 24)
    .setInteractive({ useHandCursor: true });

  interactables.push({
    id: "well",
    label: "Poço da Ilha",
    message: "Poço da Ilha: fonte de água cristalina para irrigação das suas lavouras.",
    gameObject: well,
    x: WELL.x,
    y: WELL.y + 12,
  });

  // Barco de pesca próximo ao píer
  const boat = scene.add
    .image(BOAT.x, BOAT.y, "boat")
    .setOrigin(0.5, 0.5)
    .setDepth(BOAT.y)
    .setInteractive({ useHandCursor: true });

  interactables.push({
    id: "boat",
    label: "Barco de Pesca",
    message: "Barco ancorado no píer da ilha: navegação e comércio marítimo em breve.",
    gameObject: boat,
    x: BOAT.x,
    y: BOAT.y,
  });

  // Palmeiras nas praias
  for (const palm of PALM_TREES) {
    scene.add.image(palm.x, palm.y, "palm-tree").setOrigin(0.5, 1).setDepth(palm.y);
  }

  // Árvores no interior da ilha
  for (const tree of INLAND_TREES) {
    scene.add.image(tree.x, tree.y, "tree").setOrigin(0.5, 1).setDepth(tree.y);
  }

  return {
    interactables,
    plotSprites,
  };
}
