import Phaser from "phaser";

import type { CharacterAppearance, Facing } from "@/services/character-service";

/**
 * Texturas geradas em runtime.
 *
 * O MVP não depende de arquivos de arte externos: cada tile e sprite é
 * desenhado com `Graphics` e convertido em textura. Isso mantém o repositório
 * leve e permite trocar a arte depois sem mexer na lógica do mapa.
 */

const SKIN_COLORS: Record<CharacterAppearance["skin_tone"], number> = {
  light: 0xf0c8a0,
  medium: 0xd39b6e,
  dark: 0xa9714a,
  deep: 0x7a4a2c,
};

const HAIR_COLOR = 0x3b2a1c;
const HAT_COLOR = 0xd8b25a;
const HAT_SHADE = 0xb8923f;
const TROUSERS_COLOR = 0x33414d;
const SHOE_COLOR = 0x2a2118;

type CharacterFrame = 0 | 1 | 2;

function makeTexture(
  scene: Phaser.Scene,
  key: string,
  width: number,
  height: number,
  draw: (graphics: Phaser.GameObjects.Graphics) => void,
): void {
  const graphics = scene.make.graphics({ x: 0, y: 0 }, false);
  draw(graphics);
  graphics.generateTexture(key, width, height);
  graphics.destroy();
}

function mulberry32(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state + 0x6d2b79f5) | 0;
    let value = Math.imul(state ^ (state >>> 15), 1 | state);
    value = (value + Math.imul(value ^ (value >>> 7), 61 | value)) ^ value;
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function darken(color: number): number {
  return (color >> 1) & 0x7f7f7f;
}

function drawGrass(graphics: Phaser.GameObjects.Graphics, seed: number): void {
  const random = mulberry32(seed);
  graphics.fillStyle(0x527f43, 1);
  graphics.fillRect(0, 0, 32, 32);

  for (let index = 0; index < 9; index += 1) {
    const x = Math.floor(random() * 30);
    const y = Math.floor(random() * 30);
    graphics.fillStyle(random() > 0.5 ? 0x466f39 : 0x5c8a4b, 1);
    graphics.fillRect(x, y, 2, 2);
  }
  for (let index = 0; index < 5; index += 1) {
    const x = Math.floor(random() * 31);
    const y = Math.floor(random() * 29);
    graphics.fillStyle(0x6b9a58, 1);
    graphics.fillRect(x, y, 1, 3);
  }
}

function drawDirt(graphics: Phaser.GameObjects.Graphics): void {
  const random = mulberry32(42);
  graphics.fillStyle(0x8a6a44, 1);
  graphics.fillRect(0, 0, 32, 32);

  for (let index = 0; index < 12; index += 1) {
    const x = Math.floor(random() * 31);
    const y = Math.floor(random() * 31);
    graphics.fillStyle(random() > 0.5 ? 0x7a5a36 : 0x9a7a52, 1);
    graphics.fillRect(x, y, 2, 2);
  }
}

function drawWater(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x2d6b88, 1);
  graphics.fillRect(0, 0, 32, 32);
  graphics.fillStyle(0x3d86a6, 1);
  graphics.fillRect(2, 7, 12, 2);
  graphics.fillRect(18, 8, 10, 2);
  graphics.fillRect(8, 20, 14, 2);
  graphics.fillStyle(0x275c78, 1);
  graphics.fillRect(0, 14, 8, 2);
  graphics.fillRect(22, 25, 8, 2);
}

function drawOcean(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x194363, 1);
  graphics.fillRect(0, 0, 32, 32);
  graphics.fillStyle(0x21537a, 1);
  graphics.fillRect(3, 8, 12, 2);
  graphics.fillRect(17, 21, 13, 2);
  graphics.fillStyle(0x2d6894, 1);
  graphics.fillRect(5, 9, 5, 1);
  graphics.fillRect(20, 22, 5, 1);
}

function drawShallowWater(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x287799, 1);
  graphics.fillRect(0, 0, 32, 32);
  graphics.fillStyle(0x3ea6c7, 1);
  graphics.fillRect(2, 6, 14, 3);
  graphics.fillRect(16, 18, 14, 3);
  graphics.fillStyle(0xcbf1f7, 0.75);
  graphics.fillRect(4, 7, 8, 1);
  graphics.fillRect(18, 19, 9, 1);
}

