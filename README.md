# Módulo de Gestión de Cartera de Inversión y Motor de Rebalanceo

Solución de ingeniería de software para el módulo de administración de portafolios y rebalanceo algorítmico de inversiones (estilo Fintual), desarrollada en **Python 3.11** bajo principios **SOLID**, **Clean Code**, **Pydantic (v2)** y separación de responsabilidades.

---

## 1. Supuestos, Decisiones de Diseño y Trade-offs

Para resolver las ambigüedades propias del dominio financiero de forma explícita y auditable, se adoptaron las siguientes decisiones:

1. **Aritmética `Decimal` en lugar de `float` binario:**
   * *Decisión:* Todos los precios, pesos, cantidades de acciones y montos monetarios operan internamente con `decimal.Decimal` y redondeo financiero `ROUND_HALF_UP` (2 decimales para dinero y precios; 6 decimales para acciones fraccionarias).
   * *Por qué:* En sistemas financieros, el punto flotante binario (`float`) introduce errores de representación (ej. `0.1 + 0.2 != 0.3`). Los constructores siguen aceptando `float`, `int`, `str` o `Decimal` por ergonomía, pero convierten los `float` vía `Decimal(str(x))` para no arrastrar ruido binario.
2. **Cartera 100% invertida (sin caja disponible / *cash = 0*):**
   * *Decisión:* El valor total de la cartera equivale estrictamente a $\sum (\text{acciones}_i \times \text{precio}_i)$. No se modela saldo en efectivo externo; el rebalanceo es autofinanciado (las ventas financian las compras).
   * *Trade-off:* Simplifica la lógica de primera iteración. Para incorporar depósitos o liquidez previa bastaría sumar un parámetro `cash_balance` al valor total objetivo.
3. **Normalización de precios a 2 decimales:**
   * *Decisión:* `Asset.current_price` se normaliza a 2 decimales (`0.01`) con `ROUND_HALF_UP` y exige que el precio resultante sea estrictamente mayor a `0.00` (si un precio como `0.001` redondea a `0.00`, se rechaza con `InvalidPriceError`).
4. **Acciones fraccionarias:**
   * *Decisión:* Se soportan fracciones de acciones (hasta 6 decimales) en lugar de acciones enteras, alineado con plataformas modernas de inversión personal.
   * *Trade-off:* El redondeo individual por activo puede dejar un residual de centavos entre el total vendido y el total comprado cuando los precios no son divisores exactos.
5. **Activos fuera de la distribución objetivo y activos nuevos:**
   * *Activos huérfanos* (presentes en `holdings` pero ausentes o con peso `0` en `target_allocations`): se interpretan como salida del mandato y generan una orden `SELL` por el 100% de la posición.
   * *Activos nuevos* (presentes en `target_allocations` pero no en `holdings`): se asume tenencia inicial `0` y generan una orden `BUY`.
6. **Umbral épsilon (`1e-4`) sobre diferencia de acciones:**
   * *Decisión:* Si $|\text{acciones\_ideales} - \text{acciones\_actuales}| < \epsilon$, se emite `HOLD` con `shares = 0` y `amount = 0.00` para evitar micro-órdenes innecesarias.
   * *Trade-off:* En activos de precio unitario muy alto, una fracción pequeña de acción puede equivaler a un monto monetario relevante; por eso `epsilon` es configurable en `rebalance()`.
7. **Sin fricciones de mercado:**
   * Se asume ejecución simultánea sin comisiones de corretaje, impuestos ni *slippage* entre el cálculo de la orden y su calce.
8. **Priorización financiera (`SELL` antes que `BUY`):**
   * Las instrucciones retornan ordenadas con `SELL` primero para liberar liquidez antes de ejecutar compras, seguidas de `BUY` y `HOLD`.
9. **Estructura plana:**
   * Para un módulo de este tamaño, mantener los archivos directamente en la raíz evita *over-engineering* de subpaquetes innecesarios y facilita la lectura.

---

## 2. Arquitectura y Estructura del Proyecto

* **Single Responsibility Principle (SRP):**
  * `Asset` encapsula datos de mercado y validación de precios.
  * `Portfolio` administra tenencias y validación de ponderaciones objetivo (tolerancia `1e-6`).
  * `RebalanceService` es un servicio *stateless* dedicado al cálculo matemático del rebalanceo.
* **Compatibilidad de Nomenclatura:** Implementación nativa en `snake_case` (PEP 8) con aliases `camelCase` (`currentPrice`, `getCurrentPrice`, `targetAllocations`).

```text
├── models.py           # Modelos de dominio (Asset, Portfolio, RebalanceInstruction, ActionType) y excepciones
├── rebalance.py        # Motor algorítmico de rebalanceo (RebalanceService)
├── main.py             # Script de demostración (estado Antes vs Después)
├── test_portfolio.py   # Suite de pruebas unitarias automatizadas con pytest
├── requirements.txt    # Dependencias del proyecto (pydantic, pytest)
├── pyproject.toml      # Configuración de proyecto y pytest
├── Solicitud.md        # Contrato detallado de entradas, salidas y tipos
└── README.md           # Documentación general, supuestos y guía de uso
```

---

## 3. Modelo Matemático

1. **Valor Total de Mercado:**
   $$\text{Valor Total} = \sum (\text{acciones}_i \times \text{precio}_i)$$
2. **Posición Ideal por Activo:**
   $$\text{Valor Ideal}_i = \text{Valor Total} \times \text{peso\_objetivo}_i$$
   $$\text{Acciones Ideales}_i = \frac{\text{Valor Ideal}_i}{\text{precio}_i}$$
3. **Desviación y Clasificación:**
   $$\Delta \text{Acciones}_i = \text{Acciones Ideales}_i - \text{Acciones Actuales}_i$$
   * $|\Delta \text{Acciones}_i| < \epsilon$ $\rightarrow$ `HOLD`
   * $\Delta \text{Acciones}_i > 0$ $\rightarrow$ `BUY`
   * $\Delta \text{Acciones}_i < 0$ $\rightarrow$ `SELL`

---

## 4. Instalación y Ejecución

Crea un entorno virtual (recomendado) e instala explícitamente las dependencias declaradas en `requirements.txt`:

```bash
python -m venv .venv
# En Windows (PowerShell): .\.venv\Scripts\Activate.ps1
# En Linux/macOS:         source .venv/bin/activate

pip install -r requirements.txt
```

### Ejecutar demostración (Antes vs Después):
```bash
python main.py
```

### Ejecutar pruebas automatizadas:
```bash
pytest -v
```
