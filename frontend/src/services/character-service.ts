import { apiClient } from "./api";

export type SkinTone = "light" | "medium" | "dark" | "deep";
export type HairStyle = "short" | "long" | "bun" | "cap";
export type Facing = "up" | "down" | "left" | "right";

export interface CharacterAppearance {
  skin_tone: SkinTone;
  hair_style: HairStyle;
  outfit_color: string;
}

export interface Character {
  id: string;
  user_id: string;
  property_id: string;
  name: string;
  appearance: CharacterAppearance;
  position_x: number;
  position_y: number;
  facing: Facing;
  created_at: string;
}

export interface CreateCharacterPayload {
  name: string;
  property_id?: string;
  appearance?: Partial<CharacterAppearance>;
}

export interface CharacterPositionUpdate {
  x: number;
  y: number;
  facing: Facing;
}

export const characterService = {
  getMine: (token: string): Promise<Character> =>
    apiClient.get<Character>("/characters/me", { token }),

  create: (payload: CreateCharacterPayload, token: string): Promise<Character> =>
    apiClient.post<Character>("/characters", payload, { token }),

  updatePosition: (
    payload: CharacterPositionUpdate,
    token: string,
    keepalive = false,
  ): Promise<Character> =>
    apiClient.request<Character>("/characters/me/position", {
      method: "PATCH",
      body: payload,
      token,
      keepalive,
    }),
};
