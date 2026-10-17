# -*- coding: utf-8 -*-
"""
Etiquetas de validación que acompañan a los scans en los menús.

Cada scan lleva, junto a su título, lo que se sabe de su rentabilidad
frente al benchmark medida sin mirar al futuro (septiembre de 2026):

    ⚗️  no rentable · solo laboratorio  medido y sin resultado positivo
    📈  positivo, no significativo      medido y positivo, pero con t < 2
    ❔  sin validar                     no medible con datos gratuitos

Un único sitio: si una medición cambia, se cambia aquí y todos los menús
lo reflejan. `MEDICIONES` guarda el porqué de cada etiqueta.
"""

from typing import Dict, Tuple

LAB = "⚗️ no rentable · solo laboratorio"
POS = "📈 positivo, no significativo"
SIN = "❔ sin validar"
MIXTO = "📈/⚗️ según perfil"

LEYENDA = ("⚗️ medido sin ventaja sobre el benchmark · 📈 medido positivo, "
           "no significativo · ❔ no medible con datos gratuitos")

# clave → (etiqueta, medición que la justifica)
MEDICIONES: Dict[str, Tuple[str, str]] = {
    # ── Menú principal ─────────────────────────────────────────────
    "W": (LAB, "Elige acciones con la Retail Strategy (K), que parte del Market Scanner."),
    "1": (LAB, "Presets fundamentales, concepto medido con SimFin 2021-25: ninguno "
               "positivo frente al SPY salvo Graham (+0,08 pp/trim, 5 acciones)."),
    "2": (LAB, "Mismos presets que el scanner global."),
    "3": (LAB, "Mismos presets que el scanner global."),
    "E": (SIN, "Universo de supervivientes con 30 años de historia: no medible sin sesgo."),
    "F": (LAB, "Sus 8 factores son value/quality/growth/GARP: los cuatro por debajo "
               "del SPY en 2021-25 (value −1,39 pp/trim, GARP −1,89)."),
    "H": (SIN, "Sin histórico de valor liquidativo de los fondos."),
    "I": (MIXTO, "3 de 5 perfiles por encima del SPY en 15 años, ninguno con t ≥ 2."),
    "J": (LAB, "Top 3 países 7,1 %/año frente a ACWI 11,4 % (2009-26), t = −1,69; "
               "también peor que todos los países a partes iguales."),
    "K": (LAB, "Paso 1 = Market Scanner; paso 2 = presets fundamentales."),
    "X": (SIN, "Sin histórico de tokenomics ni de sentimiento."),
    "Y": (LAB, "−0,86 pp/mes frente al universo en 35 meses, t = −1,39."),
    "Z": (SIN, "Los quebrados no están en los datos: backtest optimista sin remedio."),
    "R": (POS, "+0,27 pp/trim frente al SPY (t = 0,30); +0,72 frente a la acción "
               "media (t = 2,04), 2020-26."),
    "N": (SIN, "Las OPVs fracasadas dejan de cotizar y Yahoo no guarda sus precios: "
               "sin histórico honesto. En la literatura, las OPVs rinden menos que sus "
               "comparables a 3-5 años (Ritter 1991; Loughran-Ritter 1995)."),
    # ── Presets fundamentales (scanner global, índice, sector) ─────
    "preset_value": (LAB, "−1,39 pp/trim frente al SPY, t = −1,37."),
    "preset_growth": (LAB, "−0,13 pp/trim frente al SPY, t = −0,13."),
    "preset_quality": (LAB, "−0,71 pp/trim frente al SPY, t = −0,76."),
    "preset_garp": (LAB, "−1,89 pp/trim frente al SPY, t = −1,59."),
    "preset_balanced": (LAB, "−0,74 pp/trim frente al SPY, t = −0,86."),
    "preset_graham": (POS, "+0,08 pp/trim frente al SPY, t = 0,05 (5 acciones de mediana)."),
    "preset_dividend": (SIN, "No medido: no se reprodujo en la prueba con SimFin."),
    "preset_deep": (SIN, "No medido (Piotroski, Altman… sin histórico en la prueba)."),
    # ── Perfiles del Technical Scan (S&P 500, 15 años, trimestral) ─
    "perfil_discovery": (SIN, "Depende del Discovery que se haya ejecutado."),
    "perfil_fuerza_relativa": (POS, "17,7 %/año frente a 15,7 %, t = 0,71; Sharpe menor."),
    "perfil_momentum_quality": (LAB, "14,0 %/año frente a 15,7 %, t = −0,43."),
    "perfil_breakout_squeeze": (POS, "17,9 %/año frente a 15,7 %, t = 0,90."),
    "perfil_mean_reversion": (LAB, "13,4 %/año frente a 15,7 %, t = −0,14; caída −44 %."),
    "perfil_multi_tf": (POS, "23,1 %/año frente a 15,7 %, t = 1,80."),
    # ── Modos del Scan Fundamental (F) ─────────────────────────────
    "fundamental_puro": (LAB, "Sus factores, por debajo del SPY en 2021-25."),
    "pre_explosion": (SIN, "No medido directamente: value (negativo) × precio dormido."),
}


def etiqueta(clave: str) -> str:
    """Texto de la etiqueta, o cadena vacía si la clave no está."""
    entrada = MEDICIONES.get(clave)
    return entrada[0] if entrada else ""


def motivo(clave: str) -> str:
    """Medición que justifica la etiqueta."""
    entrada = MEDICIONES.get(clave)
    return entrada[1] if entrada else ""
