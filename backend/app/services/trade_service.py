"""Trocas diretas: propor, aceitar, recusar, cancelar e expirar.

- **Custódia:** ao propor, os itens e o AGC do proponente (mais a taxa dele) saem da conta e ficam
  na proposta. Se não houver troca (recusa, cancelamento ou expiração), tudo volta.
- **Aceite atômico:** o destinatário entrega o lado dele (itens, AGC e a taxa dele) e recebe o
  lado do proponente, numa única transação. A proposta só sai de ``pending`` uma vez
  (atualização condicional), então aceitar e cancelar ao mesmo tempo nunca liquida duas vezes.
- **Ordem de travas:** sempre carteiras (por id de usuário) e só depois a proposta. Como a
  carteira funciona como trava por jogador, duas operações que envolvam o mesmo jogador nunca
  se bloqueiam mutuamente.
"""

import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.core.time import ensure_utc, utcnow
from app.game.catalog import get_item
from app.game.exchange import reference_prices
from app.game.trade import (
    EXPIRY_HOURS,
    MAX_AGC,
    MAX_ITEM_LINES,
    MAX_ITEM_QUANTITY,
    MAX_PENDING_OUTGOING,
    SIDE_OFFER,
    SIDE_REQUEST,
    STATUS_ACCEPTED,
    STATUS_CANCELLED,
    STATUS_DECLINED,
    STATUS_EXPIRED,
    STATUS_PENDING,
    TRADE_FEE_BP,
    TRADE_MIN_LEVEL,
    ratio_ok,
    side_value,
    trade_fee,
)
from app.models.property import Property
from app.models.trade import TradeItem, TradeOffer
from app.models.user import User
from app.repositories.trade_repository import TradeRepository
from app.repositories.user_repository import UserRepository
from app.services.inventory_service import InventoryService
from app.services.progress_service import ProgressService
from app.services.property_service import PropertyService
from app.services.wallet_service import WalletService

KIND_ESCROW = "trade_escrow"
KIND_REFUND = "trade_refund"
KIND_PAID = "trade_paid"
KIND_RECEIVED = "trade_received"

Lines = list[tuple[str, int]]


def _name(item_id: str) -> str:
    item = get_item(item_id)
    return item.name if item else item_id


@dataclass(frozen=True, slots=True)
class OfferView:
    offer: TradeOffer
    direction: str  # "in" (recebida) | "out" (enviada)
    other_player: str
    offer_items: Lines
    request_items: Lines
    offer_value: int
    request_value: int
    # O que este jogador paga/entrega nesta troca, em AGC, incluindo a taxa dele.
    your_fee: int


@dataclass(frozen=True, slots=True)
class PlayerView:
    username: str
    level: int


@dataclass(slots=True)
class TradeInfo:
    min_level: int
    max_pending: int
    max_lines: int
    expiry_hours: int
    fee_basis_points: int
    max_ratio: int
    player_level: int
    pending_outgoing: int
    tradable: list[tuple[str, str, int]] = field(default_factory=list)  # id, nome, valor


