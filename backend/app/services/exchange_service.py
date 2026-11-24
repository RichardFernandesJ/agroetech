"""Mercado entre jogadores: anunciar, comprar, cancelar e histórico comercial.

Princípios (AGENTS.md §7): o servidor define tudo, nada duplica, tudo é atômico.

- **Custódia:** ao anunciar, os itens saem do inventário (débito atômico) e ficam no anúncio;
  voltam ao vendedor se o anúncio for cancelado ou expirar.
- **Compra:** o comprador paga o bruto; o vendedor recebe o bruto menos a taxa (que sai da
  economia); os itens vão para o inventário do comprador. As duas carteiras são travadas em
  ordem fixa (sem deadlock) e o estoque do anúncio só diminui se ainda houver (atualização
  condicional), então duas compras simultâneas nunca vendem a mesma unidade duas vezes.
- **Preço:** livre dentro de uma faixa em torno do valor de referência do NPC (anti-inflação).
"""

import uuid
from dataclasses import dataclass, field
from datetime import timedelta

from app.core.exceptions import ConflictError, GameRuleError, NotFoundError
from app.core.time import ensure_utc, utcnow
from app.game.catalog import get_item
from app.game.economy import SALE_FEE_BASIS_POINTS
from app.game.exchange import (
    LISTING_HOURS,
    MAX_ACTIVE_LISTINGS,
    MAX_QUANTITY,
    MIN_LEVEL,
    STATUS_ACTIVE,
    STATUS_CANCELLED,
    STATUS_EXPIRED,
    p2p_fee,
    price_bounds,
    reference_prices,
)
from app.game.modifiers import Stat, effective_fee_bp
from app.models.exchange import MarketListing, MarketTransaction
from app.models.property import Property
from app.models.user import User
from app.repositories.exchange_repository import ExchangeRepository
from app.repositories.user_repository import UserRepository
from app.services.inventory_service import InventoryService
from app.services.modifier_service import ModifierService
from app.services.progress_service import ProgressService
from app.services.property_service import PropertyService
from app.services.wallet_service import WalletService

KIND_PURCHASE = "p2p_purchase"
KIND_SALE = "p2p_sale"


def _item_name(item_id: str) -> str:
    item = get_item(item_id)
    return item.name if item else item_id


@dataclass(frozen=True, slots=True)
class ListingView:
    listing: MarketListing
    seller_name: str
    item_name: str
    is_mine: bool


@dataclass(frozen=True, slots=True)
class PriceInfo:
    item_id: str
    name: str
    reference: int
    minimum: int
    maximum: int
    last_price: int | None  # média das últimas negociações
    lowest_listing: int | None


@dataclass(frozen=True, slots=True)
class ExchangeInfo:
    min_level: int
    max_active_listings: int
    listing_hours: int
    fee_basis_points: int
    player_level: int
    active_listings: int
    prices: list[PriceInfo]


@dataclass(frozen=True, slots=True)
class TradeResult:
    transaction: MarketTransaction
    listing: MarketListing
    balance: int
    replayed: bool = False


@dataclass(slots=True)
class HistoryView:
    transaction: MarketTransaction
    role: str  # "buyer" | "seller"
    counterpart: str
    item_name: str


@dataclass(slots=True)
class MyListings:
    listings: list[ListingView] = field(default_factory=list)


