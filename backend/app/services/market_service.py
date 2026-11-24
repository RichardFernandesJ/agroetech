"""Entreposto NPC: compra de sementes e venda de safras.

Os preços vêm sempre do servidor (catálogo). A operação inteira (saldo,
inventário e livro-razão) acontece na transação da requisição: qualquer erro
desfaz tudo, e a chave de idempotência impede que um reenvio repita o efeito.
"""

import uuid
from dataclasses import dataclass

from app.core.exceptions import ConflictError, GameRuleError
from app.game.catalog import get_item, sell_scope_for_item
from app.game.economy import SALE_FEE_BASIS_POINTS, product_prices, sale_fee, seed_prices
from app.game.modifiers import BP, Stat, effective_fee_bp
from app.models.user import User
from app.models.wallet import Wallet, WalletLedgerEntry
from app.services.inventory_service import InventoryService
from app.services.modifier_service import ModifierService
from app.services.property_service import PropertyService
from app.services.wallet_service import WalletService

KIND_PURCHASE = "seed_purchase"
KIND_SALE = "crop_sale"


@dataclass(frozen=True, slots=True)
class TradeResult:
    entry: WalletLedgerEntry
    balance: int
    replayed: bool


class MarketService:
    def __init__(
        self,
        properties: PropertyService,
        inventory: InventoryService,
        wallets: WalletService,
        modifiers: ModifierService,
    ) -> None:
        self.properties = properties
        self.inventory = inventory
        self.wallets = wallets
        self.modifiers = modifiers

    async def buy_seeds(
        self,
        user: User,
        property_id: uuid.UUID,
        item_id: str,
        quantity: int,
        idempotency_key: str | None,
    ) -> TradeResult:
        await self.properties.get_owned(property_id, user.id)
        unit_price = seed_prices().get(item_id)
        if unit_price is None:
            raise GameRuleError("Este item não está à venda no entreposto.")

        wallet = await self.wallets.get_locked(user.id)
        replay = await self._replay(wallet, KIND_PURCHASE, item_id, quantity, idempotency_key)
        if replay is not None:
            return replay

        entry = await self.wallets.apply(
            wallet,
            kind=KIND_PURCHASE,
            amount=-(unit_price * quantity),
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            idempotency_key=idempotency_key,
        )
        await self.inventory.add(property_id, item_id, quantity)
        return TradeResult(entry=entry, balance=wallet.balance, replayed=False)

    async def sell_products(
        self,
        user: User,
        property_id: uuid.UUID,
        item_id: str,
        quantity: int,
        idempotency_key: str | None,
    ) -> TradeResult:
        await self.properties.get_owned(property_id, user.id)
        unit_price = product_prices().get(item_id)
        if unit_price is None:
            raise GameRuleError("O entreposto não compra este item.")

        wallet = await self.wallets.get_locked(user.id)
        replay = await self._replay(wallet, KIND_SALE, item_id, quantity, idempotency_key)
        if replay is not None:
            return replay

        definition = get_item(item_id)
        await self.inventory.consume(
            property_id,
            item_id,
            quantity,
            label=definition.name if definition else item_id,
        )

        # Talentos: bônus no preço (por cultura) e redução da taxa, com tetos no motor.
        modifiers = await self.modifiers.for_property(user.id, property_id)
        price_bp = modifiers.total_bp(Stat.SELL_PRICE, sell_scope_for_item(item_id))
        fee_bp = effective_fee_bp(SALE_FEE_BASIS_POINTS, modifiers.total_bp(Stat.MARKET_FEE))
        gross = unit_price * quantity * (BP + price_bp) // BP
        fee = sale_fee(gross, fee_bp)
        entry = await self.wallets.apply(
            wallet,
            kind=KIND_SALE,
            amount=gross - fee,
            item_id=item_id,
            quantity=quantity,
            unit_price=unit_price,
            fee=fee,
            idempotency_key=idempotency_key,
        )
        return TradeResult(entry=entry, balance=wallet.balance, replayed=False)

    async def _replay(
        self,
        wallet: Wallet,
        kind: str,
        item_id: str,
        quantity: int,
        key: str | None,
    ) -> TradeResult | None:
        if key is None:
            return None
        existing = await self.wallets.find_by_key(wallet, key)
        if existing is None:
            return None
        if (existing.kind, existing.item_id, existing.quantity) != (kind, item_id, quantity):
            raise ConflictError("Esta chave de idempotência já foi usada em outra operação.")
        return TradeResult(entry=existing, balance=wallet.balance, replayed=True)