function drawSand(graphics: Phaser.GameObjects.Graphics, seed: number): void {
  const random = mulberry32(seed);
  graphics.fillStyle(0xd6bd7e, 1);
  graphics.fillRect(0, 0, 32, 32);
  for (let i = 0; i < 7; i += 1) {
    const x = Math.floor(random() * 30);
    const y = Math.floor(random() * 30);
    graphics.fillStyle(random() > 0.5 ? 0xebd996 : 0xbf9f5e, 1);
    graphics.fillRect(x, y, 2, 2);
  }
}

function drawSandDecor(graphics: Phaser.GameObjects.Graphics, seed: number): void {
  drawSand(graphics, seed);
  const random = mulberry32(seed + 101);
  if (random() > 0.5) {
    // Conchinha perolada
    graphics.fillStyle(0xf6ede2, 1);
    graphics.fillCircle(16, 16, 3);
    graphics.fillStyle(0xa6744f, 1);
    graphics.fillRect(15, 15, 2, 2);
  } else {
    // Estrela-do-mar tropical
    graphics.fillStyle(0xeb6b4b, 1);
    graphics.fillRect(15, 13, 2, 6);
    graphics.fillRect(13, 15, 6, 2);
    graphics.fillStyle(0xf59273, 1);
    graphics.fillRect(15, 15, 2, 2);
  }
}

function drawPier(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x194363, 0.35);
  graphics.fillRect(0, 0, 32, 32);
  graphics.fillStyle(0x7a5233, 1);
  graphics.fillRect(2, 2, 28, 7);
  graphics.fillRect(2, 11, 28, 7);
  graphics.fillRect(2, 20, 28, 7);
  graphics.fillStyle(0x94653e, 1);
  graphics.fillRect(4, 3, 24, 2);
  graphics.fillRect(4, 12, 24, 2);
  graphics.fillRect(4, 21, 24, 2);
  graphics.fillStyle(0x4a301a, 1);
  graphics.fillRect(0, 0, 2, 32);
  graphics.fillRect(30, 0, 2, 32);
  graphics.fillRect(2, 9, 28, 2);
  graphics.fillRect(2, 18, 28, 2);
  graphics.fillRect(2, 27, 28, 2);
}

function drawPalmTree(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x000000, 0.2);
  graphics.fillEllipse(24, 60, 34, 10);

  // Tronco curvado
  graphics.fillStyle(0x754e2f, 1);
  graphics.fillRect(20, 36, 7, 24);
  graphics.fillRect(18, 22, 7, 16);
  graphics.fillStyle(0x8f633d, 1);
  graphics.fillRect(21, 38, 2, 20);
  graphics.fillRect(19, 24, 2, 12);
  graphics.fillStyle(0x57371f, 1);
  graphics.fillRect(20, 42, 7, 2);
  graphics.fillRect(20, 50, 7, 2);
  graphics.fillRect(18, 30, 7, 2);

  // Cocos
  graphics.fillStyle(0x4a2a12, 1);
  graphics.fillCircle(19, 22, 3);
  graphics.fillCircle(24, 23, 3);

  // Folhas tropicais
  graphics.fillStyle(0x286326, 1);
  graphics.fillTriangle(20, 20, -2, 26, 8, 12);
  graphics.fillTriangle(22, 20, 46, 26, 36, 12);
  graphics.fillTriangle(21, 20, 10, 2, 32, 2);

  graphics.fillStyle(0x3e8a3a, 1);
  graphics.fillTriangle(20, 20, 2, 32, 12, 18);
  graphics.fillTriangle(22, 20, 42, 32, 32, 18);
  graphics.fillStyle(0x57a852, 1);
  graphics.fillRect(18, 18, 6, 4);
}

function drawBoat(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x000000, 0.2);
  graphics.fillEllipse(24, 26, 36, 10);
  graphics.fillStyle(0x8a5232, 1);
  graphics.fillRoundedRect(6, 10, 36, 16, 5);
  graphics.fillStyle(0xa66842, 1);
  graphics.fillRect(10, 12, 28, 10);
  graphics.fillStyle(0x63381e, 1);
  graphics.fillRect(6, 16, 36, 2);
  graphics.fillStyle(0xd4ab6a, 1);
  graphics.fillRect(18, 6, 3, 18);
  graphics.fillRect(15, 6, 6, 4);
}

