import { apiClient } from "./api";

export interface PriceInfo {
  item_id: string;
  name: string;
  reference: number;
  minimum: number;
  maximum: number;
  /** Média das últimas negociações (null se ainda não houve). */
  last_price: number | null;
  lowest_listing: number | null;
}

export interface ExchangeInfo {
  currency: string;
  min_level: number;
  max_active_listings: number;
  listing_hours: number;
  /** Taxa que o vendedor paga, em pontos-base (500 = 5%). */
  fee_basis_points: number;
  player_level: number;
  active_listings: number;
  prices: PriceInfo[];
}

export interface Listing {
  id: string;
  seller_name: string;
  is_mine: boolean;
  item_id: string;
  item_name: string;
  quantity_initial: number;
  quantity_remaining: number;
  unit_price: number;
  status: "active" | "sold" | "cancelled" | "expired";
  expires_at: string;
  created_at: string;
}

export interface Trade {
  transaction_id: string;
  listing_id: string;
  item_id: string;
  item_name: string;
  quantity: number;
  unit_price: number;
  gross: number;
  fee: number;
  seller_net: number;
  balance: number;
  listing_remaining: number;
  listing_status: string;
  replayed: boolean;
}

export interface HistoryEntry {
  id: string;
  role: "buyer" | "seller";
  counterpart: string;
  item_id: string;
  item_name: string;
  quantity: number;
  unit_price: number;
  gross: number;
  fee: number;
  /** Variação do saldo: −bruto (compra) ou +líquido (venda). */
  amount: number;
  created_at: string;
}

/** Taxa do vendedor com arredondamento para cima (igual ao servidor). */
export function estimateFee(gross: number, feeBasisPoints: number): number {
  return gross > 0 ? Math.max(1, Math.ceil((gross * feeBasisPoints) / 10_000)) : 0;
}

export const exchangeService = {
  getInfo: (token: string): Promise<ExchangeInfo> =>
    apiClient.get<ExchangeInfo>("/exchange/info", { token }),

  browse: (token: string, itemId?: string): Promise<Listing[]> =>
    apiClient.get<Listing[]>(
      `/exchange/listings?sort=price&limit=60${itemId ? `&item_id=${encodeURIComponent(itemId)}` : ""}`,
      { token },
    ),

  mine: (token: string): Promise<Listing[]> =>
    apiClient.get<Listing[]>("/exchange/listings/mine", { token }),

  history: (token: string): Promise<HistoryEntry[]> =>
    apiClient.get<HistoryEntry[]>("/exchange/history?limit=40", { token }),

  /** Cada clique usa uma chave nova; um reenvio acidental não duplica o anúncio. */
  create: (
    payload: { item_id: string; quantity: number; unit_price: number },
    token: string,
  ): Promise<Listing> =>
    apiClient.post<Listing>("/exchange/listings", payload, {
      token,
      headers: { "Idempotency-Key": crypto.randomUUID() },
    }),

  buy: (listingId: string, quantity: number, token: string): Promise<Trade> =>
    apiClient.post<Trade>(
      `/exchange/listings/${listingId}/buy`,
      { quantity },
      { token, headers: { "Idempotency-Key": crypto.randomUUID() } },
    ),

  cancel: (listingId: string, token: string): Promise<Listing> =>
    apiClient.request<Listing>(`/exchange/listings/${listingId}`, { method: "DELETE", token }),
};
