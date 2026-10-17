# 📊 Portfolio Lab — Architecture & Technical Showcase

[![CI](https://img.shields.io/badge/CI-passing%20%28Python%203.11%20%7C%203.12%29-brightgreen.svg)](samples/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Scale](https://img.shields.io/badge/codebase-~104.000%20LOC%20%7C%20247%20modules-informational.svg)](#%EF%B8%8F-arquitectura-del-proyecto)
[![Tests](https://img.shields.io/badge/tests-~2.000%20passed%20%28pytest%29-brightgreen.svg)](samples/conftest.py)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Side Project](https://img.shields.io/badge/project-personal%20side--project-8a2be2.svg)](#)

> [!IMPORTANT]
> **🔒 Nota sobre Propiedad Intelectual y Muestras de Código (*Code Samples*)**
>
> **Portfolio Lab** es un ***side-project* personal e independiente de I+D cuantitativa**. Por motivos de protección de propiedad intelectual y modelos cuantitativos propietarios (*alpha*), el código fuente completo (**~104.000 líneas de código en 247 módulos Python y +2.000 tests unitarios**) se mantiene en un repositorio privado (Nachovelher/Portfolio_lab).
>
> Este repositorio público actúa como **escaparate técnico y de arquitectura** e incluye:
> - La documentación completa de ingeniería, diseño de módulos y metodología cuantitativa.
> - La definición de empaquetado y dependencias de producción ([pyproject.toml](pyproject.toml), [equirements.txt](requirements.txt)).
> - **Muestras reales de código de infraestructura y testing en [samples/](samples/):**
>   - [samples/conftest.py](samples/conftest.py) — Aislamiento efímero de HOME/USERPROFILE y verificación criptográfica de integridad para los ~2.000 tests.
>   - [samples/fred.py](samples/fred.py) — Cliente macroeconómico de FRED sin API key con alineación *Point-in-Time* a fecha real de publicación (_fecha_publicacion=True) para eliminar *look-ahead bias*.
>   - [samples/cache.py](samples/cache.py) — SmartCache SQLite *thread-safe* con TTLs dinámicos ajustados al cierre de mercado (16:30 ET).
>   - [samples/etiquetas_validacion.py](samples/etiquetas_validacion.py) — Registro centralizado de validación empírica *walk-forward* fuera de muestra en la interfaz.
>   - [samples/ci.yml](samples/ci.yml) — Pipeline de Integración Continua (GitHub Actions matrix Python 3.11 / 3.12).
>
> *El repositorio privado completo está disponible para demostración en vivo o revisión técnica durante procesos de selección.*

---
Laboratorio cuantitativo de investigación de factores, selección de activos, optimización de carteras, gestión dinámica del riesgo y seguimiento de P&L real multi-divisa en Python.

Diseñado bajo una premisa central: **ningún número se acepta sin auditar antes sus sesgos**. Cada motor de backtest, escáner e indicador está construido para eliminar el *look-ahead bias*, cuantificar el *survivorship bias* y declarar en la propia interfaz qué estrategias tienen respaldo estadístico fuera de muestra y cuáles son únicamente herramientas de exploración.

---

## 🎯 Pilares de Ingeniería Cuantitativa

### 1. Higiene Estricta contra Sesgos (*Anti-Look-Ahead & Point-in-Time*)
* **Ejecución en $t+1$:** Las señales de cobertura y régimen (medias móviles, índice de turbulencia de Mahalanobis, HMM con filtrado recursivo y umbrales expansivos) se calculan al cierre de $t$ y solo pueden alterar la exposición a partir del retorno de $t+1$.
* **Universo S&P 500 *Point-in-Time* con ex-miembros (`scanner/index_history.py`):** Reconstruye la composición histórica fecha a fecha deshaciendo altas y bajas, e incorpora a los ex-miembros que abandonaron el índice para evitar inflar el alfa con los ganadores actuales (efecto medido en momentum 15 años: de $38{,}4\%$ CAGR con sesgo a $20{,}4\%$ PIT con costes).
* **Fundamentales y Macro con retraso de publicación (`utils/fred.py`, `data/fundamentals_historical.py`):** Las series macroeconómicas de FRED se alinean en su fecha real de publicación (`a_fecha_publicacion=True`) y los estados financieros históricos aplican un *lag* de 90 días. Prohibición total de `bfill()` en precios y tipos de cambio (verificado mediante tests estáticos sobre el código).

### 2. Etiquetas de Validación Empírica en la Interfaz (`ui/etiquetas_validacion.py`)
Cada escáner muestra junto a su título el resultado de su validación *walk-forward* fuera de muestra frente a su benchmark, medida con estadístico $t$ pareado por periodo en [`validaciones/`](validaciones/):
* `📈 positivo, no significativo` — Bate al benchmark o al universo equiponderado en la muestra histórica, con su estadístico $t$ reportado explícitamente.
* `⚗️ no rentable · solo laboratorio` — Medido sin ventaja neta sobre el índice tras costes y corrección de universo; útil como filtro exploratorio, no como sistema automático.
* `❔ sin validar` — Estrategia cuya validación honesta requiere datos de empresas deslistadas/quebradas que las fuentes gratuitas no conservan (declarado abiertamente en lugar de mostrar un backtest engañoso).

### 3. Contabilidad Multi-Divisa y Cartera Real (`utils/fx.py`, `portfolio/pnl.py`)
* **Conciliación de tres monedas por activo (`asymmetric/currency.py`):** Distingue entre moneda de cotización (incluyendo ajuste automático de peniques británicos `GBp / 100`), moneda de capitalización (`marketCap`) y moneda de los estados financieros (`financialCurrency`, p. ej. empresas europeas o japonesas que reportan en USD/IFRS).
* **P&L Real auditado e importación de Interactive Brokers (`data/importador_broker.py`):** Importa extractos *Activity Statement* y *Flex Query* con deduplicación idempotente. Calcula P&L por **coste medio ponderado** y por **FIFO** (criterio fiscal en España), desglosando el retorno del activo frente al efecto divisa mediante el tipo de cambio histórico exacto de cada compra y cada venta.

---

## 🧭 Mapa de Módulos y Escáneres

### 🔎 Escáneres Especializados (Paquetes Autónomos y Motores de Selección)
| Opción | Módulo | Descripción |
| :---: | :--- | :--- |
| **`W`** | `ui/wizard.py` | **Asistente guiado (7 pasos):** perfila horizonte/riesgo/divisa, evalúa contexto de mercado, construye y optimiza la cartera y configura su vigilancia diaria (`--check` + webhook). |
| **`Y`** | [`asymmetric/`](asymmetric/README.md) | **Asimetría positiva (Swing 20 sesiones):** compresión de volatilidad + stop estructural bajo *swing low* fractal sin *look-ahead*, ratio *gap/stop*, estudio de eventos en múltiplos $R$ con encogimiento Bayesiano hacia el universo y validación *walk-forward* mensual (`python -m portfolio_lab.asymmetric --validate`). |
| **`Z`** | [`fallen/`](fallen/README.md) | **Caídos con suelo (S&P 1500 + Internacional):** criba en dos fases (caída $\ge 60\%$ estabilizada sobre 52w low $\rightarrow$ solvencia de balance, caja neta/FCF positivo y **Piotroski F-Score** $\ge 7/9$). |
| **`R`** | `shrinkers/` | **Encogedores (Recompras netas):** detecta empresas que reducen su número de acciones en circulación corrigiendo *splits*, *spin-offs* y estructuras multi-clase con respaldo de caja (*cash backing*). Único factor del laboratorio con exceso estadísticamente significativo frente a la acción media del S&P 500 PIT ($+0{,}72\text{ pp/trim}$, $t = 2{,}04$). |
| **`N`** | `recien/` | **Recién llegados (OPVs EE. UU.):** calendario de salidas a bolsa en Nasdaq (filtrando SPACs), crecimiento anual implícito exigido por EV/Ventas a 10 años, atención en Wikipedia/Wikidata, tono VADER en titulares y tracción en GitHub/App Store. |
| **`X`** | `crypto/` | **Escáner de Criptoactivos:** análisis fundamental de *tokenomics* y riesgo de dilución (FDV/MCap, oferta circulante, liquidez real en libro), sentimiento multi-fuente, actividad de repositorios en GitHub, ficha de auditoría por moneda y análisis de sensibilidad a los pesos. |
| **`1–3, E–K`** | `scanner/` | **Scanners Clásicos y Factoriales:** Global (Finviz + países), Componentes de Índices, Sectores, *Tulkas* (supervivientes 30+ años), *Quality × Value* (puro o pre-explosión), *Holding Scan* (conglomerados/CEFs/BDCs), *Technical Multi-Factor Scan* y *Market Scanner* por países. |

### 💼 Optimización, Riesgo,Validación Estadística y Macro
* **Optimización (`portfolio/optimizer.py`, `portfolio/robust_optimizer.py`):** Markowitz (Max Sharpe, Mínima Varianza), Risk Parity, **HRP** (Hierarchical Risk Parity), **CVaR**, **Kelly**, **Black-Litterman** con *views* cuantitativas y shrinkage de covarianza (Ledoit-Wolf). Comparativa y selección automática por **Sharpe fuera de muestra** (70% train / 30% OOS).
* **Gestión Dinámica del Riesgo (`portfolio/risk_strategies.py`, `portfolio/risk_strategies_dynamic.py`):** Stop-loss por medias móviles, *Turbulence Index* (distancia de Mahalanobis con umbral expansivo), rotación a activos refugio, CPPI y *Meta-Portfolio* con validación *walk-forward* que re-optimiza pesos en cada ventana de entrenamiento.
* **Validación Estadística y Stress Testing (`analysis/statistical_tests.py`, `portfolio/stress_test.py`):** Stationary Bootstrap (Politis-Romano), corrección por comparaciones múltiples de **Romano-Wolf**, **CPCV** (*Combinatorial Purged Cross-Validation*), **Deflated Sharpe Ratio** y replay histórico sobre **13 crisis reales (1973–2023)** ponderado por cobertura efectiva de la cartera.
* **Macro y Materias Primas (`analysis/macro_regime.py`, `analysis/commodity_advanced.py`):** Régimen de Crecimiento/Inflación con datos reales de FRED (sin API key) e indicador CISS del BCE, ciclos de Kondratieff, y matriz de materias primas con *carry* medido sobre la curva real de futuros de Yahoo y posicionamiento COT de la CFTC.

---

## ⚙️ Arquitectura del Proyecto

```text
portfolio_lab/                  # ~104.000 LOC en 247 módulos Python
├── main.py                     # Dispatcher de menú interactivo y modos CLI (--check, --backup, --restore)
├── config.py                   # Configuración global, perfiles de costes de brokers (IBKR/DEGIRO) y RF
├── ui/                         # Menús interactivos en español, asistente guiado (wizard) y gráficos
├── scanner/                    # Motores de screening, Factor Discovery, Factor Backtest y S&P 500 PIT
├── analysis/                   # Modelos cuantitativos: fundamentales, factores, regímenes, macro, tests
├── portfolio/                  # Optimizadores, backtesters, estrategias de riesgo, P&L FIFO y tracker
├── asymmetric/                 # Paquete autónomo: escáner de asimetría positiva en R + walk-forward
├── fallen/                     # Paquete autónomo: caídos con suelo (Piotroski F-score + solvencia)
├── shrinkers/                  # Paquete autónomo: recompras netas ajustadas por splits + walk-forward
├── recien/                     # Paquete autónomo: análisis de OPVs recientes, expectativas y atención
├── crypto/                     # Paquete autónomo: tokenomics, sentimiento, GitHub dev y sensibilidad
├── validaciones/               # Scripts reproducibles que auditan y justifican las etiquetas de menú
├── data/                       # Persistencia SQLite con migraciones (PRAGMA user_version), IBKR y FMP
├── utils/                      # SmartCache SQLite thread-safe, cliente HTTP/FRED, conversión FX e i18n
├── herramientas/               # Explorador automático de menús en procesos aislados (fuzzing/QA)
└── tests/                      # ~2.000 tests (pytest) en 69 archivos con aislamiento de HOME
```

---

## 🚀 Instalación y Uso

### 1. Instalación

```bash
git clone https://github.com/Nachovelher/Portfolio_lab.git portfolio_lab
cd portfolio_lab

pip install -r requirements.txt        # Dependencias principales
pip install -r requirements-dev.txt    # Desarrollo (+ pytest, pytest-cov, flake8)
pip install -e .                       # Instala el comando CLI `portfolio-lab`
```

Extras opcionales declarados en [`pyproject.toml`](pyproject.toml):

```bash
pip install -e ".[optim]"    # cvxpy (optimización convexa avanzada)
pip install -e ".[quant]"    # arch (GARCH), hmmlearn
pip install -e ".[reports]"  # reportlab (generación de informes PDF)
pip install -e ".[crypto]"   # vaderSentiment, feedparser, praw
```

### 2. Ejecución Interactiva y Modos CLI

```bash
# Menú interactivo principal
portfolio-lab
# o desde el directorio padre:
python -m portfolio_lab

# Escáneres autónomos por CLI directa
python -m portfolio_lab.asymmetric --top 20
python -m portfolio_lab.asymmetric --validate
python -m portfolio_lab.fallen --universe sp1500
python -m portfolio_lab.shrinkers --validate
python -m portfolio_lab.recien
```

### 3. Vigilancia Automatizada (*Headless Health Check*) y Backups

Evalúa tus carteras guardadas sin abrir el menú (ideal para `cron` o Programador de tareas de Windows), registrando un snapshot en SQLite y enviando alertas a Slack/Discord/Teams si se superan umbrales de *drift*, *drawdown*, volatilidad o cambio de régimen del benchmark:

```bash
python -m portfolio_lab --check     # Exit codes: 0 = OK, 1 = Alertas, 2 = Sin datos
python -m portfolio_lab --backup    # Exporta toda la base de datos SQLite a JSON
python -m portfolio_lab --restore ruta_backup.json
```

---

## 🧪 Calidad y Suite de Tests

La suite cuenta con **~2.000 tests automatizados** en 69 ficheros (`tests/`). [`tests/conftest.py`](tests/conftest.py) redirige `HOME`/`USERPROFILE` a un entorno efímero antes de importar ningún módulo y verifica al cierre de la sesión que ningún archivo real del usuario haya sido tocado.

```bash
pytest tests --ignore=tests/test_integration.py   # Suite completa sin red (CI)
pytest --cov=portfolio_lab                        # Cobertura de código
flake8 .                                          # Análisis estático funcional
```

---

## ⚠️ Aviso Legal (*Disclaimer*)

Este software se proporciona **únicamente con fines educativos, académicos y de investigación cuantitativa**. Ningún ranking, puntuación, simulación, backtest o métrica generada por **Portfolio Lab** constituye asesoramiento financiero, recomendación de inversión ni oferta de compra o venta de activos. Rentabilidades pasadas o simuladas no garantizan rentabilidades futuras.

## 📄 Licencia

Distribuido bajo la licencia **GNU General Public License v3.0 (GPLv3)**. Consulta el archivo [`LICENSE`](LICENSE) para más detalles.