function drawTree(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x000000, 0.22);
  graphics.fillEllipse(24, 60, 36, 10);

  graphics.fillStyle(0x5a3a22, 1);
  graphics.fillRect(21, 38, 6, 22);
  graphics.fillStyle(0x432a18, 1);
  graphics.fillRect(21, 48, 2, 12);

  graphics.fillStyle(0x2f6035, 1);
  graphics.fillCircle(24, 26, 20);
  graphics.fillStyle(0x3a7040, 1);
  graphics.fillCircle(16, 22, 12);
  graphics.fillCircle(32, 28, 12);
  graphics.fillStyle(0x4c8a4c, 1);
  graphics.fillCircle(20, 17, 6);
  graphics.fillCircle(30, 20, 5);
  graphics.fillStyle(0x5b9a58, 1);
  graphics.fillRect(18, 14, 3, 3);
  graphics.fillRect(29, 24, 2, 2);
}

function drawHouse(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x000000, 0.2);
  graphics.fillEllipse(96, 122, 176, 18);

  graphics.fillStyle(0x8a5a4a, 1);
  graphics.fillRect(148, 14, 16, 34);

  graphics.fillStyle(0xd9b184, 1);
  graphics.fillRect(12, 44, 168, 76);
  graphics.fillStyle(0xc59d72, 1);
  graphics.fillRect(12, 108, 168, 12);

  graphics.fillStyle(0x9c4038, 1);
  graphics.fillTriangle(4, 52, 188, 52, 96, 4);
  graphics.fillStyle(0x7f302b, 1);
  graphics.fillTriangle(4, 52, 96, 4, 96, 52);
  graphics.lineStyle(3, 0x6d2622, 1);
  graphics.strokeTriangle(4, 52, 188, 52, 96, 4);

  graphics.fillStyle(0x5c3b24, 1);
  graphics.fillRect(80, 82, 32, 46);
  graphics.fillStyle(0x7a5233, 1);
  graphics.fillRect(84, 86, 24, 38);
  graphics.fillStyle(0xd8b25a, 1);
  graphics.fillCircle(102, 106, 2);

  graphics.fillStyle(0xbfe3ea, 1);
  graphics.fillRect(30, 66, 30, 26);
  graphics.fillRect(132, 66, 30, 26);
  graphics.lineStyle(3, 0x6d4a2c, 1);
  graphics.strokeRect(30, 66, 30, 26);
  graphics.strokeRect(132, 66, 30, 26);
  graphics.lineStyle(1, 0x6d4a2c, 1);
  graphics.lineBetween(45, 66, 45, 92);
  graphics.lineBetween(132, 79, 162, 79);

  graphics.fillStyle(0x6d4a2c, 1);
  graphics.fillRect(76, 80, 40, 4);
}

function drawPlot(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x6d4a2c, 1);
  graphics.fillRect(0, 0, 64, 64);
  graphics.fillStyle(0x583a22, 1);
  graphics.fillRect(4, 4, 56, 56);

  for (let y = 10; y < 58; y += 10) {
    graphics.fillStyle(0x4a3019, 1);
    graphics.fillRect(6, y, 52, 3);
    graphics.fillStyle(0x6a4a2c, 1);
    graphics.fillRect(6, y + 3, 52, 1);
  }

  graphics.fillStyle(0x7d5a38, 1);
  graphics.fillRect(8, 52, 4, 3);
  graphics.fillRect(50, 12, 3, 3);
}

function drawMarket(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x000000, 0.2);
  graphics.fillEllipse(64, 90, 116, 12);

  graphics.fillStyle(0x7a5233, 1);
  graphics.fillRect(8, 34, 6, 58);
  graphics.fillRect(114, 34, 6, 58);

  for (let index = 0; index < 8; index += 1) {
    graphics.fillStyle(index % 2 === 0 ? 0xc0503f : 0xf2e2c4, 1);
    graphics.fillRect(4 + index * 15, 8, 15, 26);
  }
  graphics.fillStyle(0x8d3a2f, 1);
  graphics.fillRect(4, 30, 120, 4);

  graphics.fillStyle(0x9c6b40, 1);
  graphics.fillRect(10, 62, 108, 22);
  graphics.fillStyle(0x7a5233, 1);
  graphics.fillRect(10, 80, 108, 4);

  graphics.fillStyle(0xd9b96a, 1);
  graphics.fillCircle(30, 58, 5);
  graphics.fillStyle(0xc0503f, 1);
  graphics.fillCircle(48, 58, 4);
  graphics.fillStyle(0x5b9a58, 1);
  graphics.fillCircle(66, 58, 5);
  graphics.fillStyle(0xd9b96a, 1);
  graphics.fillCircle(86, 58, 4);
}

