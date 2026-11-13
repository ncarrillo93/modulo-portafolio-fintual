# Contrato Técnico: Módulo de Gestión de Cartera y Motor de Rebalanceo

Solución modular y tipada en Python 3.11 con Pydantic, Dataclasses, aritmética `Decimal` y principios SOLID.

## Archivos del Proyecto
* [`models.py`](models.py): Modelos de datos (`Asset`, `Portfolio`, `RebalanceInstruction`, `ActionType`) y excepciones.
* [`rebalance.py`](rebalance.py): Motor algorítmico de rebalanceo (`RebalanceService`).
* [`main.py`](main.py): Demostración interactiva (estado antes y después).
* [`test_portfolio.py`](test_portfolio.py): Suite de pruebas unitarias automatizadas con `pytest`.
* [`requirements.txt`](requirements.txt): Dependencias necesarias (`pydantic`, `pytest`).
* [`README.md`](README.md): Supuestos, trade-offs de diseño y guía de uso.

---

## 1. Clases, Contenedores y Tipos de Variable

### `ActionType(str, Enum)`
Tipo de acción de una orden:
* `BUY`: Compra de acciones para aumentar posición.
* `SELL`: Venta de acciones para reducir sobreponderación o liquidar.
* `HOLD`: Mantener posición (cambio dentro del umbral épsilon).

---

### `Asset`
Contenedor estructurado de activo financiero (`pydantic.dataclasses.dataclass`).

| Variable | Tipo | Requerido | Descripción | Regla de Validación |
| :--- | :--- | :--- | :--- | :--- |
| `symbol` | `str` | Sí | Ticker del activo | Se normaliza a mayúsculas, sin espacios y no vacío. |
| `current_price` | `Decimal` | Sí | Precio de mercado actual | Acepta `Decimal \| float \| int \| str`. Redondeado a 2 decimales (`ROUND_HALF_UP`), estrictamente `> 0.00`. |

#### Métodos:
* **`get_current_price() -> Decimal`** / **`getCurrentPrice() -> Decimal`**: Retorna `current_price`.
* **`currentPrice`** *(property)*: Alias `camelCase` para compatibilidad.

---

### `RebalanceInstruction`
Instrucción inmutable generada por el motor (`frozen dataclass`).

| Variable | Tipo | Descripción |
| :--- | :--- | :--- |
| `symbol` | `str` | Ticker del activo a transaccionar. |
| `action` | `ActionType` | Orden recomendada (`BUY`, `SELL`, `HOLD`). |
| `shares` | `Decimal` | Cantidad de acciones a transaccionar (6 decimales, `0` si es `HOLD`). |
| `amount` | `Decimal` | Monto monetario estimado (2 decimales). |
| `current_shares` | `Decimal` | Acciones iniciales antes del rebalanceo (6 decimales). |
| `target_shares` | `Decimal` | Acciones objetivo deseadas tras el rebalanceo (6 decimales). |

---

### `Portfolio`
Administrador de tenencias y objetivos de ponderación.

| Variable | Tipo | Por Defecto | Descripción | Regla de Validación |
| :--- | :--- | :--- | :--- | :--- |
| `holdings` | `dict[str, Decimal]` | `{}` | Mapeo `símbolo -> acciones` | Cantidades `>= 0`. |
| `target_allocations` | `dict[str, Decimal]` | `{}` | Mapeo `símbolo -> peso objetivo` | Pesos `>= 0`. Su suma debe ser `1` (tolerancia `1e-6`). |

#### Métodos:
* **`validate_target_allocations(tolerance: Decimal | float = Decimal("1e-6")) -> None`**:
  * *Entrada:* `tolerance: Decimal | float` (default `1e-6`).
  * *Salida:* `None`.
  * *Excepción:* Lanza `InvalidAllocationError` (`ValueError`) si la suma difiere de 1 más allá de la tolerancia o si hay pesos negativos.
* **`validate_holdings() -> None`**:
  * *Salida:* `None`.
  * *Excepción:* Lanza `ValueError` si hay tenencias negativas.
* **`rebalance(assets: Mapping[str, Asset], epsilon: Decimal | float = Decimal("1e-4")) -> list[RebalanceInstruction]`**:
  * *Entradas:*
    * `assets: Mapping[str, Asset]` (catálogo de precios).
    * `epsilon: Decimal | float` (default `1e-4`, umbral para `HOLD`).
  * *Salida:* `list[RebalanceInstruction]`. Ordenado con `SELL` primero (para liberar liquidez), luego `BUY`, luego `HOLD`.
  * *Excepciones:* Lanza `AssetNotFoundError` si un activo no tiene precio; `InvalidPriceError` si un precio es `<= 0.00`; `ValueError` si `epsilon < 0`.

---

## 2. Instalación y Ejecución

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar script de demostración (Antes vs Después)
python main.py

# 3. Ejecutar pruebas unitarias
pytest -v
```
