"""
Motor algorítmico de rebalanceo de carteras de inversión.

Opera con aritmética Decimal exacta para evitar acumulación de errores de punto
flotante binario en valorizaciones y montos de órdenes.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping

from models import (
    ActionType,
    Asset,
    AssetNotFoundError,
    InvalidPriceError,
    Portfolio,
    RebalanceInstruction,
    to_decimal,
)

SHARES_QUANT = Decimal("0.000001")
MONEY_QUANT = Decimal("0.01")


class RebalanceService:
    """Servicio encargado de la lógica matemática de cálculo y ajuste de carteras."""

    @classmethod
    def rebalance(
        cls,
        portfolio: Portfolio,
        assets: Mapping[str, Asset],
        epsilon: Decimal | float = Decimal("1e-4"),
    ) -> list[RebalanceInstruction]:
        """
        Calcula las instrucciones de compra, venta y mantenimiento de la cartera.

        1. Valida el parámetro épsilon y la disponibilidad de precios > 0.
        2. Calcula el valor total de mercado de la cartera en Decimal.
        3. Para cada activo, determina su valor ideal y la diferencia de acciones.
        4. Clasifica en BUY, SELL o HOLD usando el umbral épsilon.
        5. Ordena priorizando ventas (SELL) para liberar liquidez antes de comprar (BUY).
        """
        epsilon_dec = to_decimal(epsilon)
        if epsilon_dec < Decimal("0"):
            raise ValueError(f"El umbral épsilon no puede ser negativo: {epsilon}")

        normalized_assets: dict[str, Asset] = {
            k.strip().upper(): v for k, v in assets.items()
        }

        all_symbols = sorted(
            set(portfolio.holdings.keys()).union(portfolio.target_allocations.keys())
        )

        for sym in all_symbols:
            if sym not in normalized_assets:
                raise AssetNotFoundError(
                    f"No se encontró precio para el activo '{sym}' en el catálogo provisto."
                )
            asset = normalized_assets[sym]
            if asset.get_current_price() <= Decimal("0.00"):
                raise InvalidPriceError(
                    f"El precio del activo '{sym}' debe ser > 0.00. Recibido: {asset.get_current_price()}"
                )

        total_market_value = sum(
            (
                portfolio.holdings.get(sym, Decimal("0"))
                * normalized_assets[sym].get_current_price()
                for sym in portfolio.holdings
            ),
            Decimal("0"),
        )

        if total_market_value <= Decimal("0"):
            return [
                RebalanceInstruction(
                    symbol=sym,
                    action=ActionType.HOLD,
                    shares=Decimal("0"),
                    amount=Decimal("0.00"),
                    current_shares=Decimal("0"),
                    target_shares=Decimal("0"),
                )
                for sym in all_symbols
            ]

        instructions: list[RebalanceInstruction] = []

        for sym in all_symbols:
            asset = normalized_assets[sym]
            price = asset.get_current_price()
            current_shares = portfolio.holdings.get(sym, Decimal("0"))
            target_weight = portfolio.target_allocations.get(sym, Decimal("0"))

            ideal_monetary_value = total_market_value * target_weight
            target_shares = ideal_monetary_value / price

            delta_shares = target_shares - current_shares
            delta_amount = delta_shares * price

            if abs(delta_shares) < epsilon_dec:
                action = ActionType.HOLD
                shares_to_transact = Decimal("0")
                amount_to_transact = Decimal("0.00")
            elif delta_shares > Decimal("0"):
                action = ActionType.BUY
                shares_to_transact = delta_shares.quantize(SHARES_QUANT, rounding=ROUND_HALF_UP)
                amount_to_transact = delta_amount.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            else:
                action = ActionType.SELL
                shares_to_transact = abs(delta_shares).quantize(SHARES_QUANT, rounding=ROUND_HALF_UP)
                amount_to_transact = abs(delta_amount).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)

            instructions.append(
                RebalanceInstruction(
                    symbol=sym,
                    action=action,
                    shares=shares_to_transact,
                    amount=amount_to_transact,
                    current_shares=current_shares.quantize(SHARES_QUANT, rounding=ROUND_HALF_UP),
                    target_shares=target_shares.quantize(SHARES_QUANT, rounding=ROUND_HALF_UP),
                )
            )

        priority = {ActionType.SELL: 0, ActionType.BUY: 1, ActionType.HOLD: 2}
        instructions.sort(key=lambda item: (priority[item.action], item.symbol))

        return instructions
