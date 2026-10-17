# -*- coding: utf-8 -*-
"""
Portfolio Lab — Smart Cache con TTL.

Caché transparente para datos de yfinance basado en SQLite.
Evita descargas repetidas respetando la frescura de los datos.

Uso:
    from portfolio_lab.utils.cache import cached_download, cached_info, cache_stats

    # Reemplaza descargar_con_reintentos — automáticamente cachea
    df = cached_download(['AAPL', 'MSFT'], period='1y')

    # Info de ticker cacheada 24h
    info = cached_info('AAPL')

    # Estadísticas
    cache_stats()

TTLs por defecto:
    - Precios diarios: hasta cierre de mercado (16:30 ET) + 30min
    - Precios intraday: 5 minutos
    - Info/fundamentales: 24 horas
    - Índices/componentes: 7 días
"""

import sqlite3
import hashlib
import json
import pickle
import threading
import time
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, List, Union, Dict, Any

import numpy as np
import pandas as pd

from .logging import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════
# CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════

# TTLs en segundos
TTL_PRECIOS_DIARIOS = 6 * 3600    # 6 horas (datos EOD no cambian hasta cierre)
TTL_PRECIOS_INTRADAY = 5 * 60     # 5 minutos
TTL_INFO_TICKER = 24 * 3600       # 24 horas
TTL_FUNDAMENTALES = 24 * 3600     # 24 horas
TTL_INDICES = 7 * 24 * 3600       # 7 días (composición cambia poco)

# Tamaño máximo de caché en bytes (500MB por defecto)
MAX_CACHE_SIZE = 500 * 1024 * 1024

# Directorio de caché
def _get_cache_dir() -> Path:
    """Retorna el directorio de caché, creándolo si no existe."""
    for base in [Path.home(), Path('/tmp')]:
        cache_dir = base / '.portfolio_lab' / 'cache'
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
            return cache_dir
        except OSError:
            continue
    # Fallback
    fallback = Path('.portfolio_lab_cache')
    fallback.mkdir(exist_ok=True)
    return fallback


# ═══════════════════════════════════════════════════════════════════
# CACHE ENGINE
# ═══════════════════════════════════════════════════════════════════

