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

from .clean import limpiar_precio
from .io import ArchivoSepa, abrir_csv_gz

_COLS_ID = ["id_comercio", "id_bandera", "id_sucursal", "sucursales_provincia", "id_producto"]
_DTYPE_ID = {c: "str" for c in _COLS_ID}

# precio_YYYYMMDD  (minorista)  |  precio_<medida>_YYYYMMDD  (mayorista)
_RE_PRECIO = re.compile(r"^precio_(?:(?P<medida>uni_iva|uni|bulto_iva|bulto)_)?(?P<fecha>\d{8})$")


def _price_cols(cols) -> list[str]:
    return [c for c in cols if c.startswith("precio_")]


def wide_a_long(chunk: pd.DataFrame, tipo: str) -> pd.DataFrame:
    """Transforma un chunk wide a long. Devuelve columnas:
    id_comercio, id_bandera, id_sucursal, sucursales_provincia, id_producto,
    fecha (date), precio (float32) y —solo mayorista— tipo_precio.
    """
    pcols = _price_cols(chunk.columns)
    long = chunk.melt(id_vars=_COLS_ID, value_vars=pcols,
                      var_name="_col", value_name="precio")
    meta = long["_col"].str.extract(_RE_PRECIO)
    long["fecha"] = pd.to_datetime(meta["fecha"], format="%Y%m%d").dt.date
    if tipo == "mayorista":
        long["tipo_precio"] = meta["medida"]
    long["precio"] = limpiar_precio(long["precio"])
    long = long.drop(columns="_col")
    # Descartar filas sin precio (ahorra mucho espacio; el "no listado" no aporta al análisis)
    long = long[long["precio"].notna()].reset_index(drop=True)
    return long


def procesar_archivo(archivo: ArchivoSepa, out_root: str | Path,
                     chunksize: int = 300_000, verbose: bool = True) -> Path:
    """Lee un ArchivoSepa en chunks, lo pasa a long y lo escribe como Parquet particionado.

    Escribe en: {out_root}/tipo={tipo}/anio={anio}/mes={mes}/parte{parte}.parquet
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    out_dir = Path(out_root) / f"tipo={archivo.tipo}" / f"anio={archivo.anio}" / f"mes={archivo.mes:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"parte{archivo.parte}.parquet"

    writer = None
    n = 0
    with abrir_csv_gz(archivo.path) as g:
        for chunk in pd.read_csv(g, dtype=_DTYPE_ID, chunksize=chunksize, low_memory=False):
            long = wide_a_long(chunk, archivo.tipo)
            if long.empty:
                continue
            table = pa.Table.from_pandas(long, preserve_index=False)
            if writer is None:
                writer = pq.ParquetWriter(out_path, table.schema, compression="zstd")
            writer.write_table(table)
            n += len(long)
    if writer is not None:
        writer.close()
    if verbose:
        print(f"  {archivo.tipo} {archivo.periodo} parte{archivo.parte}: {n:,} filas -> {out_path.name}")
    return out_path
