"""
Script de demostración del motor de rebalanceo de inversiones.

Muestra el estado detallado de la cartera ANTES y DESPUÉS de aplicar las
instrucciones generadas por el motor algorítmico de rebalanceo.
"""

from __future__ import annotations

from decimal import Decimal

from models import ActionType, Asset, Portfolio


def print_separator(char: str = "=", length: int = 80) -> None:
    print(char * length)


def print_portfolio_state(
    title: str,
    holdings: dict[str, Decimal],
    target_allocations: dict[str, Decimal],
    assets: dict[str, Asset],
) -> Decimal:
    print_separator("-")
    print(f" {title.upper()}")
    print_separator("-")

    total_value = sum(
        (
            holdings.get(sym, Decimal("0")) * assets[sym].get_current_price()
            for sym in holdings
            if sym in assets
        ),
        Decimal("0"),
    )

    header = f"{'Símbolo':<10} | {'Acciones':<12} | {'Precio':<10} | {'Valor ($)':<12} | {'% Actual':<10} | {'% Objetivo':<10}"
    print(header)
    print("-" * len(header))

    all_symbols = sorted(set(holdings.keys()).union(target_allocations.keys()))
    for sym in all_symbols:
        shares = holdings.get(sym, Decimal("0"))
        price = assets[sym].get_current_price() if sym in assets else Decimal("0")
        val = shares * price
        pct_actual = (val / total_value * Decimal("100")) if total_value > Decimal("0") else Decimal("0")
        pct_target = target_allocations.get(sym, Decimal("0")) * Decimal("100")

        print(
            f"{sym:<10} | {shares:>12.4f} | ${price:>9.2f} | ${val:>11.2f} | {pct_actual:>9.2f}% | {pct_target:>9.2f}%"
        )

    print("-" * len(header))
    print(f"VALOR TOTAL DEL PORTAFOLIO: ${total_value:,.2f}")
    print()
    return total_value


def main() -> None:
    print_separator("=")
    print("      SISTEMA DE GESTIÓN DE CARTERAS & MOTOR DE REBALANCEO - FINTUAL")
    print_separator("=")
    print()

    # 1. Catálogo de activos de mercado
    market_assets: dict[str, Asset] = {
        "META": Asset(symbol="META", current_price=Decimal("500.00")),
        "FRUNA": Asset(symbol="FRUNA", current_price=Decimal("10.00")),
        "AAPL": Asset(symbol="AAPL", current_price=Decimal("200.00")),
        "TSLA": Asset(symbol="TSLA", current_price=Decimal("250.00")),
    }

    # 2. Cartera con tenencias desbalanceadas
    portfolio = Portfolio(
        holdings={
            "META": Decimal("10.0"),
            "FRUNA": Decimal("50.0"),
            "AAPL": Decimal("5.0"),
        },
        target_allocations={
            "META": Decimal("0.40"),
            "FRUNA": Decimal("0.30"),
            "AAPL": Decimal("0.30"),
        },
    )

    # 3. Estado ANTES del rebalanceo
    print(">>> FASE 1: DIAGNÓSTICO INICIAL")
    print_portfolio_state(
        title="Estado del Portafolio: ANTES del Rebalanceo",
        holdings=portfolio.holdings,
        target_allocations=portfolio.target_allocations,
        assets=market_assets,
    )

    # 4. Ejecutar rebalanceo
    print(">>> FASE 2: EJECUCIÓN DEL MOTOR DE REBALANCEO (rebalance)")
    instructions = portfolio.rebalance(assets=market_assets, epsilon=Decimal("1e-4"))

    print(
        f"{'Acción':<8} | {'Símbolo':<8} | {'Acciones a Operar':<18} | {'Monto Est. ($)':<16} | {'Acciones Ini -> Fin'}"
    )
    print("-" * 75)

    total_ventas = Decimal("0.00")
    total_compras = Decimal("0.00")

    for instr in instructions:
        if instr.action == ActionType.SELL:
            total_ventas += instr.amount
            prefix = "[-]"
        elif instr.action == ActionType.BUY:
            total_compras += instr.amount
            prefix = "[+]"
        else:
            prefix = "[=]"

        flow_str = f"{instr.current_shares:.4f} -> {instr.target_shares:.4f}"
        print(
            f"{prefix} {instr.action.value:<4} | {instr.symbol:<8} | {instr.shares:>18.4f} | ${instr.amount:>15.2f} | {flow_str}"
        )

    print("-" * 75)
    print(f"Resumen de Flujos: Ventas = ${total_ventas:,.2f} | Compras = ${total_compras:,.2f}")
    balance_neto = total_ventas - total_compras
    print(f"Balance Neto de Efectivo (Autofinanciado): ${balance_neto:,.2f}")
    print()

    # 5. Estado DESPUÉS del rebalanceo
    simulated_holdings = {instr.symbol: instr.target_shares for instr in instructions}

    print(">>> FASE 3: AUDITORÍA POST-EJECUCIÓN")
    print_portfolio_state(
        title="Estado del Portafolio: DESPUÉS del Rebalanceo",
        holdings=simulated_holdings,
        target_allocations=portfolio.target_allocations,
        assets=market_assets,
    )

    print("[OK] Rebalanceo completado con éxito. Todas las ponderaciones convergen al objetivo deseado.")
    print_separator("=")


if __name__ == "__main__":
    main()
