import type {
  CropCatalogItem,
  InventoryItem,
  Planting,
  Property,
} from "@/services/property-service";

/**
 * Estado da fazenda compartilhado entre os módulos da cena.
 * Só guarda dados; quem altera e atualiza a tela é o `FarmController`.
 */
export class FarmState {
  token?: string;
  property?: Property;
  crops: CropCatalogItem[] = [];
  plantings = new Map<number, Planting>();
  inventory: InventoryItem[] = [];
  balance = 0;
  level = 0;
}

/** Talhão com colheita pronta (qualquer estado equivalente a "pronto"). */
export function isPlantingReady(planting: Planting): boolean {
  return planting.status === "ready" || planting.seconds_until_ready === 0;
}

/** Texto curto de tempo restante: «45s» ou «3 min». */
export function formatRemaining(seconds: number, long = false): string {
  if (seconds > 60) {
    const minutes = Math.ceil(seconds / 60);
    return long ? `${minutes} minutos` : `${minutes} min`;
  }
  return long ? `${seconds} segundos` : `${seconds}s`;
}
