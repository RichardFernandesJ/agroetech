import { ApiError } from "@/services/api-client";
import { economyService } from "@/services/economy-service";
import { propertyService, type InventoryItem } from "@/services/property-service";
import {
  tradeFee,
  tradeService,
  type Player,
  type TradeInfo,
  type TradeOffer,
  type TradeSide,
} from "@/services/trade-service";

import { formatDuration } from "./format";
import { PressGuard } from "./press-guard";
import { escapeHtml } from "./talents/talent-sidebar";

type Tab = "in" | "out" | "new";
type Side = "offer" | "request";

export interface TradeModalOptions {
  propertyId: string;
  token: string;
  /** Após aceitar, propor, recusar ou cancelar: o mundo atualiza inventário e saldo. */
  onChange: () => void;
  onClose: () => void;
}

interface DraftSide {
  lines: Map<string, number>;
  agc: number;
}

const AGC_STEPS = [-100, -10, -1, 1, 10, 100];
const STATUS_LABELS: Record<string, string> = {
  pending: "Pendente",
  accepted: "Aceita",
  declined: "Recusada",
  cancelled: "Cancelada",
  expired: "Expirada",
};

/**
 * Trocas diretas: propostas recebidas e enviadas, e o montador de uma nova troca.
 * Escolha de jogador, itens e valores é toda por botões; o servidor valida o equilíbrio.
 */
export class TradeModal {
  private readonly root: HTMLDivElement;
  private readonly guard: PressGuard;
  private readonly timer: number;
  private tab: Tab = "in";
  private info: TradeInfo | null = null;
  private offers: TradeOffer[] = [];
  private players: Player[] = [];
  private inventory: InventoryItem[] = [];
  private balance = 0;
  private query = "";
  private message = "";
  private busy = false;
  private destroyed = false;

  private recipient = "";
  private draft: Record<Side, DraftSide> = {
    offer: { lines: new Map(), agc: 0 },
    request: { lines: new Map(), agc: 0 },
  };

  constructor(private readonly options: TradeModalOptions) {
    this.root = document.createElement("div");
    this.root.className = "overlay";
    const layer = document.getElementById("ui-layer");
    (layer ?? document.body).append(this.root);
    this.root.addEventListener("click", (event) => {
      if (event.target === this.root) {
        this.options.onClose();
      }
    });
    this.guard = new PressGuard(this.root, () => this.render());

    this.render();
    void this.load();
    this.timer = window.setInterval(() => {
      if (!this.busy && this.tab !== "new") {
        void this.load();
      }
    }, 12_000);
  }

  destroy(): void {
    this.destroyed = true;
    this.guard.dispose();
    window.clearInterval(this.timer);
    this.root.remove();
  }

  // ---------------------------------------------------------------- dados
  private async load(): Promise<void> {
    const { token, propertyId } = this.options;
    try {
      const [info, offers, players, inventory, wallet] = await Promise.all([
        tradeService.getInfo(token),
        tradeService.list(token),
        tradeService.players(token, this.query),
        propertyService.getInventory(propertyId, token),
        economyService.getWallet(token),
      ]);
      this.info = info;
      this.offers = offers;
      this.players = players;
      this.inventory = inventory.items;
      this.balance = wallet.balance;
    } catch (error) {
      this.message = this.describe(error);
    }
    this.render();
  }

  private async run(action: () => Promise<string>): Promise<void> {
    if (this.busy) {
      return;
    }
    this.busy = true;
    this.message = "";
    this.render();
    try {
      this.message = await action();
      await this.load();
      this.options.onChange();
    } catch (error) {
      this.message = this.describe(error);
    } finally {
      this.busy = false;
      if (!this.destroyed) {
        this.render();
      }
    }
  }

  private describe(error: unknown): string {
    return error instanceof ApiError ? error.message : "Não foi possível falar com o servidor.";
  }

  // --------------------------------------------------------------- cálculos
  private valueOf(side: Side): number {
    const prices = new Map((this.info?.tradable ?? []).map((item) => [item.item_id, item.value]));
    let total = this.draft[side].agc;
    for (const [itemId, quantity] of this.draft[side].lines) {
      total += (prices.get(itemId) ?? 0) * quantity;
    }
    return total;
  }

