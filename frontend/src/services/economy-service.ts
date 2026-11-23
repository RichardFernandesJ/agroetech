import { apiClient } from "./api";

export interface Wallet {
  id: string;
  balance: number;
  currency: string;
}

export interface MarketOffer {
  item_id: string;
  name: string;
  category: string;
  buy_price: number | null;
  sell_price: number | null;
  /** Bônus de talentos sobre o preço de venda, em pontos-base (10.000 = 100%). */
  sell_bonus_bp: number;
}

export interface MarketOffers {
  currency: string;
  fee_basis_points: number;
  offers: MarketOffer[];
}

export interface TradeResult {
  kind: "seed_purchase" | "crop_sale";
  item_id: string;
  item_name: string;
  quantity: number;
  unit_price: number;
  gross: number;
  fee: number;
  amount: number;
  balance: number;
  replayed: boolean;
}

export interface LedgerEntry {
  id: string;
  kind: string;
  amount: number;
  balance_after: number;
  item_id: string | null;
  item_name: string | null;
  quantity: number | null;
  unit_price: number | null;
  fee: number;
  created_at: string;
}

export interface LedgerPage {
  entries: LedgerEntry[];
  limit: number;
  offset: number;
}

/** Chave única por clique: um reenvio acidental não repete a operação. */
function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

export const economyService = {
  getWallet: (token: string): Promise<Wallet> => apiClient.get<Wallet>("/wallet", { token }),

  getLedger: (token: string, limit = 20, offset = 0): Promise<LedgerPage> =>
    apiClient.get<LedgerPage>(`/wallet/ledger?limit=${limit}&offset=${offset}`, { token }),

  getOffers: (token: string): Promise<MarketOffers> =>
    apiClient.get<MarketOffers>("/market/offers", { token }),

  buy: (
    propertyId: string,
    payload: { item_id: string; quantity: number },
    token: string,
  ): Promise<TradeResult> =>
    apiClient.post<TradeResult>(`/properties/${propertyId}/market/buy`, payload, {
      token,
      headers: { "Idempotency-Key": newIdempotencyKey() },
    }),

  sell: (
    propertyId: string,
    payload: { item_id: string; quantity: number },
    token: string,
  ): Promise<TradeResult> =>
    apiClient.post<TradeResult>(`/properties/${propertyId}/market/sell`, payload, {
      token,
      headers: { "Idempotency-Key": newIdempotencyKey() },
    }),
};