function drawWell(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x000000, 0.2);
  graphics.fillEllipse(24, 44, 34, 8);

  graphics.fillStyle(0x8b8b86, 1);
  graphics.fillEllipse(24, 34, 32, 14);
  graphics.fillStyle(0x2a2a28, 1);
  graphics.fillEllipse(24, 34, 22, 9);
  graphics.fillStyle(0x6f6f6a, 1);
  graphics.fillRect(8, 30, 4, 12);
  graphics.fillRect(36, 30, 4, 12);

  graphics.fillStyle(0x7a5233, 1);
  graphics.fillRect(10, 10, 3, 24);
  graphics.fillRect(35, 10, 3, 24);
  graphics.fillStyle(0x9c4038, 1);
  graphics.fillTriangle(6, 14, 42, 14, 24, 2);
  graphics.fillStyle(0x5a3a22, 1);
  graphics.fillRect(12, 14, 24, 3);
}

function drawCropSprout(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x4ca848, 1);
  const spots = [
    { x: 18, y: 18 },
    { x: 44, y: 18 },
    { x: 18, y: 44 },
    { x: 44, y: 44 },
  ];
  for (const s of spots) {
    graphics.fillStyle(0x2f6b2c, 1);
    graphics.fillRect(s.x + 1, s.y + 5, 2, 5);
    graphics.fillStyle(0x5cb858, 1);
    graphics.fillRect(s.x - 2, s.y + 2, 3, 3);
    graphics.fillRect(s.x + 3, s.y + 1, 3, 3);
  }
}

function drawCropGrowing(graphics: Phaser.GameObjects.Graphics): void {
  const spots = [
    { x: 18, y: 18 },
    { x: 44, y: 18 },
    { x: 18, y: 44 },
    { x: 44, y: 44 },
  ];
  for (const s of spots) {
    graphics.fillStyle(0x286326, 1);
    graphics.fillRect(s.x + 1, s.y + 2, 3, 11);
    graphics.fillRect(s.x - 4, s.y + 4, 5, 3);
    graphics.fillRect(s.x + 3, s.y + 2, 5, 3);
    graphics.fillStyle(0x4ca848, 1);
    graphics.fillRect(s.x - 1, s.y - 1, 6, 5);
  }
}

function drawCropMature(graphics: Phaser.GameObjects.Graphics, cropId: string): void {
  const spots = [
    { x: 18, y: 18 },
    { x: 44, y: 18 },
    { x: 18, y: 44 },
    { x: 44, y: 44 },
  ];

  for (const s of spots) {
    // Folhagem base
    graphics.fillStyle(0x286326, 1);
    graphics.fillRect(s.x + 1, s.y + 3, 3, 11);
    graphics.fillRect(s.x - 5, s.y + 5, 6, 4);
    graphics.fillRect(s.x + 3, s.y + 3, 6, 4);

    if (cropId === "milho") {
      // Espiga de milho dourada
      graphics.fillStyle(0xd9b33a, 1);
      graphics.fillRect(s.x, s.y - 4, 5, 10);
      graphics.fillStyle(0xf5d862, 1);
      graphics.fillRect(s.x + 1, s.y - 3, 3, 8);
    } else if (cropId === "cenoura") {
      // Topo de cenoura laranja
      graphics.fillStyle(0xe06326, 1);
      graphics.fillRect(s.x - 1, s.y + 7, 7, 6);
      graphics.fillStyle(0xf27d44, 1);
      graphics.fillRect(s.x, s.y + 8, 5, 4);
    } else if (cropId === "tomate") {
      // Tomates vermelhos redondos
      graphics.fillStyle(0xcc3325, 1);
      graphics.fillCircle(s.x - 1, s.y + 3, 4);
      graphics.fillCircle(s.x + 6, s.y + 5, 4);
      graphics.fillStyle(0xf05646, 1);
      graphics.fillRect(s.x - 2, s.y + 2, 2, 2);
      graphics.fillRect(s.x + 5, s.y + 4, 2, 2);
    } else if (cropId === "morango") {
      // Moranguinhos vermelhos
      graphics.fillStyle(0xd62828, 1);
      graphics.fillRect(s.x - 2, s.y + 5, 5, 6);
      graphics.fillRect(s.x + 4, s.y + 4, 5, 6);
      graphics.fillStyle(0xf4df42, 1);
      graphics.fillRect(s.x - 1, s.y + 7, 1, 1);
      graphics.fillRect(s.x + 5, s.y + 6, 1, 1);
    } else {
      // Café (grãos vermelhos escuros)
      graphics.fillStyle(0x7a1818, 1);
      graphics.fillCircle(s.x, s.y + 1, 3);
      graphics.fillCircle(s.x + 5, s.y + 3, 3);
      graphics.fillCircle(s.x + 2, s.y + 6, 3);
      graphics.fillStyle(0xa83232, 1);
      graphics.fillRect(s.x - 1, s.y, 2, 2);
    }
  }
}

