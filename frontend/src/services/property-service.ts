import { apiClient } from "./api";

export interface Property {
  id: string;
  name: string;
  area_hectares: number;
  plot_count: number;
  created_at: string;
  last_production_sync_at: string;
}

export type PlantingStatus = "growing" | "ready" | "exhausted";

export interface Planting {
  id: string;
  property_id: string;
  crop_id: string;
  crop_name: string;
  plot_index: number;
  status: PlantingStatus;
  planted_at: string;
  next_ready_at: string;
  cycles_done: number;
  max_cycles: number;
  stored_cycles: number;
  seconds_until_ready: number | null;
  expected_yield: number;
}

export interface HarvestOutcome {
  planting_id: string;
  crop_id: string;
  crop_name: string;
  cycles_harvested: number;
  product_item: string;
  product_name: string;
  product_quantity: number;
  seed_item: string;
  seed_name: string;
  seed_quantity: number;
  planting_status: PlantingStatus;
}

export interface HarvestAllOutcome {
  property_id: string;
  harvests: HarvestOutcome[];
  products: Record<string, number>;
  seeds: Record<string, number>;
}

export interface InventoryItem {
  item_id: string;
  name: string;
  category: string;
  description: string;
  quantity: number;
}

export interface InventoryResponse {
  property_id: string;
  items: InventoryItem[];
}

export interface CropCatalogItem {
  id: string;
  name: string;
  category: string;
  description: string;
  grow_seconds: number;
  yield_quantity: number;
  max_cycles: number;
  seed_item: string;
  product_item: string;
}

export const propertyService = {
  get: (propertyId: string, token: string): Promise<Property> =>
    apiClient.get<Property>(`/properties/${propertyId}`, { token }),

  getPlantings: (propertyId: string, token: string): Promise<Planting[]> =>
    apiClient.get<Planting[]>(`/properties/${propertyId}/plantings`, { token }),

  plant: (
    propertyId: string,
    payload: { crop_id: string; plot_index: number },
    token: string,
  ): Promise<Planting> =>
    apiClient.post<Planting>(`/properties/${propertyId}/plantings`, payload, { token }),

  harvest: (plantingId: string, token: string): Promise<HarvestOutcome> =>
    apiClient.post<HarvestOutcome>(`/plantings/${plantingId}/harvest`, undefined, { token }),

  harvestAll: (propertyId: string, token: string): Promise<HarvestAllOutcome> =>
    apiClient.post<HarvestAllOutcome>(`/properties/${propertyId}/harvest`, undefined, { token }),

  getInventory: (propertyId: string, token: string): Promise<InventoryResponse> =>
    apiClient.get<InventoryResponse>(`/properties/${propertyId}/inventory`, { token }),

  getCrops: (): Promise<CropCatalogItem[]> =>
    apiClient.get<CropCatalogItem[]>("/catalog/crops"),
};
