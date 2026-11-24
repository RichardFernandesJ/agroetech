import { apiClient } from "./api";
import type { TalentEffect } from "./talent-service";

export interface BuildingLevel {
  level: number;
  cost: number;
  min_player_level: number;
  /** Total de talhões da fazenda neste nível (só a Casa da Fazenda). */
  plots: number | null;
  effects: TalentEffect[];
}

export interface Building {
  id: string;
  name: string;
  description: string;
  level: number;
  max_level: number;
  current: BuildingLevel | null;
  next: BuildingLevel | null;
  can_upgrade: boolean;
  blocked_reason: string | null;
}

export interface BuildingsState {
  property_id: string;
  plot_count: number;
  player_level: number;
  balance: number;
  buildings: Building[];
  replayed: boolean;
}

export const buildingService = {
  getState: (propertyId: string, token: string): Promise<BuildingsState> =>
    apiClient.get<BuildingsState>(`/properties/${propertyId}/buildings`, { token }),

  /** Cada clique usa uma chave nova; um reenvio acidental não cobra duas vezes. */
  upgrade: (propertyId: string, buildingId: string, token: string): Promise<BuildingsState> =>
    apiClient.post<BuildingsState>(
      `/properties/${propertyId}/buildings/${buildingId}/upgrade`,
      undefined,
      { token, headers: { "Idempotency-Key": crypto.randomUUID() } },
    ),
};