function drawReadyBadge(graphics: Phaser.GameObjects.Graphics): void {
  graphics.fillStyle(0x000000, 0.25);
  graphics.fillCircle(12, 14, 11);
  graphics.fillStyle(0xd9a836, 1);
  graphics.fillCircle(12, 12, 11);
  graphics.fillStyle(0xf7e27e, 1);
  graphics.fillCircle(12, 12, 8);
  // Foice/brilho
  graphics.fillStyle(0x5c3b1e, 1);
  graphics.fillRect(11, 7, 2, 10);
  graphics.fillRect(8, 7, 7, 2);
  graphics.fillRect(7, 8, 3, 3);
}

function drawFlower(graphics: Phaser.GameObjects.Graphics, petal: number): void {
  graphics.fillStyle(0x3f6f39, 1);
  graphics.fillRect(5, 5, 2, 7);
  graphics.fillStyle(petal, 1);
  graphics.fillRect(3, 2, 3, 3);
  graphics.fillRect(7, 2, 3, 3);
  graphics.fillRect(5, 0, 3, 3);
  graphics.fillRect(5, 4, 3, 3);
  graphics.fillStyle(0xf4e4b5, 1);
  graphics.fillRect(5, 2, 3, 3);
}

export function createWorldTextures(scene: Phaser.Scene): void {
  if (scene.textures.exists("tile-grass")) {
    return;
  }

  makeTexture(scene, "tile-ocean", 32, 32, drawOcean);
  makeTexture(scene, "tile-shallow-water", 32, 32, drawShallowWater);
  makeTexture(scene, "tile-sand", 32, 32, (graphics) => drawSand(graphics, 31));
  makeTexture(scene, "tile-sand-decor", 32, 32, (graphics) => drawSandDecor(graphics, 47));
  makeTexture(scene, "tile-pier", 32, 32, drawPier);
  makeTexture(scene, "palm-tree", 48, 64, drawPalmTree);
  makeTexture(scene, "boat", 48, 32, drawBoat);

  makeTexture(scene, "tile-grass", 32, 32, (graphics) => drawGrass(graphics, 7));
  makeTexture(scene, "tile-grass-2", 32, 32, (graphics) => drawGrass(graphics, 19));
  makeTexture(scene, "tile-dirt", 32, 32, drawDirt);
  makeTexture(scene, "tile-water", 32, 32, drawWater);
  makeTexture(scene, "tree", 48, 64, drawTree);
  makeTexture(scene, "house", 192, 128, drawHouse);
  makeTexture(scene, "plot", 64, 64, drawPlot);
  makeTexture(scene, "market", 128, 96, drawMarket);
  makeTexture(scene, "well", 48, 48, drawWell);
  makeTexture(scene, "crop-sprout", 64, 64, drawCropSprout);
  makeTexture(scene, "crop-growing", 64, 64, drawCropGrowing);
  makeTexture(scene, "crop-mature-milho", 64, 64, (graphics) => drawCropMature(graphics, "milho"));
  makeTexture(scene, "crop-mature-cenoura", 64, 64, (graphics) => drawCropMature(graphics, "cenoura"));
  makeTexture(scene, "crop-mature-tomate", 64, 64, (graphics) => drawCropMature(graphics, "tomate"));
  makeTexture(scene, "crop-mature-morango", 64, 64, (graphics) => drawCropMature(graphics, "morango"));
  makeTexture(scene, "crop-mature-cafe", 64, 64, (graphics) => drawCropMature(graphics, "cafe"));
  makeTexture(scene, "ready-badge", 24, 24, drawReadyBadge);

  makeTexture(scene, "flower-a", 12, 12, (graphics) => drawFlower(graphics, 0xe8d36a));
  makeTexture(scene, "flower-b", 12, 12, (graphics) => drawFlower(graphics, 0xd97a8a));
  makeTexture(scene, "flower-c", 12, 12, (graphics) => drawFlower(graphics, 0x9fc4e8));
}

export function characterTextureKey(facing: Facing, frame: CharacterFrame): string {
  return `char-${facing}-${frame}`;
}

