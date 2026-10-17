# -*- coding: utf-8 -*-
"""
Series de FRED sin API key.

La API oficial de FRED pide una clave, pero `fredgraph.csv` sirve cualquier
serie pública sin ella. El programa preguntaba la clave cada vez y, sin ella,
rellenaba el crecimiento con el retorno del SPY y el tramo a 2 años con el
T-bill a 3 meses más medio punto. Aquí se descargan los datos reales, con
caché en disco (`~/.portfolio_lab/cache/fred`).

Fecha de publicación: FRED etiqueta las series mensuales con el día 1 del mes
de REFERENCIA; el IPC de marzo se publica a mediados de abril. En un histórico
que se vaya a cruzar con precios hay que pedir la serie con
`a_fecha_publicacion=True`, que desplaza cada dato al día en que se conocía.
Usar la fecha de referencia es mirar al futuro.
"""

import io
import time
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd
import requests

from .logging import get_logger

logger = get_logger(__name__)

URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={serie}"
_CACHE_DIR = Path.home() / '.portfolio_lab' / 'cache' / 'fred'
TTL_HORAS = 12

# Días naturales entre la fecha con la que FRED etiqueta el dato y el día en
# que se publica. Las mensuales van fechadas el día 1 del mes de referencia;
# las trimestrales, el día 1 del trimestre (el PIB avance sale ~30 días
# después de cerrarlo).
RETRASO_PUBLICACION: Dict[str, int] = {
    # Diarias (H.15, ICE BofA, breakevens): disponibles al día siguiente
    'DGS3MO': 1, 'DGS2': 1, 'DGS5': 1, 'DGS10': 1, 'DGS30': 1,
    'T10Y2Y': 1, 'T10Y3M': 1, 'T10YIE': 1, 'T5YIFR': 1, 'DFF': 1,
    'BAMLH0A0HYM2': 1, 'BAMLC0A0CM': 1, 'DTWEXBGS': 1, 'VIXCLS': 1,
    # Semanales
    'WALCL': 1,      # fechada el miércoles, publicada el jueves
    'NFCI': 5,       # semana hasta el viernes, publicada el miércoles siguiente
    # Mensuales
    'CPIAUCSL': 45, 'CPILFESL': 45, 'PCEPILFE': 60, 'INDPRO': 47,
    'UNRATE': 36, 'PAYEMS': 36, 'M2SL': 56, 'FEDFUNDS': 32, 'UMCSENT': 30,
    'PCEPI': 60, 'PPIFIS': 45, 'RSXFS': 45, 'USREC': 60,
    # Trimestrales
    'GDPC1': 120, 'GDP': 120,
}

# Curva del Tesoro de EE. UU. (constant maturity, en %)
CURVA_TESORO = {'3M': 'DGS3MO', '2Y': 'DGS2', '5Y': 'DGS5', '10Y': 'DGS10', '30Y': 'DGS30'}


def _ruta_cache(serie_id: str) -> Path:
    return Path(_CACHE_DIR) / f"{serie_id}.csv"


def _parsear(texto: str, serie_id: str) -> pd.Series:
    """CSV de fredgraph → Serie. FRED marca los huecos con '.'."""
    df = pd.read_csv(io.StringIO(texto))
    if df.shape[1] < 2:
        raise ValueError(f"CSV sin columna de valores: {texto[:80]!r}")
    fechas = pd.to_datetime(df.iloc[:, 0], errors='coerce')
    valores = pd.to_numeric(df.iloc[:, 1], errors='coerce')
    s = pd.Series(valores.values, index=pd.DatetimeIndex(fechas), name=serie_id)
    return s[s.index.notna()].dropna().sort_index()


def retraso_publicacion(serie_id: str, s: Optional[pd.Series] = None) -> int:
    """
    Días entre la fecha del dato y su publicación. Si la serie no está en
    la tabla se deduce de su frecuencia (diaria 1, mensual 45, trimestral
    120) y se avisa: es una estimación.
    """
    if serie_id in RETRASO_PUBLICACION:
        return RETRASO_PUBLICACION[serie_id]
    if s is None or len(s) < 3:
        return 45
    paso = pd.Series(s.index).diff().dt.days.median()
    dias = 1 if paso <= 7 else (45 if paso <= 40 else 120)
    logger.debug(f"FRED {serie_id}: retraso de publicación estimado en {dias} días")
    return dias


def serie(serie_id: str, desde=None, a_fecha_publicacion: bool = False,
          usar_cache: bool = True, timeout: int = 30) -> Optional[pd.Series]:
    """
    Serie de FRED, o None si no hay forma de obtenerla.

    Args:
        serie_id: Código FRED ('DGS2', 'CPIAUCSL'...).
        desde: Recorta a partir de esta fecha (tras el desplazamiento).
        a_fecha_publicacion: Desplaza cada dato al día en que se publicó.
        usar_cache: Si False, descarga aunque la copia en disco sea reciente.

    Si la descarga falla y hay una copia en disco, se usa diciendo su edad.
    """
    ruta = _ruta_cache(serie_id)
    edad_h = (time.time() - ruta.stat().st_mtime) / 3600 if ruta.exists() else None

    if usar_cache and edad_h is not None and edad_h < TTL_HORAS:
        texto = ruta.read_text(encoding='utf-8')
    else:
        try:
            r = requests.get(URL.format(serie=serie_id), timeout=timeout)
            r.raise_for_status()
            texto = r.text
            cabecera = texto.lstrip()[:40].lower()
            if not (cabecera.startswith('observation_date') or cabecera.startswith('date')):
                raise ValueError(f"la respuesta no es un CSV: {texto[:80]!r}")
            try:
                ruta.parent.mkdir(parents=True, exist_ok=True)
                ruta.write_text(texto, encoding='utf-8')
            except OSError as e:
                logger.debug(f"FRED {serie_id}: no se pudo guardar la caché: {e}")
        except (requests.RequestException, ValueError) as e:
            if edad_h is None:
                logger.warning(f"FRED {serie_id} no disponible: {e}")
                return None
            logger.warning(f"FRED {serie_id}: {e} — uso la copia en disco "
                           f"de hace {edad_h / 24:.0f} días")
            texto = ruta.read_text(encoding='utf-8')

    try:
        s = _parsear(texto, serie_id)
    except (ValueError, pd.errors.ParserError) as e:
        logger.warning(f"FRED {serie_id}: CSV ilegible: {e}")
        return None
    if s.empty:
        logger.warning(f"FRED {serie_id}: la serie llegó vacía")
        return None

    if a_fecha_publicacion:
        s.index = s.index + pd.Timedelta(days=retraso_publicacion(serie_id, s))
    if desde is not None:
        s = s[s.index >= pd.Timestamp(desde)]
    return s


def series(ids: Iterable[str], **kwargs) -> pd.DataFrame:
    """Varias series como columnas. Las que no se obtienen, no aparecen."""
    cols = {i: serie(i, **kwargs) for i in ids}
    cols = {k: v for k, v in cols.items() if v is not None and not v.empty}
    return pd.DataFrame(cols) if cols else pd.DataFrame()


def curva_tesoro(desde=None, **kwargs) -> pd.DataFrame:
    """
    Curva del Tesoro con columnas '3M', '2Y', '5Y', '10Y', '30Y' (en %).
    Los plazos que no se obtienen faltan; nunca se interpolan.
    """
    df = series(CURVA_TESORO.values(), desde=desde, **kwargs)
    return df.rename(columns={v: k for k, v in CURVA_TESORO.items()})
