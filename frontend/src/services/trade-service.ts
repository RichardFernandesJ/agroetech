import { apiClient } from "./api";

export interface TradeLine {
  item_id: string;
  name: string;
  quantity: number;
  value: number;
}

export interface TradeSide {
  items: TradeLine[];
  agc: number;
  /** Valor de referência (itens pelo preço do entreposto + AGC). */
  value: number;
}

export interface TradeOffer {
  id: string;
  direction: "in" | "out";
  other_player: string;
  status: "pending" | "accepted" | "declined" | "cancelled" | "expired";
  offer: TradeSide;
  request: TradeSide;
  /** Taxa que este jogador paga nesta troca. */
  your_fee: number;
  expires_at: string;
  created_at: string;
  resolved_at: string | null;
}

export interface TradableItem {
  item_id: string;
  name: string;
  value: number;
}

export interface TradeInfo {
  min_level: number;
  max_pending_outgoing: number;
  max_item_lines: number;
  expiry_hours: number;
  fee_basis_points: number;
  max_value_ratio: number;
  player_level: number;
  pending_outgoing: number;
  tradable: TradableItem[];
}

export interface Player {
  username: string;
  level: number;
}

export interface ProposePayload {
  recipient: string;
  offer_items: { item_id: string; quantity: number }[];
  offer_agc: number;
  request_items: { item_id: string; quantity: number }[];
  request_agc: number;
}

/** Mesma regra do servidor: taxa de 2% arredondada para cima (mínimo de 1 AGC). */
export function tradeFee(value: number, feeBasisPoints: number): number {
  return value > 0 ? Math.max(1, Math.ceil((value * feeBasisPoints) / 10_000)) : 0;
}

export const tradeService = {
  getInfo: (token: string): Promise<TradeInfo> => apiClient.get<TradeInfo>("/trades/info", { token }),

  players: (token: string, query = ""): Promise<Player[]> =>
    apiClient.get<Player[]>(`/trades/players?q=${encodeURIComponent(query)}`, { token }),

  list: (token: string): Promise<TradeOffer[]> => apiClient.get<TradeOffer[]>("/trades", { token }),

  /** Cada clique usa uma chave nova; um reenvio acidental não cria outra proposta. */
  propose: (payload: ProposePayload, token: string): Promise<TradeOffer> =>
    apiClient.post<TradeOffer>("/trades", payload, {
      token,
      headers: { "Idempotency-Key": crypto.randomUUID() },
    }),

  accept: (id: string, token: string): Promise<TradeOffer> =>
    apiClient.post<TradeOffer>(`/trades/${id}/accept`, undefined, { token }),

  decline: (id: string, token: string): Promise<TradeOffer> =>
    apiClient.post<TradeOffer>(`/trades/${id}/decline`, undefined, { token }),

  cancel: (id: string, token: string): Promise<TradeOffer> =>
    apiClient.post<TradeOffer>(`/trades/${id}/cancel`, undefined, { token }),
};
