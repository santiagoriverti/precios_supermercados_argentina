"""Conversión wide→long y escritura de Parquet particionado.

Cada archivo SEPA está en formato WIDE (una columna de precio por día). Se transforma a
LONG (una fila por producto×sucursal×fecha) y se escribe como Parquet particionado por
tipo/anio/mes. DuckDB consulta luego solo las particiones necesarias.

Ver docs/ARQUITECTURA.md §Layout de Parquet.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

from .clean import UMBRAL_CENTAVOS, limpiar_precio
from .io import ArchivoSepa, abrir_csv_gz

_COLS_ID = ["id_comercio", "id_bandera", "id_sucursal", "sucursales_provincia", "id_producto"]
_DTYPE_ID = {c: "str" for c in _COLS_ID}

# precio_YYYYMMDD  (minorista)  |  precio_<medida>_YYYYMMDD  (mayorista)
_RE_PRECIO = re.compile(r"^precio_(?:(?P<medida>uni_iva|uni|bulto_iva|bulto)_)?(?P<fecha>\d{8})$")


def _price_cols(cols) -> list[str]:
    return [c for c in cols if c.startswith("precio_")]


def _primera_col_precio(path) -> str:
    with abrir_csv_gz(path) as g:
        header = g.readline().rstrip("\r\n").split(",")
    return next(c for c in header if c.startswith("precio_"))


def detectar_factor_archivo(archivo: ArchivoSepa) -> tuple[int, float, str]:
    """Detecta el factor (1=pesos, 100=centavos) de UN archivo por la mediana GLOBAL de su
    primera columna de precio, calculada con DuckDB (streaming, sin sesgo de "primeras filas"
    ni memoria alta). El factor es constante dentro de un archivo.

    Devuelve (factor, mediana_global, metodo). Verificado: esta base es toda pesos → factor 1.
    """
    import duckdb

    pcol = _primera_col_precio(archivo.path)
    path = str(archivo.path).replace("\\", "/")
    q = (f"SELECT median(TRY_CAST(nullif(\"{pcol}\", 'NA') AS DOUBLE)) "
         f"FROM read_csv('{path}', all_varchar=1, ignore_errors=1)")
    m = duckdb.sql(q).fetchone()[0]
    m = float(m) if m is not None else float("nan")
    return (100 if (pd.notna(m) and m > UMBRAL_CENTAVOS) else 1), m, "mediana_global"


def wide_a_long(chunk: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Transforma un chunk wide a long. Devuelve columnas:
    id_comercio, id_bandera, id_sucursal, sucursales_provincia, id_producto,
    fecha (date), precio (float32) y —solo mayorista— tipo_precio.

    Eficiente en memoria: la fecha/medida se derivan de los NOMBRES de columna (pocos)
    con un diccionario, no con regex por fila (millones). Se descartan los NA antes de
    mapear la fecha para reducir el pico de RAM.
    """
    from datetime import datetime

    pcols = _price_cols(chunk.columns)
    metas = {c: _RE_PRECIO.match(c) for c in pcols}
    long = chunk.melt(id_vars=_COLS_ID, value_vars=pcols,
                      var_name="_col", value_name="precio")
    long["precio"] = limpiar_precio(long["precio"])
    long = long[long["precio"].notna()]  # descartar sin precio antes de mapear (menos RAM)
    if long.empty:
        return long.drop(columns="_col")

    fecha_map = {c: datetime.strptime(m.group("fecha"), "%Y%m%d").date()
                 for c, m in metas.items() if m}
    long["fecha"] = long["_col"].map(fecha_map)
    if tipo == "mayorista":
        medida_map = {c: m.group("medida") for c, m in metas.items() if m}
        long["tipo_precio"] = long["_col"].map(medida_map)
    return long.drop(columns="_col").reset_index(drop=True)


def procesar_archivo(archivo: ArchivoSepa, out_root: str | Path,
                     chunksize: int = 150_000, limite_filas: int | None = None,
                     verbose: bool = True) -> Path:
    """Lee un ArchivoSepa en chunks, lo pasa a long y lo escribe como Parquet particionado.

    Escribe en: {out_root}/tipo={tipo}/anio={anio}/mes={mes}/parte{parte}.parquet

    Parámetros de memoria (importantes en Colab, ~12 GB):
    - chunksize: filas por chunk. Menor = menor pico de RAM (y más lento).
    - limite_filas: si se pasa, corta tras leer ~N filas de origen (para muestras/demos).

    Los `NA` se leen como número (na_values) en vez de texto → mucha menos RAM.
    """
    import gc

    import pyarrow as pa
    import pyarrow.parquet as pq

    out_dir = Path(out_root) / f"tipo={archivo.tipo}" / f"anio={archivo.anio}" / f"mes={archivo.mes:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"parte{archivo.parte}.parquet"

    # Factor de escala (1=pesos, 100=centavos): constante por archivo, se detecta y aplica.
    factor, med, metodo = detectar_factor_archivo(archivo)

    writer = None
    n = leidas = 0
    with abrir_csv_gz(archivo.path) as g:
        for chunk in pd.read_csv(g, dtype=_DTYPE_ID, na_values=["NA"],
                                 chunksize=chunksize, low_memory=False):
            long = wide_a_long(chunk, archivo.tipo)
            del chunk
            if not long.empty:
                if factor != 1:
                    long["precio"] = (long["precio"] / factor).astype("float32")
                table = pa.Table.from_pandas(long, preserve_index=False)
                if writer is None:
                    writer = pq.ParquetWriter(out_path, table.schema, compression="zstd")
                writer.write_table(table)
                n += len(long)
                del table
            del long
            gc.collect()
            leidas += chunksize
            if limite_filas and leidas >= limite_filas:
                break
    if writer is not None:
        writer.close()
    if verbose:
        extra = f" (muestra ~{leidas:,} filas origen)" if limite_filas else ""
        print(f"  {archivo.tipo} {archivo.periodo} parte{archivo.parte}: {n:,} filas -> "
              f"{out_path.name} | factor={factor} ({metodo}, med={med:.0f}){extra}")
    return out_path
