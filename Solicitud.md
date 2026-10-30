# Módulo de Gestión de Cartera y Motor de Rebalanceo

Solución modular y tipada en Python 3.11 con Pydantic, Dataclasses y principios SOLID. Todo el código reside directamente en la raíz del proyecto.

## Archivos del Proyecto
* [`models.py`](file:///c:/Users/Nicolas%20Carrillo/OneDrive%20-%20CTR/Escritorio/Postulacion%20Fintual/models.py): Modelos de datos (`Asset`, `Portfolio`, `RebalanceInstruction`, `ActionType`) y excepciones.
* [`rebalance.py`](file:///c:/Users/Nicolas%20Carrillo/OneDrive%20-%20CTR/Escritorio/Postulacion%20Fintual/rebalance.py): Motor algorítmico de rebalanceo (`RebalanceService`).
* [`main.py`](file:///c:/Users/Nicolas%20Carrillo/OneDrive%20-%20CTR/Escritorio/Postulacion%20Fintual/main.py): Demostración interactiva (estado antes y después). Valida e instala dependencias automáticamente si faltan.
* [`test_portfolio.py`](file:///c:/Users/Nicolas%20Carrillo/OneDrive%20-%20CTR/Escritorio/Postulacion%20Fintual/test_portfolio.py): Suite de 18 pruebas unitarias automatizadas con `pytest`.
* [`requirements.txt`](file:///c:/Users/Nicolas%20Carrillo/OneDrive%20-%20CTR/Escritorio/Postulacion%20Fintual/requirements.txt): Dependencias necesarias (`pydantic`, `pytest`).

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
| `symbol` | `str` | Sí | Ticker del activo | Se normaliza a mayúsculas y sin espacios. |
| `current_price` | `float` | Sí | Precio de mercado actual | Estrictamente `> 0.0`. Redondeado a 2 decimales. |

#### Métodos:
* **`get_current_price() -> float`** / **`getCurrentPrice() -> float`**: Retorna `current_price`.
* **`currentPrice`** *(property)*: Alias `camelCase` para compatibilidad.

---

### `RebalanceInstruction`
Instrucción inmutable generada por el motor (`frozen dataclass`).

| Variable | Tipo | Descripción |
| :--- | :--- | :--- |
| `symbol` | `str` | Ticker del activo a transaccionar. |
| `action` | `ActionType` | Orden recomendada (`BUY`, `SELL`, `HOLD`). |
| `shares` | `float` | Cantidad de acciones a transaccionar (`0.0` si es `HOLD`). |
| `amount` | `float` | Monto monetario estimado (`shares * precio`). |
| `current_shares` | `float` | Acciones iniciales antes del rebalanceo. |
| `target_shares` | `float` | Acciones objetivo deseadas tras el rebalanceo. |

---

### `Portfolio`
Administrador de tenencias y objetivos de ponderación.

| Variable | Tipo | Por Defecto | Descripción | Regla de Validación |
| :--- | :--- | :--- | :--- | :--- |
| `holdings` | `dict[str, float]` | `{}` | Mapeo `símbolo -> acciones` | Cantidades deben ser `>= 0.0`. |
| `target_allocations` | `dict[str, float]` | `{}` | Mapeo `símbolo -> peso objetivo` | Pesos `>= 0.0`. Su suma debe ser `1.0` (tolerancia `1e-6`). |

#### Métodos:
* **`validate_target_allocations(tolerance: float = 1e-6) -> None`**:
  * *Entrada:* `tolerance: float` (default `1e-6`).
  * *Salida:* `None`.
  * *Excepción:* Lanza `InvalidAllocationError` (`ValueError`) si la suma difiere de 1.0 más allá de la tolerancia o si hay pesos negativos.
* **`validate_holdings() -> None`**:
  * *Salida:* `None`.
  * *Excepción:* Lanza `ValueError` si hay tenencias negativas.
* **`rebalance(assets: Mapping[str, Asset], epsilon: float = 1e-4) -> list[RebalanceInstruction]`**:
  * *Entradas:*
    * `assets: Mapping[str, Asset]` (catálogo de precios).
    * `epsilon: float` (default `1e-4`, umbral para `HOLD`).
  * *Salida:* `list[RebalanceInstruction]`. Ordenado con `SELL` primero (para liberar liquidez), luego `BUY`, luego `HOLD`.
  * *Excepciones:* Lanza `AssetNotFoundError` si un activo no tiene precio; `InvalidPriceError` si un precio es `<= 0.0`.

---

## 2. Instalación y Ejecución

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar script de demostración (Antes vs Después)
python main.py

# 3. Ejecutar pruebas unitarias (18 tests)
pytest -v
```
