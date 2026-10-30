"""
Modelos de datos y entidades del dominio de carteras de inversión.
"""

from __future__ import annotations

from enum import Enum
import math
from typing import Mapping, TYPE_CHECKING
from pydantic import Field, ConfigDict
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from rebalance import RebalanceService


class ActionType(str, Enum):
    """Acción recomendada en una orden de rebalanceo."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PortfolioDomainError(ValueError):
    """Clase base para errores de validación de cartera (hereda de ValueError)."""

    pass


class InvalidAllocationError(PortfolioDomainError):
    """Lanzada cuando las asignaciones objetivo no suman 1.0."""

    pass


class InvalidPriceError(PortfolioDomainError):
    """Lanzada cuando el precio de un activo es menor o igual a 0.0."""

    pass


class AssetNotFoundError(PortfolioDomainError):
    """Lanzada cuando falta un activo en el catálogo de precios."""

    pass


@dataclass(config=ConfigDict(validate_assignment=True, extra="forbid"))
class Asset:
    """
    Representa un activo financiero con su símbolo y precio actual de mercado.

    Atributos:
        symbol (str): Ticker del activo (ej. 'META', 'AAPL', 'FRUNA').
        current_price (float): Último precio disponible (> 0.0, mantisa de 2 decimales).
    """

    symbol: str
    current_price: float = Field(..., gt=0.0)

    def __post_init__(self) -> None:
        object.__setattr__(self, "symbol", self.symbol.strip().upper())
        if self.current_price <= 0.0:
            raise InvalidPriceError(
                f"El precio del activo '{self.symbol}' debe ser > 0.0. Recibido: {self.current_price}"
            )
        object.__setattr__(self, "current_price", round(float(self.current_price), 2))

    @property
    def currentPrice(self) -> float:
        """Alias en camelCase."""
        return self.current_price

    def get_current_price(self) -> float:
        """Retorna el precio actual (snake_case)."""
        return self.current_price

    def getCurrentPrice(self) -> float:
        """Retorna el precio actual (camelCase)."""
        return self.current_price


@dataclass(frozen=True, config=ConfigDict(extra="forbid"))
class RebalanceInstruction:
    """
    Instrucción estructurada de rebalanceo para un activo.

    Atributos:
        symbol (str): Símbolo o ticker del activo.
        action (ActionType): BUY, SELL o HOLD.
        shares (float): Cantidad de acciones a transaccionar.
        amount (float): Monto monetario estimado (shares * precio).
        current_shares (float): Acciones actuales antes del rebalanceo.
        target_shares (float): Acciones ideales tras el rebalanceo.
    """

    symbol: str
    action: ActionType
    shares: float
    amount: float
    current_shares: float
    target_shares: float


@dataclass(config=ConfigDict(validate_assignment=True, extra="forbid"))
class Portfolio:
    """
    Administra las tenencias actuales y las asignaciones objetivo de la cartera.

    Atributos:
        holdings (dict[str, float]): Mapeo de símbolo a cantidad de acciones.
        target_allocations (dict[str, float]): Mapeo de símbolo a porcentaje objetivo (suma = 1.0).
    """

    holdings: dict[str, float] = Field(default_factory=dict)
    target_allocations: dict[str, float] = Field(default_factory=dict)

    DEFAULT_ALLOCATION_TOLERANCE: float = 1e-6

    def __post_init__(self) -> None:
        self.holdings = {k.strip().upper(): float(v) for k, v in self.holdings.items()}
        self.target_allocations = {
            k.strip().upper(): float(v) for k, v in self.target_allocations.items()
        }
        self.validate_target_allocations()
        self.validate_holdings()

    def validate_target_allocations(self, tolerance: float = DEFAULT_ALLOCATION_TOLERANCE) -> None:
        """Valida que los pesos sumen 1.0 con tolerancia 1e-6 y sean no negativos."""
        if not self.target_allocations:
            return

        for sym, weight in self.target_allocations.items():
            if weight < 0.0:
                raise InvalidAllocationError(
                    f"El peso objetivo para '{sym}' no puede ser negativo: {weight}"
                )

        total_weight = sum(self.target_allocations.values())
        if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=tolerance):
            raise InvalidAllocationError(
                f"La suma de los pesos objetivo debe ser complementaria a 1.0 (tolerancia {tolerance}). "
                f"Suma actual: {total_weight:.8f}"
            )

    def validate_holdings(self) -> None:
        """Valida que las cantidades de tenencias no sean negativas."""
        for sym, qty in self.holdings.items():
            if qty < 0.0:
                raise ValueError(f"La tenencia de '{sym}' no puede ser negativa: {qty}")

    @property
    def targetAllocations(self) -> dict[str, float]:
        """Alias en camelCase."""
        return self.target_allocations

    def rebalance(
        self,
        assets: Mapping[str, Asset],
        epsilon: float = 1e-4,
    ) -> list[RebalanceInstruction]:
        """Calcula las instrucciones de rebalanceo delegando a RebalanceService."""
        from rebalance import RebalanceService

        return RebalanceService.rebalance(portfolio=self, assets=assets, epsilon=epsilon)

