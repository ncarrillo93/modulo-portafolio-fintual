"""
Modelos de datos y entidades del dominio de carteras de inversión.

Usa Decimal internamente para evitar errores de precisión binaria propios de float
en precios, acciones fraccionarias y montos monetarios.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import Enum
import math
from typing import Annotated, ClassVar, Mapping, TYPE_CHECKING

from pydantic import BeforeValidator, ConfigDict, Field, ValidationError
from pydantic.dataclasses import dataclass

if TYPE_CHECKING:
    from rebalance import RebalanceService

PRICE_QUANT = Decimal("0.01")


def _unwrap_domain_errors(cls):
    """
    Desenvuelve excepciones de dominio para que se puedan capturar como su tipo específico
    (InvalidAllocationError, InvalidPriceError) o como ValueError, sin quedar encapsuladas
    en ValidationError de Pydantic.
    """
    orig_init = cls.__init__

    def wrapped_init(self, *args, **kwargs):
        try:
            orig_init(self, *args, **kwargs)
        except ValidationError as exc:
            for err in exc.errors():
                cause = err.get("ctx", {}).get("error")
                if isinstance(cause, PortfolioDomainError):
                    raise cause from None
            raise

    cls.__init__ = wrapped_init
    return cls


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """
    Convierte entradas numéricas o textuales a Decimal de forma segura.

    Para valores float convierte vía str(value) para evitar arrastrar ruido binario
    IEEE-754 (ej. 0.1 -> Decimal('0.1') en vez de Decimal('0.10000000000000000555...')).
    """
    if isinstance(value, bool):
        raise ValueError("No se permite booleano como valor numérico.")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"El valor Decimal debe ser finito: {value}")
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"El valor float debe ser finito: {value}")
        return Decimal(str(value))
    if isinstance(value, (int, str)):
        try:
            parsed = Decimal(value)
        except InvalidOperation as exc:
            raise ValueError(f"No se pudo convertir '{value}' a Decimal.") from exc
        if not parsed.is_finite():
            raise ValueError(f"El valor debe ser finito: {value}")
        return parsed
    raise TypeError(f"Tipo no soportado para conversión a Decimal: {type(value).__name__}")


MoneyDecimal = Annotated[Decimal, BeforeValidator(to_decimal)]


class ActionType(str, Enum):
    """Acción recomendada en una orden de rebalanceo."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class PortfolioDomainError(ValueError):
    """Clase base para errores de validación de cartera (hereda de ValueError)."""


class InvalidAllocationError(PortfolioDomainError):
    """Lanzada cuando las asignaciones objetivo no suman 1.0 dentro de la tolerancia."""


class InvalidPriceError(PortfolioDomainError):
    """Lanzada cuando el precio de un activo es menor o igual a 0.0."""


class AssetNotFoundError(PortfolioDomainError):
    """Lanzada cuando falta un activo en el catálogo de precios."""


@_unwrap_domain_errors
@dataclass(config=ConfigDict(validate_assignment=True, extra="forbid"))
class Asset:
    """
    Representa un activo financiero con su símbolo y precio actual de mercado.

    Atributos:
        symbol (str): Ticker del activo (ej. 'META', 'AAPL', 'FRUNA').
        current_price (Decimal): Último precio disponible (> 0.00, 2 decimales ROUND_HALF_UP).
    """

    symbol: str
    current_price: MoneyDecimal = Field(..., gt=Decimal("0"))

    def __post_init__(self) -> None:
        normalized_symbol = self.symbol.strip().upper()
        if not normalized_symbol:
            raise ValueError("El símbolo del activo no puede estar vacío.")
        object.__setattr__(self, "symbol", normalized_symbol)

        rounded_price = self.current_price.quantize(PRICE_QUANT, rounding=ROUND_HALF_UP)
        if rounded_price <= Decimal("0.00"):
            raise InvalidPriceError(
                f"El precio del activo '{self.symbol}' tras redondear a 2 decimales debe ser > 0.00. "
                f"Recibido: {self.current_price}"
            )
        object.__setattr__(self, "current_price", rounded_price)

    @property
    def currentPrice(self) -> Decimal:
        """Alias en camelCase."""
        return self.current_price

    def get_current_price(self) -> Decimal:
        """Retorna el precio actual (snake_case)."""
        return self.current_price

    def getCurrentPrice(self) -> Decimal:
        """Retorna el precio actual (camelCase)."""
        return self.current_price


