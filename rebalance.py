"""
Motor algorítmico de rebalanceo de carteras de inversión.
"""

from __future__ import annotations

import math
from typing import Mapping

from models import ActionType, Asset, AssetNotFoundError, InvalidPriceError, Portfolio, RebalanceInstruction


class RebalanceService:
    """Servicio encargado de la lógica matemática de cálculo y ajuste de carteras."""

    @classmethod
    def rebalance(
        cls,
        portfolio: Portfolio,
        assets: Mapping[str, Asset],
        epsilon: float = 1e-4,
    ) -> list[RebalanceInstruction]:
        """
        Calcula las instrucciones de compra, venta y mantenimiento de la cartera.

        1. Valida que todos los activos involucrados tengan precio registrado y > 0.0.
        2. Calcula el valor total de mercado de la cartera.
        3. Para cada activo, calcula su valor ideal y la diferencia de acciones necesaria.
        4. Clasifica en BUY, SELL o HOLD según el umbral épsilon.
        5. Ordena priorizando ventas (SELL) para generar liquidez, seguidas de compras (BUY).
        """
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
            if asset.get_current_price() <= 0.0:
                raise InvalidPriceError(
                    f"El precio del activo '{sym}' debe ser > 0.0. Recibido: {asset.get_current_price()}"
                )

        total_market_value = sum(
            portfolio.holdings.get(sym, 0.0) * normalized_assets[sym].get_current_price()
            for sym in portfolio.holdings
        )

        if math.isclose(total_market_value, 0.0, abs_tol=1e-9):
            return [
                RebalanceInstruction(
                    symbol=sym,
                    action=ActionType.HOLD,
                    shares=0.0,
                    amount=0.0,
                    current_shares=0.0,
                    target_shares=0.0,
                )
                for sym in all_symbols
            ]

        instructions: list[RebalanceInstruction] = []

        for sym in all_symbols:
            asset = normalized_assets[sym]
            price = asset.get_current_price()
            current_shares = portfolio.holdings.get(sym, 0.0)
            target_weight = portfolio.target_allocations.get(sym, 0.0)

            ideal_monetary_value = total_market_value * target_weight
            target_shares = ideal_monetary_value / price

            delta_shares = target_shares - current_shares
            delta_amount = delta_shares * price

            if abs(delta_shares) < epsilon:
                action = ActionType.HOLD
                shares_to_transact = 0.0
                amount_to_transact = 0.0
            elif delta_shares > 0:
                action = ActionType.BUY
                shares_to_transact = round(delta_shares, 6)
                amount_to_transact = round(delta_amount, 2)
            else:
                action = ActionType.SELL
                shares_to_transact = round(abs(delta_shares), 6)
                amount_to_transact = round(abs(delta_amount), 2)

            instructions.append(
                RebalanceInstruction(
                    symbol=sym,
                    action=action,
                    shares=shares_to_transact,
                    amount=amount_to_transact,
                    current_shares=round(current_shares, 6),
                    target_shares=round(target_shares, 6),
                )
            )

        priority = {ActionType.SELL: 0, ActionType.BUY: 1, ActionType.HOLD: 2}
        instructions.sort(key=lambda item: (priority[item.action], item.symbol))

        return instructions