  private stockOf(itemId: string): number {
    return this.inventory.find((item) => item.item_id === itemId)?.quantity ?? 0;
  }

  private draftProblem(): string | null {
    const offer = this.valueOf("offer");
    const request = this.valueOf("request");
    const feeBp = this.info?.fee_basis_points ?? 200;
    if (!this.recipient) return "Escolha com quem negociar.";
    if (offer <= 0 || request <= 0) return "Os dois lados precisam ter valor.";
    const [low, high] = offer < request ? [offer, request] : [request, offer];
    const ratio = this.info?.max_value_ratio ?? 3;
    if (high > low * ratio) return `Troca desigual: um lado vale mais de ${ratio}x o outro.`;
    for (const [itemId, quantity] of this.draft.offer.lines) {
      if (quantity > this.stockOf(itemId)) return "Você não tem tudo o que está oferecendo.";
    }
    if (this.draft.offer.agc + tradeFee(offer, feeBp) > this.balance) {
      return "Saldo insuficiente para o AGC oferecido e a taxa.";
    }
    return null;
  }

  // -------------------------------------------------------------- exibição
  private sideText(side: TradeSide): string {
    const parts = side.items.map((line) => `${line.quantity}× ${escapeHtml(line.name)}`);
    if (side.agc > 0) parts.push(`${side.agc} AGC`);
    return `${parts.join(" + ") || "—"} <small>(valor ${side.value})</small>`;
  }

  private offerCard(offer: TradeOffer): string {
    const pending = offer.status === "pending";
    const left = formatDuration((Date.parse(offer.expires_at) - Date.now()) / 1000);
    const incoming = offer.direction === "in";
    // Em uma proposta recebida, "oferece" é o que o outro dá a você e "pede" o que você entrega.
    const buttons = !pending
      ? ""
      : incoming
        ? `<button type="button" class="btn-trade" data-accept="${offer.id}" ${this.busy ? "disabled" : ""}>Aceitar</button>
           <button type="button" class="btn-trade" data-decline="${offer.id}" ${this.busy ? "disabled" : ""}>Recusar</button>`
        : `<button type="button" class="btn-trade" data-cancel="${offer.id}" ${this.busy ? "disabled" : ""}>Cancelar</button>`;
    return `
      <article class="trade-card status-${offer.status}">
        <div class="trade-card-head">
          <strong>${incoming ? "De" : "Para"} ${escapeHtml(offer.other_player)}</strong>
          <span class="trade-status">${STATUS_LABELS[offer.status] ?? offer.status}${pending ? ` · expira em ${left}` : ""}</span>
        </div>
        <p><span>${incoming ? "Você recebe:" : "Você oferece:"}</span> ${this.sideText(offer.offer)}</p>
        <p><span>${incoming ? "Você entrega:" : "Você pede:"}</span> ${this.sideText(offer.request)}</p>
        <p class="trade-note">Sua taxa: ${offer.your_fee} AGC ${incoming && pending ? "(cobrada ao aceitar)" : ""}</p>
        <div class="trade-actions">${buttons}</div>
      </article>`;
  }

  private listTab(direction: "in" | "out"): string {
    const rows = this.offers.filter((offer) => offer.direction === direction);
    if (rows.length === 0) {
      return `<p class="empty-list">${direction === "in" ? "Nenhuma proposta recebida." : "Você ainda não enviou propostas."}</p>`;
    }
    return `<div class="trade-cards">${rows.map((offer) => this.offerCard(offer)).join("")}</div>`;
  }