class SmartCache:
    """
    Motor de caché SQLite con TTL para datos financieros.
    
    Thread-safe para lecturas y escrituras concurrentes mediante RLock + WAL.
    """
    
    _instance = None
    _cls_lock = threading.RLock()
    
    def __new__(cls):
        """Singleton — una sola instancia por proceso."""
        with cls._cls_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        with self._cls_lock:
            if self._initialized:
                return
            
            self._lock = threading.RLock()
            if not hasattr(self, '_db_path') or self._db_path is None:
                self._db_path = _get_cache_dir() / 'market_data.db'
            self._conn = None
            self._init_db()
            self._initialized = True
            self._stats = {'hits': 0, 'misses': 0, 'writes': 0}
    
    def _init_db(self):
        """Inicializa la base de datos SQLite."""
        with self._lock:
            self._conn = sqlite3.connect(
                str(self._db_path),
                check_same_thread=False,
                timeout=10,
            )
            # WAL mode para lecturas concurrentes
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS cache_entries (
                    key         TEXT PRIMARY KEY,
                    data        BLOB NOT NULL,
                    data_type   TEXT NOT NULL,
                    created_at  REAL NOT NULL,
                    expires_at  REAL NOT NULL,
                    size_bytes  INTEGER NOT NULL,
                    metadata    TEXT
                )
            """)
            
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_expires 
                ON cache_entries(expires_at)
            """)
            
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_data_type 
                ON cache_entries(data_type)
            """)
            
            self._conn.commit()
    
    @staticmethod
    def _make_key(prefix: str, params: dict) -> str:
        """Genera una clave de caché determinista."""
        # Serializar params de forma estable
        param_str = json.dumps(params, sort_keys=True, default=str)
        h = hashlib.sha256(param_str.encode()).hexdigest()[:16]
        return f"{prefix}:{h}"
    
    def get(self, key: str) -> Optional[Any]:
        """
        Recupera un valor del caché si existe y no ha expirado.
        
        Returns:
            El valor deserializado o None si no hay hit.
        """
        now = time.time()
        with self._lock:
            row = self._conn.execute(
                "SELECT data, expires_at FROM cache_entries WHERE key = ?",
                (key,)
            ).fetchone()
            
            if row is None:
                self._stats['misses'] += 1
                return None
            
            data_blob, expires_at = row
            
            if now > expires_at:
                # Expirado — eliminar y retornar miss
                self._conn.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                self._conn.commit()
                self._stats['misses'] += 1
                return None
            
            self._stats['hits'] += 1
        return pickle.loads(data_blob)
    
    def put(self, key: str, value: Any, ttl: float, data_type: str = 'generic',
            metadata: dict = None):
        """
        Almacena un valor en el caché.
        
        Args:
            key: Clave de caché
            value: Valor a almacenar (debe ser pickle-serializable)
            ttl: Tiempo de vida en segundos
            data_type: Tipo de dato (para estadísticas y limpieza)
            metadata: Metadatos opcionales (JSON-serializable)
        """
        now = time.time()
        data_blob = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
        size = len(data_blob)
        metadata_json = json.dumps(metadata or {}, default=str)
        
        with self._lock:
            self._conn.execute("""
                INSERT OR REPLACE INTO cache_entries 
                (key, data, data_type, created_at, expires_at, size_bytes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                key, data_blob, data_type, now, now + ttl, size, metadata_json
            ))
            
            self._conn.commit()
            self._stats['writes'] += 1
    
    def invalidate(self, prefix: str = None, data_type: str = None):
        """
        Invalida entradas del caché.
        
        Args:
            prefix: Elimina claves que empiecen con este prefijo
            data_type: Elimina todas las entradas de este tipo
        """
        with self._lock:
            if prefix:
                self._conn.execute(
                    "DELETE FROM cache_entries WHERE key LIKE ?",
                    (f"{prefix}%",)
                )
            elif data_type:
                self._conn.execute(
                    "DELETE FROM cache_entries WHERE data_type = ?",
                    (data_type,)
                )
            else:
                self._conn.execute("DELETE FROM cache_entries")
            
            self._conn.commit()
    
    def cleanup_expired(self) -> int:
        """Elimina entradas expiradas. Retorna el número de eliminadas."""
        with self._lock:
            cursor = self._conn.execute(
                "DELETE FROM cache_entries WHERE expires_at < ?",
                (time.time(),)
            )
            self._conn.commit()
            count = cursor.rowcount
        if count > 0:
            logger.debug(f"Cache cleanup: {count} entradas expiradas eliminadas")
        return count
    
    def cleanup_by_size(self):
        """Si el caché excede MAX_CACHE_SIZE, elimina entradas más antiguas."""
        with self._lock:
            total_size = self._conn.execute(
                "SELECT COALESCE(SUM(size_bytes), 0) FROM cache_entries"
            ).fetchone()[0]
            
            if total_size <= MAX_CACHE_SIZE:
                return
            
            # Eliminar las más antiguas hasta estar bajo el límite
            target = int(MAX_CACHE_SIZE * 0.8)  # Limpiar hasta el 80%
            rows = self._conn.execute(
                "SELECT key, size_bytes FROM cache_entries ORDER BY created_at ASC"
            ).fetchall()
            
            freed = 0
            keys_to_delete = []
            for key, size in rows:
                keys_to_delete.append(key)
                freed += size
                if total_size - freed <= target:
                    break
            
            if keys_to_delete:
                placeholders = ','.join('?' * len(keys_to_delete))
                self._conn.execute(
                    f"DELETE FROM cache_entries WHERE key IN ({placeholders})",
                    keys_to_delete
                )
                self._conn.commit()
                logger.info(f"Cache size cleanup: {len(keys_to_delete)} entradas eliminadas "
                           f"({freed / 1024 / 1024:.1f} MB liberados)")
    
    def stats(self) -> Dict:
        """Retorna estadísticas del caché."""
        now = time.time()
        with self._lock:
            row = self._conn.execute("""
                SELECT 
                    COUNT(*) as entries,
                    COALESCE(SUM(size_bytes), 0) as total_bytes,
                    COUNT(DISTINCT data_type) as types
                FROM cache_entries
                WHERE expires_at > ?
            """, (now,)).fetchone()
            
            type_stats = self._conn.execute("""
                SELECT data_type, COUNT(*), COALESCE(SUM(size_bytes), 0)
                FROM cache_entries 
                WHERE expires_at > ?
                GROUP BY data_type
            """, (now,)).fetchall()
            
            hits = self._stats['hits']
            misses = self._stats['misses']
            writes = self._stats['writes']
        
        total_hits = hits + misses
        hit_rate = hits / total_hits if total_hits > 0 else 0
        
        return {
            'entries': row[0],
            'size_mb': row[1] / 1024 / 1024,
            'types': {t: {'count': c, 'size_mb': s / 1024 / 1024} for t, c, s in type_stats},
            'hits': hits,
            'misses': misses,
            'writes': writes,
            'hit_rate': hit_rate,
            'db_path': str(self._db_path),
        }
    
    def close(self):
        """Cierra la conexión a la base de datos."""
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None
                self._initialized = False
                SmartCache._instance = None


