import { apiClient } from "./api";

export interface TalentEffect {
  stat: string;
  value_bp: number;
  scope: string | null;
}

export interface TalentNode {
  id: string;
  name: string;
  description: string;
  branch: string;
  tier: number;
  tier_name: string;
  cost: number;
  min_level: number;
  requires: string[];
  requires_any: string[];
  branch_points: Record<string, number>;
  exclusive_group: string | null;
  effects: TalentEffect[];
  x: number;
  y: number;
}

export interface TalentBranch {
  id: string;
  name: string;
  description: string;
  available: boolean;
  angle: number;
}

export interface TalentCatalog {
  center_x: number;
  center_y: number;
  branches: TalentBranch[];
  nodes: TalentNode[];
}

export interface TalentPreset {
  id: string;
  name: string;
  slot: number;
  is_active: boolean;
  node_ids: string[];
  points_spent: number;
  last_activated_at: string | null;
}

export interface TalentState {
  level: number;
  points_total: number;
  points_spent: number;
  points_available: number;
  preset_slots: number;
  presets: TalentPreset[];
  active_preset_id: string | null;
  switch_available_at: string | null;
  reset_cost: number;
  reset_is_free: boolean;
  build_locked: boolean;
  /** Totais de bônus do preset ativo, em pontos-base (10.000 = 100%). */
  modifiers: Record<string, number>;
}

export interface ResetResult {
  cost: number;
  state: TalentState;
}

export const talentService = {
  getCatalog: (): Promise<TalentCatalog> => apiClient.get<TalentCatalog>("/catalog/talents"),

  getState: (token: string): Promise<TalentState> =>
    apiClient.get<TalentState>("/talents", { token }),

  allocate: (nodeId: string, token: string): Promise<TalentState> =>
    apiClient.post<TalentState>("/talents/allocate", { node_id: nodeId }, { token }),

  reset: (token: string): Promise<ResetResult> =>
    apiClient.post<ResetResult>("/talents/reset", undefined, { token }),

  createPreset: (name: string, token: string): Promise<TalentState> =>
    apiClient.post<TalentState>("/talents/presets", { name }, { token }),

  renamePreset: (id: string, name: string, token: string): Promise<TalentState> =>
    apiClient.request<TalentState>(`/talents/presets/${id}`, {
      method: "PATCH",
      body: { name },
      token,
    }),

  deletePreset: (id: string, token: string): Promise<TalentState> =>
    apiClient.request<TalentState>(`/talents/presets/${id}`, { method: "DELETE", token }),

  activatePreset: (id: string, token: string): Promise<TalentState> =>
    apiClient.post<TalentState>(`/talents/presets/${id}/activate`, undefined, { token }),
};
