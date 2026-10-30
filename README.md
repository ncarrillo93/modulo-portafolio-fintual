# Módulo de Gestión de Cartera de Inversión y Motor de Rebalanceo

Solución de ingeniería de software para el módulo de administración de portafolios y rebalanceo algorítmico de inversiones (estilo Fintual), desarrollada en **Python 3.11** bajo principios de diseño **SOLID**, **Clean Code**, **Pydantic (v2)** y estricta separación de responsabilidades.

---

## 1. Principios de Diseño y Arquitectura

* **Single Responsibility Principle (SRP):**
  * `Asset` encapsula las propiedades de mercado y validación de precios.
  * `Portfolio` gestiona la asignación porcentual y tenencia de acciones.
  * `RebalanceService` es un servicio *stateless* responsable exclusivo del cálculo algorítmico de rebalanceo.
* **Separación de Responsabilidades (SoC):** La capa de dominio (`models.py`) está desacoplada de la capa de cálculo/servicio (`rebalance.py`).
* **Tipado Estricto & Validación:** Uso de `pydantic.dataclasses.dataclass` con validación en tiempo de ejecución, control de precios positivos (`> 0.0`), normalización de mantisa a 2 decimales y pesos complementarios a 1.0 (tolerancia `1e-6`).
* **Compatibilidad de Nomenclatura:** Implementación nativa en `snake_case` (PEP 8) con propiedades y métodos alias en `camelCase` (`currentPrice`, `getCurrentPrice`, `targetAllocations`).

---

## 2. Estructura del Proyecto

```text
├── models.py           # Modelos de datos (Asset, Portfolio, RebalanceInstruction, ActionType) y excepciones
├── rebalance.py        # Motor algorítmico de rebalanceo (RebalanceService)
├── main.py             # Script ejecutable de diagnóstico interactivo (Antes vs Después) con auto-instalador
├── test_portfolio.py   # Suite de 18 pruebas unitarias automatizadas con pytest
├── requirements.txt    # Especificación de dependencias (pydantic, pytest)
├── pyproject.toml      # Configuración de pruebas y empaquetado
├── Solicitud.md        # Especificación detallada de contratos, tipos y requerimientos
└── README.md           # Guía general de la solución
```

---

## 3. Modelo Matemático y Motor de Rebalanceo

El método `rebalance` calcula las órdenes necesarias para alinear el portafolio con sus pesos objetivo:

1. **Valor Total de Mercado:**
   $$\text{Valor Total} = \sum (\text{acciones}_i \times \text{precio}_i)$$
2. **Posición Ideal por Activo:**
   $$\text{Valor Ideal}_i = \text{Valor Total} \times \text{peso\_objetivo}_i$$
   $$\text{Acciones Ideales}_i = \frac{\text{Valor Ideal}_i}{\text{precio}_i}$$
3. **Desviación y Clasificación:**
   $$\Delta \text{Acciones}_i = \text{Acciones Ideales}_i - \text{Acciones Actuales}_i$$
   * Si $|\Delta \text{Acciones}_i| < 1\times 10^{-4}$ (umbral épsilon): Posición en equilibrio $\rightarrow$ `HOLD` (`shares = 0.0`).
   * Si $\Delta \text{Acciones}_i > 0$: Subponderado $\rightarrow$ `BUY`.
   * Si $\Delta \text{Acciones}_i < 0$: Sobreponderado o liquidación total $\rightarrow$ `SELL`.
4. **Prioridad Financiera:** Las órdenes `SELL` se priorizan para generar liquidez antes de ejecutar las órdenes `BUY`.

---

## 4. Instalación y Ejecución

### Opción 1: Ejecución Directa (Auto-instalable)
`main.py` detecta automáticamente si faltan dependencias e intenta instalarlas en el entorno activo:
```bash
python main.py
```

### Opción 2: Instalación Manual vía pip
```bash
pip install -r requirements.txt
```

### Ejecutar Pruebas Automatizadas:
```bash
pytest -v
```
*18 tests pasando al 100% cubriendo validaciones de precios, tolerancia flotante, órdenes fraccionarias, activos huérfanos y cartera vacía.*

