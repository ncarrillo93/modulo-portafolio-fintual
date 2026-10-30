"""
Pruebas unitarias para modelos y motor de rebalanceo de cartera.
"""

import math
import pytest

from models import (
    ActionType,
    Asset,
    AssetNotFoundError,
    InvalidAllocationError,
    InvalidPriceError,
    Portfolio,
    RebalanceInstruction,
)
from rebalance import RebalanceService


class TestAsset:
    """Pruebas para el modelo Asset."""

    def test_asset_creation_and_accessors(self) -> None:
        asset = Asset(symbol="aapl", current_price=185.50)
        assert asset.symbol == "AAPL"
        assert asset.current_price == 185.50
        assert asset.currentPrice == 185.50
        assert asset.get_current_price() == 185.50
        assert asset.getCurrentPrice() == 185.50

    def test_asset_price_rounded_to_two_decimals(self) -> None:
        asset = Asset(symbol="META", current_price=500.1234)
        assert asset.current_price == 500.12

    @pytest.mark.parametrize("invalid_price", [0.0, -10.5, -0.01])
    def test_asset_invalid_price_raises_error(self, invalid_price: float) -> None:
        with pytest.raises(ValueError):
            Asset(symbol="FRUNA", current_price=invalid_price)


class TestPortfolioValidation:
    """Pruebas de validación en la clase Portfolio."""

    def test_valid_portfolio_initialization(self) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0, "FRUNA": 50.0},
            target_allocations={"META": 0.40, "FRUNA": 0.30, "AAPL": 0.30},
        )
        assert portfolio.holdings["META"] == 10.0
        assert portfolio.targetAllocations["AAPL"] == 0.30

    def test_allocation_sum_within_tolerance_accepted(self) -> None:
        portfolio = Portfolio(
            target_allocations={"A": 0.50, "B": 0.5000005},
        )
        assert portfolio is not None

    @pytest.mark.parametrize(
        "bad_targets",
        [
            {"META": 0.40, "AAPL": 0.50},  # Suma 0.90 (< 1.0)
            {"META": 0.60, "AAPL": 0.50},  # Suma 1.10 (> 1.0)
            {"META": 1.00001, "AAPL": 0.0},  # Suma 1.00001 (fuera de tolerancia 1e-6)
            {"META": -0.20, "AAPL": 1.20},  # Peso negativo
        ],
    )
    def test_invalid_allocation_sum_raises_value_error(
        self, bad_targets: dict[str, float]
    ) -> None:
        with pytest.raises(ValueError):
            Portfolio(target_allocations=bad_targets)

    def test_negative_holdings_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            Portfolio(holdings={"META": -5.0}, target_allocations={"META": 1.0})


class TestRebalance:
    """Pruebas del motor algorítmico de rebalanceo."""

    @pytest.fixture
    def market_assets(self) -> dict[str, Asset]:
        return {
            "META": Asset(symbol="META", current_price=500.00),
            "FRUNA": Asset(symbol="FRUNA", current_price=10.00),
            "AAPL": Asset(symbol="AAPL", current_price=200.00),
            "TSLA": Asset(symbol="TSLA", current_price=250.00),
        }

    def test_standard_rebalance(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0, "FRUNA": 50.0, "AAPL": 5.0},
            target_allocations={"META": 0.40, "FRUNA": 0.30, "AAPL": 0.30},
        )
        instructions = portfolio.rebalance(assets=market_assets)
        instr_by_symbol = {i.symbol: i for i in instructions}

        # META: vende 4.8 acciones ($2400)
        assert instr_by_symbol["META"].action == ActionType.SELL
        assert math.isclose(instr_by_symbol["META"].shares, 4.8, abs_tol=1e-4)

        # FRUNA: compra 145 acciones ($1450)
        assert instr_by_symbol["FRUNA"].action == ActionType.BUY
        assert math.isclose(instr_by_symbol["FRUNA"].shares, 145.0, abs_tol=1e-4)

        # AAPL: compra 4.75 acciones ($950)
        assert instr_by_symbol["AAPL"].action == ActionType.BUY
        assert math.isclose(instr_by_symbol["AAPL"].shares, 4.75, abs_tol=1e-4)

    def test_epsilon_threshold_triggers_hold(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": 5.20002, "AAPL": 19.5},
            target_allocations={"META": 0.40, "AAPL": 0.60},
        )
        instructions = portfolio.rebalance(assets=market_assets, epsilon=1e-4)
        instr_by_symbol = {i.symbol: i for i in instructions}

        assert instr_by_symbol["META"].action == ActionType.HOLD
        assert instr_by_symbol["META"].shares == 0.0

    def test_orphan_holding_is_sold(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0, "TSLA": 4.0},
            target_allocations={"META": 1.0},
        )
        instructions = portfolio.rebalance(assets=market_assets)
        instr_by_symbol = {i.symbol: i for i in instructions}

        assert instr_by_symbol["TSLA"].action == ActionType.SELL
        assert instr_by_symbol["TSLA"].shares == 4.0

    def test_new_target_without_holding_is_bought(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0},
            target_allocations={"META": 0.50, "AAPL": 0.50},
        )
        instructions = portfolio.rebalance(assets=market_assets)
        instr_by_symbol = {i.symbol: i for i in instructions}

        assert instr_by_symbol["AAPL"].action == ActionType.BUY
        assert math.isclose(instr_by_symbol["AAPL"].target_shares, 12.5, abs_tol=1e-4)

    def test_missing_asset_raises_error(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"UNKNOWN": 10.0},
            target_allocations={"UNKNOWN": 1.0},
        )
        with pytest.raises(AssetNotFoundError):
            portfolio.rebalance(assets=market_assets)

    def test_empty_portfolio_rebalance(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(holdings={}, target_allocations={"META": 1.0})
        instructions = portfolio.rebalance(assets=market_assets)
        assert len(instructions) == 1
        assert instructions[0].action == ActionType.HOLD