@dataclass(frozen=True, config=ConfigDict(extra="forbid"))
class RebalanceInstruction:
    """
    Instrucción estructurada e inmutable de rebalanceo para un activo.

    Atributos:
        symbol (str): Símbolo o ticker del activo.
        action (ActionType): BUY, SELL o HOLD.
        shares (Decimal): Cantidad de acciones a transaccionar (>= 0).
        amount (Decimal): Monto monetario estimado (2 decimales).
        current_shares (Decimal): Acciones actuales antes del rebalanceo.
        target_shares (Decimal): Acciones ideales tras el rebalanceo.
    """

    symbol: str
    action: ActionType
    shares: Decimal
    amount: Decimal
    current_shares: Decimal
    target_shares: Decimal


@_unwrap_domain_errors
@dataclass(config=ConfigDict(validate_assignment=True, extra="forbid"))
class Portfolio:
    """
    Administra las tenencias actuales y las asignaciones objetivo de la cartera.

    Atributos:
        holdings (dict[str, Decimal]): Mapeo de símbolo a cantidad de acciones.
        target_allocations (dict[str, Decimal]): Mapeo de símbolo a peso objetivo (suma = 1).
    """

    holdings: dict[str, MoneyDecimal] = Field(default_factory=dict)
    target_allocations: dict[str, MoneyDecimal] = Field(default_factory=dict)

    DEFAULT_ALLOCATION_TOLERANCE: ClassVar[Decimal] = Decimal("1e-6")

    def __post_init__(self) -> None:
        self.holdings = {k.strip().upper(): to_decimal(v) for k, v in self.holdings.items()}
        self.target_allocations = {
            k.strip().upper(): to_decimal(v) for k, v in self.target_allocations.items()
        }
        self.validate_target_allocations()
        self.validate_holdings()

    def validate_target_allocations(
        self, tolerance: Decimal | float = DEFAULT_ALLOCATION_TOLERANCE
    ) -> None:
        """Valida que los pesos sumen 1 con tolerancia 1e-6 y sean no negativos."""
        if not self.target_allocations:
            return

        tolerance_dec = to_decimal(tolerance)
        if tolerance_dec < Decimal("0"):
            raise ValueError(f"La tolerancia no puede ser negativa: {tolerance}")

        for sym, weight in self.target_allocations.items():
            if not sym:
                raise InvalidAllocationError("El símbolo en target_allocations no puede estar vacío.")
            if weight < Decimal("0"):
                raise InvalidAllocationError(
                    f"El peso objetivo para '{sym}' no puede ser negativo: {weight}"
                )

        total_weight = sum(self.target_allocations.values(), Decimal("0"))
        if abs(total_weight - Decimal("1")) > tolerance_dec:
            raise InvalidAllocationError(
                f"La suma de los pesos objetivo debe ser complementaria a 1.0 (tolerancia {tolerance_dec}). "
                f"Suma actual: {total_weight}"
            )

    def validate_holdings(self) -> None:
        """Valida que las cantidades de tenencias no sean negativas."""
        for sym, qty in self.holdings.items():
            if not sym:
                raise ValueError("El símbolo en holdings no puede estar vacío.")
            if qty < Decimal("0"):
                raise ValueError(f"La tenencia de '{sym}' no puede ser negativa: {qty}")

    @property
    def targetAllocations(self) -> dict[str, Decimal]:
        """Alias en camelCase."""
        return self.target_allocations

    def rebalance(
        self,
        assets: Mapping[str, Asset],
        epsilon: Decimal | float = Decimal("1e-4"),
    ) -> list[RebalanceInstruction]:
        """Calcula las instrucciones de rebalanceo delegando a RebalanceService."""
        from rebalance import RebalanceService

        return RebalanceService.rebalance(portfolio=self, assets=assets, epsilon=epsilon)
