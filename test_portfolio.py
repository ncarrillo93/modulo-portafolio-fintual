"""
Pruebas unitarias para modelos y motor de rebalanceo de cartera.
"""

from decimal import Decimal
import pytest

from models import (
    ActionType,
    Asset,
    AssetNotFoundError,
    InvalidAllocationError,
    InvalidPriceError,
    Portfolio,
)


class TestAsset:
    """Pruebas para el modelo Asset y precisión Decimal."""

    def test_asset_creation_and_accessors(self) -> None:
        asset = Asset(symbol="aapl", current_price=185.50)
        assert asset.symbol == "AAPL"
        assert asset.current_price == Decimal("185.50")
        assert asset.currentPrice == Decimal("185.50")
        assert asset.get_current_price() == Decimal("185.50")
        assert asset.getCurrentPrice() == Decimal("185.50")

    def test_asset_price_rounded_half_up_to_two_decimals(self) -> None:
        assert Asset(symbol="META", current_price=500.1234).current_price == Decimal("500.12")
        assert Asset(symbol="FRUNA", current_price="10.005").current_price == Decimal("10.01")

    @pytest.mark.parametrize("invalid_price", [0.0, -10.5, -0.01, "0.001", float("nan"), float("inf")])
    def test_asset_invalid_price_raises_error(self, invalid_price: float | str) -> None:
        with pytest.raises(ValueError):
            Asset(symbol="FRUNA", current_price=invalid_price)

    def test_asset_price_rounding_to_zero_raises_invalid_price_error(self) -> None:
        with pytest.raises(InvalidPriceError):
            Asset(symbol="FRUNA", current_price="0.001")

    def test_empty_symbol_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            Asset(symbol="   ", current_price=10.00)


class TestPortfolioValidation:
    """Pruebas de validación en la clase Portfolio."""

    def test_valid_portfolio_initialization(self) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0, "FRUNA": 50.0},
            target_allocations={"META": 0.40, "FRUNA": 0.30, "AAPL": 0.30},
        )
        assert portfolio.holdings["META"] == Decimal("10.0")
        assert portfolio.targetAllocations["AAPL"] == Decimal("0.30")

    def test_binary_float_classic_weights_are_exact_in_decimal(self) -> None:
        # En float binario 0.1 + 0.2 + 0.7 != 1.0 exactamente; en Decimal es exacto.
        portfolio = Portfolio(
            target_allocations={"A": 0.1, "B": 0.2, "C": 0.7},
        )
        assert sum(portfolio.target_allocations.values()) == Decimal("1.0")

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
        with pytest.raises(InvalidAllocationError):
            Portfolio(target_allocations=bad_targets)

    def test_negative_holdings_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            Portfolio(holdings={"META": -5.0}, target_allocations={"META": 1.0})


class TestRebalance:
    """Pruebas del motor algorítmico de rebalanceo."""

    @pytest.fixture
    def market_assets(self) -> dict[str, Asset]:
        return {
            "META": Asset(symbol="META", current_price=Decimal("500.00")),
            "FRUNA": Asset(symbol="FRUNA", current_price=Decimal("10.00")),
            "AAPL": Asset(symbol="AAPL", current_price=Decimal("200.00")),
            "TSLA": Asset(symbol="TSLA", current_price=Decimal("250.00")),
        }

    def test_standard_rebalance_and_execution_order(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0, "FRUNA": 50.0, "AAPL": 5.0},
            target_allocations={"META": 0.40, "FRUNA": 0.30, "AAPL": 0.30},
        )
        instructions = portfolio.rebalance(assets=market_assets)
        instr_by_symbol = {i.symbol: i for i in instructions}

        # Prioridad: SELL antes que BUY
        assert instructions[0].action == ActionType.SELL
        assert instructions[0].symbol == "META"

        # META: vende 4.8 acciones ($2400.00)
        assert instr_by_symbol["META"].action == ActionType.SELL
        assert instr_by_symbol["META"].shares == Decimal("4.800000")
        assert instr_by_symbol["META"].amount == Decimal("2400.00")

        # FRUNA: compra 145 acciones ($1450.00)
        assert instr_by_symbol["FRUNA"].action == ActionType.BUY
        assert instr_by_symbol["FRUNA"].shares == Decimal("145.000000")
        assert instr_by_symbol["FRUNA"].amount == Decimal("1450.00")

        # AAPL: compra 4.75 acciones ($950.00)
        assert instr_by_symbol["AAPL"].action == ActionType.BUY
        assert instr_by_symbol["AAPL"].shares == Decimal("4.750000")
        assert instr_by_symbol["AAPL"].amount == Decimal("950.00")

        # Autofinanciamiento exacto
        total_sell = sum((i.amount for i in instructions if i.action == ActionType.SELL), Decimal("0"))
        total_buy = sum((i.amount for i in instructions if i.action == ActionType.BUY), Decimal("0"))
        assert total_sell == total_buy

    def test_epsilon_threshold_triggers_hold(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": Decimal("5.20002"), "AAPL": Decimal("19.5")},
            target_allocations={"META": 0.40, "AAPL": 0.60},
        )
        instructions = portfolio.rebalance(assets=market_assets, epsilon=Decimal("1e-4"))
        instr_by_symbol = {i.symbol: i for i in instructions}

        assert instr_by_symbol["META"].action == ActionType.HOLD
        assert instr_by_symbol["META"].shares == Decimal("0")
        assert instr_by_symbol["META"].amount == Decimal("0.00")

    def test_orphan_holding_is_sold(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0, "TSLA": 4.0},
            target_allocations={"META": 1.0},
        )
        instructions = portfolio.rebalance(assets=market_assets)
        instr_by_symbol = {i.symbol: i for i in instructions}

        assert instr_by_symbol["TSLA"].action == ActionType.SELL
        assert instr_by_symbol["TSLA"].shares == Decimal("4.000000")
        assert instr_by_symbol["TSLA"].amount == Decimal("1000.00")

    def test_new_target_without_holding_is_bought(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"META": 10.0},
            target_allocations={"META": 0.50, "AAPL": 0.50},
        )
        instructions = portfolio.rebalance(assets=market_assets)
        instr_by_symbol = {i.symbol: i for i in instructions}

        assert instr_by_symbol["AAPL"].action == ActionType.BUY
        assert instr_by_symbol["AAPL"].target_shares == Decimal("12.500000")
        assert instr_by_symbol["AAPL"].amount == Decimal("2500.00")

    def test_missing_asset_raises_error(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(
            holdings={"UNKNOWN": 10.0},
            target_allocations={"UNKNOWN": 1.0},
        )
        with pytest.raises(AssetNotFoundError):
            portfolio.rebalance(assets=market_assets)

    def test_negative_epsilon_raises_value_error(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(holdings={"META": 1.0}, target_allocations={"META": 1.0})
        with pytest.raises(ValueError):
            portfolio.rebalance(assets=market_assets, epsilon=-0.01)

    def test_empty_portfolio_rebalance(self, market_assets: dict[str, Asset]) -> None:
        portfolio = Portfolio(holdings={}, target_allocations={"META": 1.0})
        instructions = portfolio.rebalance(assets=market_assets)
        assert len(instructions) == 1
        assert instructions[0].action == ActionType.HOLD
        assert instructions[0].amount == Decimal("0.00")