function drawCharacter(
  graphics: Phaser.GameObjects.Graphics,
  facing: Facing,
  frame: CharacterFrame,
  appearance: CharacterAppearance,
): void {
  const skin = SKIN_COLORS[appearance.skin_tone];
  const outfit = Phaser.Display.Color.HexStringToColor(appearance.outfit_color).color;

  graphics.fillStyle(0x000000, 0.22);
  graphics.fillEllipse(16, 38, 20, 6);

  graphics.fillStyle(TROUSERS_COLOR, 1);
  if (frame === 0) {
    graphics.fillRect(12, 29, 4, 9);
    graphics.fillRect(17, 29, 4, 9);
  } else if (frame === 1) {
    graphics.fillRect(11, 30, 4, 8);
    graphics.fillRect(18, 28, 4, 8);
  } else {
    graphics.fillRect(13, 28, 4, 8);
    graphics.fillRect(16, 30, 4, 8);
  }
  graphics.fillStyle(SHOE_COLOR, 1);
  if (frame === 0) {
    graphics.fillRect(11, 36, 5, 2);
    graphics.fillRect(17, 36, 5, 2);
  } else if (frame === 1) {
    graphics.fillRect(10, 36, 5, 2);
    graphics.fillRect(18, 34, 5, 2);
  } else {
    graphics.fillRect(12, 34, 5, 2);
    graphics.fillRect(17, 36, 5, 2);
  }

  const armOffset = frame === 1 ? -1 : frame === 2 ? 1 : 0;

  graphics.fillStyle(outfit, 1);
  graphics.fillRect(10, 17, 12, 14);
  graphics.fillStyle(darken(outfit), 1);
  graphics.fillRect(10, 28, 12, 3);
  graphics.fillStyle(0xffffff, 0.12);
  graphics.fillRect(11, 18, 3, 8);

  graphics.fillStyle(outfit, 1);
  graphics.fillRect(7, 18 + armOffset, 3, 6);
  graphics.fillRect(22, 18 - armOffset, 3, 6);
  graphics.fillStyle(skin, 1);
  graphics.fillRect(7, 24 + armOffset, 3, 4);
  graphics.fillRect(22, 24 - armOffset, 3, 4);

  graphics.fillStyle(skin, 1);
  graphics.fillRect(14, 17, 4, 3);
  graphics.fillRect(10, 5, 12, 13);
  graphics.fillRect(8, 10, 2, 4);
  graphics.fillRect(22, 10, 2, 4);

  if (appearance.hair_style === "cap") {
    graphics.fillStyle(HAT_COLOR, 1);
    graphics.fillRect(9, 2, 14, 6);
    graphics.fillRect(5, 7, 22, 2);
    graphics.fillStyle(HAT_SHADE, 1);
    graphics.fillRect(9, 6, 14, 2);
  } else {
    graphics.fillStyle(HAIR_COLOR, 1);
    graphics.fillRect(9, 4, 14, 5);
    if (facing === "up") {
      graphics.fillRect(9, 8, 14, 9);
    } else {
      graphics.fillRect(9, 8, 2, 6);
      graphics.fillRect(21, 8, 2, 6);
    }
    if (appearance.hair_style === "long") {
      graphics.fillRect(8, 10, 2, 10);
      graphics.fillRect(22, 10, 2, 10);
    }
    if (appearance.hair_style === "bun") {
      graphics.fillCircle(16, 3, 3);
    }
  }

  graphics.fillStyle(0x2a2118, 1);
  if (facing === "down") {
    graphics.fillRect(13, 12, 2, 2);
    graphics.fillRect(18, 12, 2, 2);
    graphics.fillStyle(0x9a5a44, 1);
    graphics.fillRect(15, 16, 3, 1);
  } else if (facing === "left") {
    graphics.fillRect(11, 12, 2, 2);
  } else if (facing === "right") {
    graphics.fillRect(19, 12, 2, 2);
  }
}

export function createCharacterTextures(
  scene: Phaser.Scene,
  appearance: CharacterAppearance,
): void {
  const facings: Facing[] = ["up", "down", "left", "right"];
  const frames: CharacterFrame[] = [0, 1, 2];

  for (const facing of facings) {
    for (const frame of frames) {
      const key = characterTextureKey(facing, frame);
      if (scene.textures.exists(key)) {
        scene.textures.remove(key);
      }
      makeTexture(scene, key, 32, 40, (graphics) =>
        drawCharacter(graphics, facing, frame, appearance),
      );
    }
  }
}
