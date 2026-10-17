# -*- coding: utf-8 -*-
"""Configuración global de pytest para Portfolio Lab.

AISLAMIENTO DEL HOME (Sprint 24.4)
----------------------------------
La suite escribía en `~/.portfolio_lab` del usuario. El JSON legacy de
portfolios real acumulaba portfolios de test ('test_port', 'port_a', 'p1'...)
y, desde que la migración retira el JSON tras migrar, cada ejecución de pytest
renombraba el fichero real: medido, seis renombrados en una tarde. La base de
datos se salvaba porque los tests parchean su ruta, pero nada más lo hacía.

Ahora el home de toda la sesión es un directorio temporal, y al terminar se
comprueba que los ficheros reales no han cambiado: si cambian, la sesión falla.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

# ── 1. Home real: se anota ANTES de redirigir, para vigilarlo ──
_HOME_REAL = Path(os.path.expanduser('~'))
_VIGILADOS = [
    _HOME_REAL / '.portfolio_lab' / 'portfolios.db',
    _HOME_REAL / '.portfolio_lab' / 'portfolios_cache.json',
    _HOME_REAL / '.portfolio_lab' / 'strategies',
    _HOME_REAL / 'portfolio_lab_output',
]


def _huella():
    huella = {}
    for ruta in _VIGILADOS:
        if ruta.is_dir():
            huella[str(ruta)] = sorted(
                (str(f), f.stat().st_mtime) for f in ruta.rglob('*') if f.is_file())
        elif ruta.exists():
            huella[str(ruta)] = (ruta.stat().st_mtime, ruta.stat().st_size)
        else:
            huella[str(ruta)] = None
    return huella


_HUELLA_INICIAL = _huella()

# ── 2. Home de la sesión: temporal ──
_HOME_TESTS = Path(tempfile.mkdtemp(prefix='portfolio_lab_tests_home_'))
for _var in ('HOME', 'USERPROFILE'):
    os.environ[_var] = str(_HOME_TESTS)

# Asegurar que el paquete es importable (tanto el padre como la raíz)
project_root = Path(__file__).resolve().parent.parent
for _p in (project_root.parent, project_root):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

# ── 3. Constantes de módulo calculadas al importar ──
# El paquete se importa antes que este conftest (los tests viven dentro de
# él), así que las rutas fijadas a nivel de módulo ya apuntan al home real.
from portfolio_lab.data import fundamentals_historical as _fh  # noqa: E402
from portfolio_lab.scanner import factor_strategies as _fs  # noqa: E402
from portfolio_lab.scanner import index_history as _ih  # noqa: E402
from portfolio_lab.utils import fred as _fred  # noqa: E402

_fh._CACHE_DIR = _HOME_TESTS / '.portfolio_lab' / 'fmp_cache'
_fs._STRATEGIES_DIR = str(_HOME_TESTS / '.portfolio_lab' / 'strategies')
_ih._CACHE_DIR = _HOME_TESTS / '.portfolio_lab' / 'index_history'
_fred._CACHE_DIR = _HOME_TESTS / '.portfolio_lab' / 'cache' / 'fred'


def pytest_sessionfinish(session, exitstatus):
    """Falla la sesión si algún test tocó los ficheros reales del usuario."""
    cambios = [ruta for ruta, antes in _HUELLA_INICIAL.items()
               if _huella().get(ruta) != antes]
    if cambios:
        sys.stderr.write(
            "\n\n!!! LOS TESTS HAN MODIFICADO FICHEROS REALES DEL USUARIO:\n    "
            + "\n    ".join(cambios) + "\n")
        session.exitstatus = 1
    shutil.rmtree(_HOME_TESTS, ignore_errors=True)