# ═══════════════════════════════════════════════════════════════════
# API PÚBLICA — Wrappers para yfinance
# ═══════════════════════════════════════════════════════════════════

def _get_cache() -> SmartCache:
    """Obtiene la instancia singleton del caché."""
    return SmartCache()


def _compute_ttl_prices(interval: str = '1d') -> float:
    """
    Calcula el TTL apropiado para datos de precios según el intervalo.
    
    Para datos diarios: caché válido hasta el próximo cierre de mercado.
    Para datos intraday: TTL corto (5 min).
    """
    if interval in ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h'):
        return TTL_PRECIOS_INTRADAY
    
    # Para datos diarios, calcular tiempo hasta próximo cierre (16:30 ET)
    try:
        from datetime import timezone as tz
        now_utc = datetime.now(tz.utc)
        # 21:30 UTC = 16:30 ET (sin horario de verano) / 20:30 UTC en verano
        market_close_utc = now_utc.replace(hour=21, minute=30, second=0, microsecond=0)
        
        if now_utc > market_close_utc:
            # Mercado ya cerró hoy — datos válidos hasta mañana
            market_close_utc += timedelta(days=1)
        
        ttl = (market_close_utc - now_utc).total_seconds()
        # Mínimo 30 min, máximo TTL_PRECIOS_DIARIOS
        return max(1800, min(ttl + 1800, TTL_PRECIOS_DIARIOS))
    except Exception:
        return TTL_PRECIOS_DIARIOS