class ExchangeService:
    def __init__(
        self,
        exchange: ExchangeRepository,
        users: UserRepository,
        inventory: InventoryService,
        properties: PropertyService,
        progress: ProgressService,
        wallets: WalletService,
        modifiers: ModifierService,
    ) -> None:
        self.exchange = exchange
        self.users = users
        self.inventory = inventory
        self.properties = properties
        self.progress = progress
        self.wallets = wallets
        self.modifiers = modifiers

    # -------------------------------------------------------------- consultas
    async def info(self, user: User) -> ExchangeInfo:
        await self.sweep_expired()
        now = utcnow()
        prices: list[PriceInfo] = []
        for item_id in reference_prices():
            low, reference, high = price_bounds(item_id) or (0, 0, 0)
            recent = await self.exchange.recent_prices(item_id, 5)
            prices.append(
                PriceInfo(
                    item_id=item_id,
                    name=_item_name(item_id),
                    reference=reference,
                    minimum=low,
                    maximum=high,
                    last_price=round(sum(recent) / len(recent)) if recent else None,
                    lowest_listing=await self.exchange.lowest_listing(item_id, now),
                )
            )
        fee_bp = await self._fee_bp_for(user)
        return ExchangeInfo(
            min_level=MIN_LEVEL,
            max_active_listings=MAX_ACTIVE_LISTINGS,
            listing_hours=LISTING_HOURS,
            fee_basis_points=fee_bp,
            player_level=(await self.progress.describe(user.id)).level,
            active_listings=await self.exchange.count_active(user.id, now),
            prices=prices,
        )

    async def browse(
        self,
        user: User,
        *,
        item_id: str | None,
        newest_first: bool,
        limit: int,
        offset: int,
    ) -> list[ListingView]:
        await self.sweep_expired()
        rows = await self.exchange.browse(
            utcnow(), item_id=item_id, newest_first=newest_first, limit=limit, offset=offset
        )
        return [
            ListingView(listing, seller, _item_name(listing.item_id), listing.seller_id == user.id)
            for listing, seller in rows
        ]

    async def my_listings(self, user: User) -> list[ListingView]:
        await self.sweep_expired(seller_id=user.id)
        return [
            ListingView(listing, user.username, _item_name(listing.item_id), True)
            for listing in await self.exchange.list_by_seller(user.id)
        ]

    async def history(self, user: User, *, limit: int, offset: int) -> list[HistoryView]:
        rows = await self.exchange.history(user.id, limit=limit, offset=offset)
        names: dict[uuid.UUID, str] = {}

        async def name_of(user_id: uuid.UUID) -> str:
            if user_id not in names:
                other = await self.users.get_by_id(user_id)
                names[user_id] = other.username if other else "?"
            return names[user_id]

        views: list[HistoryView] = []
        for transaction in rows:
            as_buyer = transaction.buyer_id == user.id
            counterpart = await name_of(transaction.seller_id if as_buyer else transaction.buyer_id)
            views.append(
                HistoryView(
                    transaction,
                    "buyer" if as_buyer else "seller",
                    counterpart,
                    _item_name(transaction.item_id),
                )
            )
        return views

    # ---------------------------------------------------------------- anunciar
    async def create_listing(
        self,
        user: User,
        item_id: str,
        quantity: int,
        unit_price: int,
        idempotency_key: str | None,
    ) -> MarketListing:
        await self._require_level(user)
        bounds = price_bounds(item_id)
        if bounds is None:
            raise GameRuleError("Este item não pode ser negociado entre jogadores.")
        low, _, high = bounds
        if not 1 <= quantity <= MAX_QUANTITY:
            raise GameRuleError(f"Escolha de 1 a {MAX_QUANTITY} unidades.")
        if not low <= unit_price <= high:
            raise GameRuleError(
                f"Preço fora da faixa permitida para {_item_name(item_id)}: de {low} a {high} AGC."
            )

        if idempotency_key is not None:
            existing = await self.exchange.find_by_key(user.id, idempotency_key)
            if existing is not None:
                if (existing.item_id, existing.quantity_initial, existing.unit_price) != (
                    item_id,
                    quantity,
                    unit_price,
                ):
                    raise ConflictError("Esta chave de idempotência já foi usada em outro anúncio.")
                return existing

        property_ = await self._property_of(user)
        await self.exchange.lock_seller_property(property_.id)
        now = utcnow()
        if await self.exchange.count_active(user.id, now) >= MAX_ACTIVE_LISTINGS:
            raise GameRuleError(f"Limite de {MAX_ACTIVE_LISTINGS} anúncios ativos atingido.")

        # Custódia: débito atômico do inventário (falha sem efeito se faltar estoque).
        await self.inventory.consume(
            property_.id, item_id, quantity, label=_item_name(item_id).lower()
        )
        return await self.exchange.add(
            MarketListing(
                seller_id=user.id,
                seller_property_id=property_.id,
                item_id=item_id,
                quantity_initial=quantity,
                quantity_remaining=quantity,
                unit_price=unit_price,
                status=STATUS_ACTIVE,
                expires_at=now + timedelta(hours=LISTING_HOURS),
                request_key=idempotency_key,
            )
        )

    # ------------------------------------------------------------------ cancelar
    async def cancel(self, user: User, listing_id: uuid.UUID) -> MarketListing:
        listing = await self.exchange.get_listing(listing_id, for_update=True)
        if listing is None or listing.seller_id != user.id:
            raise NotFoundError("Anúncio não encontrado.")
        if listing.status != STATUS_ACTIVE:
            raise GameRuleError("Este anúncio já foi encerrado.")
        await self._close_and_return(listing, STATUS_CANCELLED)
        return listing

    async def sweep_expired(self, *, seller_id: uuid.UUID | None = None, limit: int = 50) -> int:
        """Devolve ao vendedor os itens de anúncios vencidos (feito sob demanda, sem processo)."""
        due = await self.exchange.due_for_expiry(utcnow(), seller_id=seller_id, limit=limit)
        closed = 0
        for listing in due:
            if await self._close_and_return(listing, STATUS_EXPIRED):
                closed += 1
        return closed

    async def _close_and_return(self, listing: MarketListing, new_status: str) -> bool:
        if not await self.exchange.try_close(listing.id, new_status):
            return False  # outra requisição já encerrou (e devolveu) este anúncio
        await self.exchange.session.refresh(listing)
        if listing.quantity_remaining > 0:
            await self.inventory.add(
                listing.seller_property_id, listing.item_id, listing.quantity_remaining
            )
        return True

    # -------------------------------------------------------------------- comprar
    async def buy(
        self,
        user: User,
        listing_id: uuid.UUID,
        quantity: int,
        idempotency_key: str | None,
    ) -> TradeResult:
        await self._require_level(user)
        preview = await self.exchange.get_listing(listing_id)
        if preview is None:
            raise NotFoundError("Anúncio não encontrado.")
        if preview.seller_id == user.id:
            raise GameRuleError("Você não pode comprar o próprio anúncio.")

        # Carteiras travadas em ordem fixa de usuário: dois cruzamentos nunca se bloqueiam.
        wallets = {}
        for user_id in sorted({user.id, preview.seller_id}, key=str):
            wallets[user_id] = await self.wallets.get_locked(user_id)
        buyer_wallet, seller_wallet = wallets[user.id], wallets[preview.seller_id]

        if idempotency_key is not None:
            existing = await self.exchange.find_transaction_by_key(user.id, idempotency_key)
            if existing is not None:
                if (existing.listing_id, existing.quantity) != (preview.id, quantity):
                    raise ConflictError("Esta chave de idempotência já foi usada em outra compra.")
                await self.exchange.session.refresh(preview)
                return TradeResult(existing, preview, buyer_wallet.balance, replayed=True)

        listing = await self.exchange.get_listing(listing_id, for_update=True)
        assert listing is not None
        now = utcnow()
        if listing.status != STATUS_ACTIVE or ensure_utc(listing.expires_at) <= now:
            raise GameRuleError("Este anúncio não está mais disponível.")
        if not 1 <= quantity <= listing.quantity_remaining:
            raise GameRuleError(f"Restam {listing.quantity_remaining} unidades neste anúncio.")

        buyer_property = await self._property_of(user)
        gross = listing.unit_price * quantity
        fee = p2p_fee(gross, await self._fee_bp(listing.seller_id, listing.seller_property_id))
        net = gross - fee

        await self.wallets.apply(
            buyer_wallet,
            kind=KIND_PURCHASE,
            amount=-gross,
            item_id=listing.item_id,
            quantity=quantity,
            unit_price=listing.unit_price,
        )
        if not await self.exchange.try_take(listing.id, quantity, now):
            raise GameRuleError("Este anúncio acabou de ser vendido.")
        await self.wallets.apply(
            seller_wallet,
            kind=KIND_SALE,
            amount=net,
            item_id=listing.item_id,
            quantity=quantity,
            unit_price=listing.unit_price,
            fee=fee,
        )
        await self.inventory.add(buyer_property.id, listing.item_id, quantity)
        transaction = await self.exchange.add_transaction(
            MarketTransaction(
                listing_id=listing.id,
                buyer_id=user.id,
                seller_id=listing.seller_id,
                item_id=listing.item_id,
                quantity=quantity,
                unit_price=listing.unit_price,
                gross=gross,
                fee=fee,
                seller_net=net,
                request_key=idempotency_key,
            )
        )
        await self.exchange.session.refresh(listing)
        return TradeResult(transaction, listing, buyer_wallet.balance)

    # ------------------------------------------------------------------ internos
    async def _require_level(self, user: User) -> None:
        level = (await self.progress.describe(user.id)).level
        if level < MIN_LEVEL:
            raise GameRuleError(f"O mercado entre jogadores exige nível {MIN_LEVEL}.")

    async def _property_of(self, user: User) -> Property:
        owned = await self.properties.list_owned(user.id)
        if not owned:
            raise GameRuleError("Crie sua fazenda antes de negociar.")
        return owned[0]

    async def _fee_bp(self, seller_id: uuid.UUID, seller_property_id: uuid.UUID) -> int:
        modifiers = await self.modifiers.for_property(seller_id, seller_property_id)
        return effective_fee_bp(SALE_FEE_BASIS_POINTS, modifiers.total_bp(Stat.MARKET_FEE))

    async def _fee_bp_for(self, user: User) -> int:
        owned = await self.properties.list_owned(user.id)
        if not owned:
            return SALE_FEE_BASIS_POINTS
        return await self._fee_bp(user.id, owned[0].id)
