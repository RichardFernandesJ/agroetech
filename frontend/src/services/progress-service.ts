import { apiClient } from "./api";

export interface Progress {
  level: number;
  xp: number;
  xp_into_level: number;
  /** XP necessário neste nível para o próximo; null no nível máximo. */
  xp_for_next: number | null;
  max_level: number;
}

export const progressService = {
  get: (token: string): Promise<Progress> => apiClient.get<Progress>("/progress", { token }),
};
