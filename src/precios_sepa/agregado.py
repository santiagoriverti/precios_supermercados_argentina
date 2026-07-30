"""Agregado MENSUAL de precios (producto × sucursal × mes).

Es la capa de análisis del proyecto: en vez de guardar el precio diario (formato enorme),
se reduce cada archivo a un **precio promedio mensual por (producto, sucursal)** calculando
el promedio por fila sobre las columnas de día (sin `melt` → rápido y con poca RAM).

Alimenta: selección de canastas por cobertura, costo de canastas, ejes geográfico y de
concentración. Ver docs/ARQUITECTURA.md y docs/METODOLOGIA_PRIMA_CELIACA.md.

Salida: data/processed/precios_mensuales/tipo={tipo}/anio={a}/mes={m}.parquet
Columnas: id_comercio, id_bandera, id_sucursal, sucursales_provincia, id_producto,
          precio_prom (float32, pesos), n_dias (int16)
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .clean import PRECIO_MAX_PLAUSIBLE, PRECIO_MIN_PLAUSIBLE, SENTINELAS
from .ingest import _COLS_ID, _DTYPE_ID, _price_cols, detectar_factor_archivo
from .io import ArchivoSepa, abrir_csv_gz

# Para el mayorista se toma el precio unitario con IVA como precio de referencia.
_MAYORISTA_REF = "precio_uni_iva_"


def _limpiar_matriz_precios(p: pd.DataFrame, factor: int) -> pd.DataFrame:
    """Limpia una matriz de columnas de precio: sentinelas y fuera de rango -> NaN, aplica factor."""
    p = p.apply(pd.to_numeric, errors="coerce")
    p = p.mask(p.isin(SENTINELAS))
    p = p.mask((p < PRECIO_MIN_PLAUSIBLE) | (p > PRECIO_MAX_PLAUSIBLE))
    if factor != 1:
        p = p / factor
    return p


def agregar_archivo(archivo: ArchivoSepa, chunksize: int = 400_000,
                    limite_filas: int | None = None) -> pd.DataFrame:
    """Reduce UN archivo (una quincena) a (producto × sucursal) con precio promedio y n_dias.

    Para minorista usa todas las columnas `precio_YYYYMMDD`; para mayorista, las
    `precio_uni_iva_YYYYMMDD` (precio unitario con IVA) como referencia.
    """
    factor, _, _ = detectar_factor_archivo(archivo)
    partes, leidas = [], 0
    with abrir_csv_gz(archivo.path) as g:
        for chunk in pd.read_csv(g, dtype=_DTYPE_ID, na_values=["NA"],
                                 chunksize=chunksize, low_memory=False):
            pcols = _price_cols(chunk.columns)
            if archivo.tipo == "mayorista":
                pcols = [c for c in pcols if c.startswith(_MAYORISTA_REF)]
            p = _limpiar_matriz_precios(chunk[pcols], factor)
            out = chunk[_COLS_ID].copy()
            out["precio_prom"] = p.mean(axis=1).astype("float32")
            out["n_dias"] = p.notna().sum(axis=1).astype("int16")
            out = out[out["n_dias"] > 0]
            partes.append(out)
            leidas += chunksize
            if limite_filas and leidas >= limite_filas:
                break
    return pd.concat(partes, ignore_index=True) if partes else pd.DataFrame()


def agregar_mes(archivos_mes: list[ArchivoSepa], **kw) -> pd.DataFrame:
    """Combina las partes (parte1 + parte2) de un mes en un promedio mensual ponderado por n_dias."""
    dfs = [agregar_archivo(a, **kw) for a in archivos_mes]
    df = pd.concat(dfs, ignore_index=True)
    df["_w"] = df["precio_prom"] * df["n_dias"]
    g = (df.groupby(_COLS_ID, sort=False, observed=True)
           .agg(_sw=("_w", "sum"), n_dias=("n_dias", "sum")).reset_index())
    g["precio_prom"] = (g["_sw"] / g["n_dias"]).astype("float32")
    return g.drop(columns="_sw")


def construir_mensual(archivos: list[ArchivoSepa], out_root: str | Path,
                      verbose: bool = True, **kw) -> None:
    """Construye el agregado mensual para todos los (tipo, mes) de `archivos`."""
    out_root = Path(out_root)
    claves = sorted({(a.tipo, a.anio, a.mes) for a in archivos})
    for tipo, anio, mes in claves:
        grupo = [a for a in archivos if (a.tipo, a.anio, a.mes) == (tipo, anio, mes)]
        df = agregar_mes(grupo, **kw)
        out_dir = out_root / f"tipo={tipo}" / f"anio={anio}" / f"mes={mes:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "datos.parquet"
        df.to_parquet(out_path, index=False, compression="zstd")
        if verbose:
            print(f"  {tipo} {anio}-{mes:02d}: {len(df):,} (producto x sucursal) -> {out_path.name}")
