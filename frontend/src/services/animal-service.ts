import { apiClient } from "./api";

export interface Animal {
  id: string;
  species: string;
  species_name: string;
  product_item: string;
  product_name: string;
  stored: number;
  max_stored: number;
  /** Tempo por produto e bônus de produção vigentes neste animal (talentos). */
  produce_seconds: number;
  yield_bonus_bp: number;
  is_fed: boolean;
  fed_seconds_left: number;
  /** Segundos até o próximo produto (null se está com fome ou com o estoque cheio). */
  seconds_to_next: number | null;
  fed_until: string | null;
}

export interface Housing {
  building_id: string;
  name: string;
  level: number;
  capacity: number;
  used: number;
}

export interface Species {
  id: string;
  name: string;
  description: string;
  housing: string;
  price: number;
  min_player_level: number;
  produce_seconds: number;
  product_item: string;
  product_name: string;
  sell_price: number;
  feed_item: string;
  feed_name: string;
  feed_seconds: number;
  max_feed_seconds: number;
  owned: number;
  can_buy: boolean;
  blocked_reason: string | null;
}

export interface AnimalsState {
  property_id: string;
  player_level: number;
  balance: number;
  animals: Animal[];
  housings: Housing[];
  species: Species[];
  replayed: boolean;
  products: Record<string, number>;
  units_fed: Record<string, number>;
  xp_gained: number;
}

export const animalService = {
  getState: (propertyId: string, token: string): Promise<AnimalsState> =>
    apiClient.get<AnimalsState>(`/properties/${propertyId}/animals`, { token }),

  /** Cada clique usa uma chave nova; um reenvio acidental não cobra duas vezes. */
  buy: (propertyId: string, species: string, token: string): Promise<AnimalsState> =>
    apiClient.post<AnimalsState>(
      `/properties/${propertyId}/animals/buy`,
      { species },
      { token, headers: { "Idempotency-Key": crypto.randomUUID() } },
    ),

  feed: (
    propertyId: string,
    animalId: string,
    units: number,
    token: string,
  ): Promise<AnimalsState> =>
    apiClient.post<AnimalsState>(
      `/properties/${propertyId}/animals/${animalId}/feed`,
      { units },
      { token },
    ),

  feedAll: (propertyId: string, units: number, token: string): Promise<AnimalsState> =>
    apiClient.post<AnimalsState>(`/properties/${propertyId}/animals/feed-all`, { units }, { token }),

  collect: (propertyId: string, token: string): Promise<AnimalsState> =>
    apiClient.post<AnimalsState>(`/properties/${propertyId}/animals/collect`, undefined, { token }),
};
