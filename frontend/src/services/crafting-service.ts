import { apiClient } from "./api";

export interface CraftingJob {
  id: string;
  recipe_id: string;
  recipe_name: string;
  batches: number;
  output_item: string;
  output_name: string;
  output_quantity: number;
  started_at: string;
  finish_at: string;
  seconds_left: number;
  ready: boolean;
}

export interface Station {
  building_id: string;
  name: string;
  level: number;
  job_slots: number;
  used_slots: number;
  /** Bônus no tempo de produção da estação, em pontos-base (negativo = mais rápido). */
  time_bonus_bp: number;
  jobs: CraftingJob[];
}

export interface RecipeInput {
  item_id: string;
  name: string;
  per_batch: number;
  have: number;
}

export interface Recipe {
  id: string;
  name: string;
  description: string;
  station: string;
  inputs: RecipeInput[];
  output_item: string;
  output_name: string;
  output_quantity: number;
  duration_seconds: number;
  min_player_level: number;
  xp: number;
  max_batches: number;
  can_craft: boolean;
  blocked_reason: string | null;
}

export interface CraftingState {
  property_id: string;
  player_level: number;
  stations: Station[];
  recipes: Recipe[];
  replayed: boolean;
  collected: Record<string, number>;
  xp_gained: number;
}

export const craftingService = {
  getState: (propertyId: string, token: string): Promise<CraftingState> =>
    apiClient.get<CraftingState>(`/properties/${propertyId}/crafting`, { token }),

  /** Cada clique usa uma chave nova; um reenvio acidental não inicia outro trabalho. */
  start: (
    propertyId: string,
    recipeId: string,
    batches: number,
    token: string,
  ): Promise<CraftingState> =>
    apiClient.post<CraftingState>(
      `/properties/${propertyId}/crafting/start`,
      { recipe_id: recipeId, batches },
      { token, headers: { "Idempotency-Key": crypto.randomUUID() } },
    ),

  collect: (propertyId: string, token: string): Promise<CraftingState> =>
    apiClient.post<CraftingState>(`/properties/${propertyId}/crafting/collect`, undefined, { token }),
};