  private sideEditor(side: Side): string {
    const draft = this.draft[side];
    const items =
      side === "offer"
        ? this.inventory
            .filter((item) => item.quantity > 0 && this.info?.tradable.some((t) => t.item_id === item.item_id))
            .map((item) => ({ id: item.item_id, name: item.name, extra: `×${item.quantity}` }))
        : (this.info?.tradable ?? []).map((item) => ({ id: item.item_id, name: item.name, extra: `${item.value} AGC` }));
    const chips = items
      .map(
        (item) =>
          `<button type="button" class="chip" data-add="${side}:${item.id}">${escapeHtml(item.name)} <small>${item.extra}</small></button>`,
      )
      .join("");
    const lines = [...draft.lines.entries()]
      .map(
        ([itemId, quantity]) => `
        <div class="draft-line">
          <span>${escapeHtml(this.info?.tradable.find((t) => t.item_id === itemId)?.name ?? itemId)}</span>
          <button type="button" class="btn-trade" data-qty="${side}:${itemId}:-1" aria-label="Menos">−</button>
          <strong>${quantity}</strong>
          <button type="button" class="btn-trade" data-qty="${side}:${itemId}:1" aria-label="Mais">+</button>
          <button type="button" class="btn-trade" data-qty="${side}:${itemId}:-999" aria-label="Remover">✕</button>
        </div>`,
      )
      .join("");
    const agcButtons = AGC_STEPS.map(
      (step) => `<button type="button" class="btn-trade" data-agc="${side}:${step}">${step > 0 ? "+" : ""}${step}</button>`,
    ).join("");
    return `
      <section class="side-editor">
        <h4>${side === "offer" ? "Você oferece" : "Você pede"} <small>(valor ${this.valueOf(side)})</small></h4>
        <div class="chip-row">${chips}</div>
        ${lines || `<p class="trade-note">Clique em um item para adicioná-lo.</p>`}
        <div class="stepper"><span>AGC</span><strong data-testid="agc-${side}">${draft.agc}</strong>${agcButtons}</div>
      </section>`;
  }

  private newTab(): string {
    const problem = this.draftProblem();
    const offerValue = this.valueOf("offer");
    const feeBp = this.info?.fee_basis_points ?? 200;
    const full = (this.info?.pending_outgoing ?? 0) >= (this.info?.max_pending_outgoing ?? 5);
    const playerChips = this.players
      .map(
        (player) =>
          `<button type="button" class="chip ${this.recipient === player.username ? "active" : ""}" data-player="${escapeHtml(player.username)}">${escapeHtml(player.username)} <small>Nv ${player.level}</small></button>`,
      )
      .join("");
    return `
      <section class="side-editor">
        <h4>Com quem negociar</h4>
        <label class="field"><input type="search" data-testid="player-search" placeholder="Buscar jogador..." value="${escapeHtml(this.query)}" /></label>
        <div class="chip-row">${playerChips || `<span class="trade-note">Nenhum jogador de nível ${this.info?.min_level ?? 3}+ encontrado.</span>`}</div>
      </section>
      ${this.sideEditor("offer")}
      ${this.sideEditor("request")}
      <p class="sell-summary">Valor: você oferece <strong>${offerValue}</strong> · pede <strong>${this.valueOf("request")}</strong> ·
        sua taxa <strong>${tradeFee(offerValue, feeBp)} AGC</strong> (cobrada agora; devolvida se não houver troca)</p>
      ${problem ? `<p class="building-blocked">${escapeHtml(problem)}</p>` : ""}
      <button type="button" class="primary-button" data-action="send" ${problem || this.busy || full ? "disabled" : ""}>
        ${full ? "Limite de propostas pendentes atingido" : `Enviar proposta${this.recipient ? ` para ${escapeHtml(this.recipient)}` : ""}`}</button>
      <p class="trade-note">Seu lado fica em custódia por ${this.info?.expiry_hours ?? 24} h ou até a resposta.</p>`;
  }

  private render(): void {
    if (this.destroyed || this.guard.defer()) {
      return;
    }
    const incoming = this.offers.filter((o) => o.direction === "in" && o.status === "pending").length;
    const outgoing = this.offers.filter((o) => o.direction === "out" && o.status === "pending").length;
    const body = this.tab === "new" ? this.newTab() : this.listTab(this.tab);
    const tabButton = (tab: Tab, label: string) =>
      `<button type="button" class="tab ${this.tab === tab ? "active" : ""}" data-tab="${tab}" role="tab" aria-selected="${this.tab === tab}">${label}</button>`;
    const gate =
      this.info && this.info.player_level < this.info.min_level
        ? `<p class="market-message">As trocas exigem nível ${this.info.min_level} (você está no ${this.info.player_level}).</p>`
        : "";

    this.root.innerHTML = `
      <section class="panel exchange-panel" role="dialog" aria-modal="true" aria-labelledby="trade-title">
        <div class="panel-header">
          <div>
            <p class="eyebrow">Entre dois jogadores</p>
            <h2 id="trade-title">Trocas</h2>
          </div>
          <div class="market-balance" aria-label="Saldo">🪙 <strong>${this.balance}</strong> AGC</div>
          <button type="button" class="btn-close" aria-label="Fechar">✕</button>
        </div>
        ${gate}
        <div class="tabs" role="tablist">
          ${tabButton("in", `Recebidas (${incoming})`)}${tabButton("out", `Enviadas (${outgoing})`)}${tabButton("new", "Nova troca")}
        </div>
        <p class="market-message" role="status" ${this.message ? "" : "hidden"}>${escapeHtml(this.message)}</p>
        <div class="market-section">${body}</div>
      </section>`;
    this.bind();
  }

