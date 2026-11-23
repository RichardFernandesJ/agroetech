"""Constantes e validações do mundo jogável.

O servidor precisa conhecer os limites do mapa para validar a posição do
personagem. O desenho do mapa fica no cliente; aqui ficam apenas as dimensões
compartilhadas e o ponto de spawn.
"""

from __future__ import annotations

# Tiles de 32x32 pixels (o mesmo tamanho usado pelo Phaser).
TILE_SIZE = 32
MAP_COLUMNS = 40
MAP_ROWS = 30

WORLD_WIDTH = TILE_SIZE * MAP_COLUMNS
WORLD_HEIGHT = TILE_SIZE * MAP_ROWS

# Spawn logo abaixo da casa, no centro da fazenda.
SPAWN_TILE_X = 20
SPAWN_TILE_Y = 12
SPAWN_X = SPAWN_TILE_X * TILE_SIZE + TILE_SIZE / 2
SPAWN_Y = SPAWN_TILE_Y * TILE_SIZE + TILE_SIZE / 2

FACINGS = ("up", "down", "left", "right")
DEFAULT_FACING = "down"

# Margem para o corpo do personagem não encostar na borda do mundo.
CHARACTER_HALF_SIZE = TILE_SIZE / 2
MIN_POSITION = CHARACTER_HALF_SIZE
MAX_POSITION_X = WORLD_WIDTH - CHARACTER_HALF_SIZE
MAX_POSITION_Y = WORLD_HEIGHT - CHARACTER_HALF_SIZE


def is_position_inside_world(x: float, y: float) -> bool:
    return MIN_POSITION <= x <= MAX_POSITION_X and MIN_POSITION <= y <= MAX_POSITION_Y