def cached_download(
    tickers: Union[str, List[str]],
    period: str = '1y',
    start: str = None,
    end: str = None,
    interval: str = '1d',
    max_reintentos: int = 3,
    pausa_base: float = 2.0,
    pausa_rate_limit: float = 60.0,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Wrapper cacheado de descargar_con_reintentos.
    
    Drop-in replacement: misma firma + parámetro force_refresh.
    
    Args:
        ... (mismos que descargar_con_reintentos)
        force_refresh: Si True, ignora caché y descarga de nuevo
        
    Returns:
        DataFrame con datos de precios
    """
    from .http import descargar_con_reintentos
    
    cache = _get_cache()
    
    # Normalizar tickers
    if isinstance(tickers, str):
        ticker_list = [tickers.upper()]
    else:
        ticker_list = sorted([t.upper() for t in tickers])

    # Con `start`, `period` no se usa: misma normalización que
    # descargar_con_reintentos, para que la clave no sirva datos de otra ventana
    if start:
        period = None

    # Clave de caché
    params = {
        'tickers': ticker_list,
        'period': period,
        'start': start,
        'end': end,
        'interval': interval,
    }
    key = SmartCache._make_key('prices', params)
    
    # Intentar caché
    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            logger.debug(f"Cache HIT: {len(ticker_list)} tickers, {period}")
            return cached
    
    # Miss — descargar
    logger.debug(f"Cache MISS: descargando {len(ticker_list)} tickers, {period}")
    data = descargar_con_reintentos(
        ticker_list, period=period, start=start, end=end,
        interval=interval, max_reintentos=max_reintentos,
        pausa_base=pausa_base, pausa_rate_limit=pausa_rate_limit,
    )
    
    # Guardar en caché solo si hay datos
    if data is not None and not data.empty:
        ttl = _compute_ttl_prices(interval)
        cache.put(key, data, ttl=ttl, data_type='prices', metadata={
            'tickers': ticker_list,
            'period': period,
            'rows': len(data),
        })
    
    return data


def cached_info(ticker: str, force_refresh: bool = False) -> dict:
    """
    Wrapper cacheado de obtener_info_ticker.
    
    Args:
        ticker: Símbolo
        force_refresh: Si True, ignora caché
        
    Returns:
        Dict con info del ticker
    """
    from .http import obtener_info_ticker
    
    cache = _get_cache()
    key = SmartCache._make_key('info', {'ticker': ticker.upper()})
    
    if not force_refresh:
        cached = cache.get(key)
        if cached is not None:
            return cached
    
    info = obtener_info_ticker(ticker)
    
    if info and len(info) > 5:
        cache.put(key, info, ttl=TTL_INFO_TICKER, data_type='info', metadata={
            'ticker': ticker.upper(),
        })
    
    return info


def cached_batch_sequential(
    tickers: List[str],
    period: str = '1y',
    delay: float = 1.0,
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Wrapper cacheado de descargar_batch_secuencial.
    Cachea cada ticker individualmente para máximo reúso.
    """
    from .http import descargar_ticker_individual
    
    cache = _get_cache()
    all_data = {}
    ttl = _compute_ttl_prices('1d')
    downloaded = 0
    
    for ticker in tickers:
        t = ticker.upper()
        key = SmartCache._make_key('prices_single', {'ticker': t, 'period': period})
        
        if not force_refresh:
            cached = cache.get(key)
            if cached is not None:
                all_data[t] = cached
                continue
        
        # Miss — descargar
        try:
            data = descargar_ticker_individual(t, period, max_reintentos=2)
            if not data.empty:
                close = data['Close'] if 'Close' in data.columns else data.iloc[:, 0]
                all_data[t] = close
                cache.put(key, close, ttl=ttl, data_type='prices_single', metadata={
                    'ticker': t, 'period': period, 'rows': len(data),
                })
                downloaded += 1
            
            if downloaded > 0:
                time.sleep(delay)
        except Exception:
            continue
    
    if not all_data:
        return pd.DataFrame()
    
    return pd.DataFrame(all_data)


# ═══════════════════════════════════════════════════════════════════
# UTILIDADES PÚBLICAS
# ═══════════════════════════════════════════════════════════════════

def obtener_stats() -> Dict:
    """Estadísticas del caché como dict (sin imprimir)."""
    return _get_cache().stats()


def cache_stats():
    """Muestra estadísticas del caché en consola."""
    stats = obtener_stats()

    print("\n" + "=" * 55)
    print("📊 SMART CACHE — Estadísticas")
    print("=" * 55)
    print(f"   📁 DB: {stats['db_path']}")
    print(f"   📦 Entradas válidas: {stats['entries']}")
    print(f"   💾 Tamaño: {stats['size_mb']:.2f} MB")
    print(f"   🎯 Hit rate: {stats['hit_rate']:.1%} "
          f"({stats['hits']} hits / {stats['misses']} misses)")
    print(f"   ✏️ Escrituras: {stats['writes']}")
    
    if stats['types']:
        print("\n   Por tipo:")
        for dtype, info in stats['types'].items():
            print(f"     {dtype:<20} {info['count']:>4} entradas  "
                  f"{info['size_mb']:>6.2f} MB")
    
    print("=" * 55)
    return stats


def cache_clear(data_type: str = None):
    """
    Limpia el caché.
    
    Args:
        data_type: Si se especifica, solo limpia ese tipo.
                   Opciones: 'prices', 'info', 'prices_single', 'indices'
                   Si None, limpia todo.
    """
    cache = _get_cache()
    cache.invalidate(data_type=data_type)
    
    what = data_type or 'completo'
    logger.info(f"Cache limpiado: {what}")
    print(f"   ✓ Cache limpiado: {what}")


def cache_cleanup():
    """Limpieza de mantenimiento: elimina expirados y controla tamaño."""
    cache = _get_cache()
    expired = cache.cleanup_expired()
    cache.cleanup_by_size()
    return expired