class TradeService:
    def __init__(
        self,
        trades: TradeRepository,
        users: UserRepository,
        inventory: InventoryService,
        properties: PropertyService,
        progress: ProgressService,
        wallets: WalletService,
    ) -> None:
        self.trades = trades
        self.users = users
        self.inventory = inventory
        self.properties = properties
        self.progress = progress
        self.wallets = wallets

    # ------------------------------------------------------------- consultas
    async def info(self, user: User) -> TradeInfo:
        await self.sweep_expired(user_id=user.id)
        prices = reference_prices()
        return TradeInfo(
            min_level=TRADE_MIN_LEVEL,
            max_pending=MAX_PENDING_OUTGOING,
            max_lines=MAX_ITEM_LINES,
            expiry_hours=EXPIRY_HOURS,
            fee_basis_points=TRADE_FEE_BP,
            max_ratio=3,
            player_level=(await self.progress.describe(user.id)).level,
            pending_outgoing=await self.trades.count_pending_outgoing(user.id, utcnow()),
            tradable=[(item_id, _name(item_id), price) for item_id, price in prices.items()],
        )

    async def players(self, user: User, query: str) -> list[PlayerView]:
        rows = await self.trades.search_players(query.strip(), exclude=user.id, limit=12)
        views = []
        for row in rows:
            level = (await self.progress.describe(row.id)).level
            if level >= TRADE_MIN_LEVEL:
                views.append(PlayerView(row.username, level))
        return views

    async def mine(self, user: User) -> list[OfferView]:
        await self.sweep_expired(user_id=user.id)
        offers = await self.trades.list_for_user(user.id)
        items = await self.trades.items_of([offer.id for offer in offers])
        names: dict[uuid.UUID, str] = {}
        views: list[OfferView] = []
        for offer in offers:
            direction = "out" if offer.proposer_id == user.id else "in"
            other_id = offer.recipient_id if direction == "out" else offer.proposer_id
            if other_id not in names:
                other = await self.users.get_by_id(other_id)
                names[other_id] = other.username if other else "?"
            offer_items = [
                (i.item_id, i.quantity)
                for i in items
                if i.offer_id == offer.id and i.side == SIDE_OFFER
            ]
            request_items = [
                (i.item_id, i.quantity)
                for i in items
                if i.offer_id == offer.id and i.side == SIDE_REQUEST
            ]
            offer_value = side_value(offer_items, offer.offer_agc)
            request_value = side_value(request_items, offer.request_agc)
            views.append(
                OfferView(
                    offer=offer,
                    direction=direction,
                    other_player=names[other_id],
                    offer_items=offer_items,
                    request_items=request_items,
                    offer_value=offer_value,
                    request_value=request_value,
                    your_fee=trade_fee(offer_value if direction == "out" else request_value),
                )
            )
        return views

    # ---------------------------------------------------------------- propor
    async def propose(
        self,
        user: User,
        recipient_username: str,
        offer_items: Lines,
        offer_agc: int,
        request_items: Lines,
        request_agc: int,
        idempotency_key: str | None,
    ) -> TradeOffer:
        await self._require_level(user)
        recipient = await self.users.get_by_username(recipient_username.strip().lower())
        if recipient is None or not recipient.is_active:
            raise NotFoundError("Jogador não encontrado.")
        if recipient.id == user.id:
            raise GameRuleError("Você não pode negociar consigo mesmo.")
        if (await self.progress.describe(recipient.id)).level < TRADE_MIN_LEVEL:
            raise GameRuleError(f"Este jogador ainda não pode negociar (nível {TRADE_MIN_LEVEL}).")

        offer_items = self._validate_lines(offer_items, "oferecidos")
        request_items = self._validate_lines(request_items, "pedidos")
        for amount in (offer_agc, request_agc):
            if not 0 <= amount <= MAX_AGC:
                raise GameRuleError(f"O AGC de cada lado vai de 0 a {MAX_AGC}.")
        offer_value = side_value(offer_items, offer_agc)
        request_value = side_value(request_items, request_agc)
        if offer_value <= 0 or request_value <= 0:
            raise GameRuleError("Os dois lados da troca precisam ter valor (nada de presentes).")
        if not ratio_ok(offer_value, request_value):
            raise GameRuleError(
                f"Troca desigual: o lado maior pode valer no máximo 3x o menor "
                f"({offer_value} contra {request_value} AGC pelos valores de referência)."
            )

        if idempotency_key is not None:
            existing = await self.trades.find_by_key(user.id, idempotency_key)
            if existing is not None:
                if (existing.recipient_id, existing.offer_agc, existing.request_agc) != (
                    recipient.id,
                    offer_agc,
                    request_agc,
                ):
                    raise ConflictError(
                        "Esta chave de idempotência já foi usada em outra proposta."
                    )
                return existing

        property_ = await self._property_of(user)
        wallet = await self.wallets.get_locked(user.id)
        now = utcnow()
        if await self.trades.count_pending_outgoing(user.id, now) >= MAX_PENDING_OUTGOING:
            raise GameRuleError(f"Limite de {MAX_PENDING_OUTGOING} propostas pendentes atingido.")

        fee = trade_fee(offer_value)
        # Custódia: itens (débito atômico) e AGC com a taxa. Falta de saldo ou estoque desfaz tudo.
        for item_id, quantity in offer_items:
            await self.inventory.consume(
                property_.id, item_id, quantity, label=_name(item_id).lower()
            )
        if offer_agc + fee > 0:
            await self.wallets.apply(wallet, kind=KIND_ESCROW, amount=-(offer_agc + fee), fee=fee)

        offer = await self.trades.add(
            TradeOffer(
                proposer_id=user.id,
                recipient_id=recipient.id,
                proposer_property_id=property_.id,
                status=STATUS_PENDING,
                offer_agc=offer_agc,
                request_agc=request_agc,
                proposer_fee=fee,
                expires_at=now + timedelta(hours=EXPIRY_HOURS),
                request_key=idempotency_key,
            )
        )
        await self.trades.add_items(
            [
                *[
                    TradeItem(offer_id=offer.id, side=SIDE_OFFER, item_id=i, quantity=q)
                    for i, q in offer_items
                ],
                *[
                    TradeItem(offer_id=offer.id, side=SIDE_REQUEST, item_id=i, quantity=q)
                    for i, q in request_items
                ],
            ]
        )
        return offer

    # ----------------------------------------------------------------- aceitar
    async def accept(self, user: User, offer_id: uuid.UUID) -> TradeOffer:
        await self._require_level(user)
        preview = await self.trades.get_offer(offer_id)
        if preview is None or preview.recipient_id != user.id:
            raise NotFoundError("Proposta não encontrada.")

        wallets = {}
        for user_id in sorted({user.id, preview.proposer_id}, key=str):
            wallets[user_id] = await self.wallets.get_locked(user_id)
        recipient_wallet, proposer_wallet = wallets[user.id], wallets[preview.proposer_id]

        offer = await self.trades.get_offer(offer_id, for_update=True)
        assert offer is not None
        now = utcnow()
        if offer.status != STATUS_PENDING or ensure_utc(offer.expires_at) <= now:
            raise GameRuleError("Esta proposta não está mais disponível.")
        if not await self.trades.try_transition(offer.id, STATUS_ACCEPTED, now):
            raise GameRuleError("Esta proposta acabou de ser encerrada.")

        items = await self.trades.items_of([offer.id])
        offer_items = [(i.item_id, i.quantity) for i in items if i.side == SIDE_OFFER]
        request_items = [(i.item_id, i.quantity) for i in items if i.side == SIDE_REQUEST]
        recipient_property = await self._property_of(user)
        fee = trade_fee(side_value(request_items, offer.request_agc))

        # O destinatário entrega o lado dele (qualquer falta desfaz a transação inteira).
        for item_id, quantity in request_items:
            await self.inventory.consume(
                recipient_property.id, item_id, quantity, label=_name(item_id).lower()
            )
        if offer.request_agc + fee > 0:
            await self.wallets.apply(
                recipient_wallet, kind=KIND_PAID, amount=-(offer.request_agc + fee), fee=fee
            )
        if offer.request_agc > 0:
            await self.wallets.apply(proposer_wallet, kind=KIND_RECEIVED, amount=offer.request_agc)
        if offer.offer_agc > 0:
            await self.wallets.apply(recipient_wallet, kind=KIND_RECEIVED, amount=offer.offer_agc)

        # Cada lado recebe os itens do outro.
        for item_id, quantity in request_items:
            await self.inventory.add(offer.proposer_property_id, item_id, quantity)
        for item_id, quantity in offer_items:
            await self.inventory.add(recipient_property.id, item_id, quantity)
        await self.trades.session.refresh(offer)
        return offer

    # --------------------------------------------------- recusar/cancelar/expirar
    async def decline(self, user: User, offer_id: uuid.UUID) -> TradeOffer:
        preview = await self.trades.get_offer(offer_id)
        if preview is None or preview.recipient_id != user.id:
            raise NotFoundError("Proposta não encontrada.")
        return await self._resolve(preview, STATUS_DECLINED)

    async def cancel(self, user: User, offer_id: uuid.UUID) -> TradeOffer:
        preview = await self.trades.get_offer(offer_id)
        if preview is None or preview.proposer_id != user.id:
            raise NotFoundError("Proposta não encontrada.")
        return await self._resolve(preview, STATUS_CANCELLED)

    async def sweep_expired(self, *, user_id: uuid.UUID | None = None, limit: int = 30) -> int:
        """Devolve a custódia de propostas vencidas (sob demanda, sem processo em segundo plano)."""
        due = await self.trades.due_for_expiry(utcnow(), user_id=user_id, limit=limit)
        closed = 0
        for offer in due:
            try:
                await self._resolve(offer, STATUS_EXPIRED)
                closed += 1
            except GameRuleError:
                continue  # outra requisição já resolveu esta proposta
        return closed

    async def _resolve(self, preview: TradeOffer, new_status: str) -> TradeOffer:
        """Encerra sem troca e devolve a custódia ao proponente."""
        wallet = await self.wallets.get_locked(preview.proposer_id)
        offer = await self.trades.get_offer(preview.id, for_update=True)
        assert offer is not None
        if not await self.trades.try_transition(offer.id, new_status, utcnow()):
            raise GameRuleError("Esta proposta já foi encerrada.")

        items = await self.trades.items_of([offer.id])
        for item in items:
            if item.side == SIDE_OFFER:
                await self.inventory.add(offer.proposer_property_id, item.item_id, item.quantity)
        refund = offer.offer_agc + offer.proposer_fee
        if refund > 0:
            await self.wallets.apply(wallet, kind=KIND_REFUND, amount=refund)
        await self.trades.session.refresh(offer)
        return offer

    # --------------------------------------------------------------- internos
    def _validate_lines(self, lines: Lines, label: str) -> Lines:
        if len(lines) > MAX_ITEM_LINES:
            raise GameRuleError(f"No máximo {MAX_ITEM_LINES} tipos de item entre os {label}.")
        prices = reference_prices()
        seen: set[str] = set()
        for item_id, quantity in lines:
            if item_id not in prices:
                raise GameRuleError("Há itens que não podem ser negociados entre jogadores.")
            if item_id in seen:
                raise GameRuleError("Cada item aparece uma vez por lado; some as quantidades.")
            seen.add(item_id)
            if not 1 <= quantity <= MAX_ITEM_QUANTITY:
                raise GameRuleError(f"Escolha de 1 a {MAX_ITEM_QUANTITY} unidades por item.")
        return lines

    async def _require_level(self, user: User) -> None:
        if (await self.progress.describe(user.id)).level < TRADE_MIN_LEVEL:
            raise GameRuleError(f"As trocas exigem nível {TRADE_MIN_LEVEL}.")

    async def _property_of(self, user: User) -> Property:
        owned = await self.properties.list_owned(user.id)
        if not owned:
            raise GameRuleError("Crie sua fazenda antes de negociar.")
        return owned[0]