  private bind(): void {
    const { token } = this.options;
    const all = <T extends HTMLElement>(selector: string) => this.root.querySelectorAll<T>(selector);

    this.root.querySelector(".btn-close")?.addEventListener("click", () => this.options.onClose());
    all("[data-tab]").forEach((button) =>
      button.addEventListener("click", () => {
        this.tab = button.dataset.tab as Tab;
        this.message = "";
        this.render();
        void this.load();
      }),
    );

    const resolve = (attr: string, call: (id: string) => Promise<TradeOffer>, text: string) =>
      all(`[data-${attr}]`).forEach((button) =>
        button.addEventListener("click", () =>
          void this.run(async () => {
            await call(button.dataset[attr] ?? "");
            return text;
          }),
        ),
      );
    resolve("accept", (id) => tradeService.accept(id, token), "Troca concluída!");
    resolve("decline", (id) => tradeService.decline(id, token), "Proposta recusada.");
    resolve("cancel", (id) => tradeService.cancel(id, token), "Proposta cancelada e custódia devolvida.");

    // Montagem de uma nova troca
    all("[data-player]").forEach((button) =>
      button.addEventListener("click", () => {
        this.recipient = button.dataset.player ?? "";
        this.render();
      }),
    );
    const search = this.root.querySelector<HTMLInputElement>('[data-testid="player-search"]');
    search?.addEventListener("change", () => {
      this.query = search.value.trim();
      void this.load();
    });
    all("[data-add]").forEach((button) =>
      button.addEventListener("click", () => {
        const [side, itemId] = (button.dataset.add ?? "").split(":") as [Side, string];
        const lines = this.draft[side].lines;
        if (lines.size < (this.info?.max_item_lines ?? 4) || lines.has(itemId)) {
          lines.set(itemId, Math.min(999, (lines.get(itemId) ?? 0) + 1));
        }
        this.render();
      }),
    );
    all("[data-qty]").forEach((button) =>
      button.addEventListener("click", () => {
        const [side, itemId, delta] = (button.dataset.qty ?? "").split(":") as [Side, string, string];
        const lines = this.draft[side].lines;
        const next = (lines.get(itemId) ?? 0) + Number(delta);
        if (next <= 0) lines.delete(itemId);
        else lines.set(itemId, Math.min(999, next));
        this.render();
      }),
    );
    all("[data-agc]").forEach((button) =>
      button.addEventListener("click", () => {
        const [side, step] = (button.dataset.agc ?? "").split(":") as [Side, string];
        this.draft[side].agc = Math.min(1_000_000, Math.max(0, this.draft[side].agc + Number(step)));
        this.render();
      }),
    );
    this.root.querySelector('[data-action="send"]')?.addEventListener("click", () =>
      void this.run(async () => {
        const toLines = (side: Side) =>
          [...this.draft[side].lines.entries()].map(([item_id, quantity]) => ({ item_id, quantity }));
        const sent = await tradeService.propose(
          {
            recipient: this.recipient,
            offer_items: toLines("offer"),
            offer_agc: this.draft.offer.agc,
            request_items: toLines("request"),
            request_agc: this.draft.request.agc,
          },
          token,
        );
        this.draft = {
          offer: { lines: new Map(), agc: 0 },
          request: { lines: new Map(), agc: 0 },
        };
        this.tab = "out";
        return `Proposta enviada para ${sent.other_player}. Seu lado ficou em custódia.`;
      }),
    );
  }
}
