"""Carga y reparación de los maestros de productos y sucursales.

- Repara el mojibake de encoding en columnas de texto.
- Normaliza provincias contra config/provincias.csv (código ISO como fuente primaria) y,
  ante nombres inconsistentes, reclasifica por coordenadas SIN descartar sucursales.

Ver docs/CALIDAD_DATOS.md §2 y §5.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import CONFIG_DIR
from .clean import reparar_mojibake

_COLS_TEXTO_PROD = ["producto_descripcion", "producto_marca", "rubro", "categoria", "subcategoria"]


def cargar_productos(path: str | Path) -> pd.DataFrame:
    """Carga 'Maestro de Productos Interno.xlsx' y repara el texto."""
    df = pd.read_excel(path, sheet_name=0, dtype={"producto_sepa_id": str, "producto_ean": str})
    for c in _COLS_TEXTO_PROD:
        if c in df.columns:
            df[c] = reparar_mojibake(df[c])
    df["id_producto"] = df["producto_sepa_id"].astype(str)
    return df


def cargar_sucursales(path: str | Path) -> pd.DataFrame:
    """Carga 'maestro_sucursales_completo.xlsx', repara texto y normaliza provincia/región."""
    df = pd.read_excel(path, sheet_name=0,
                       dtype={"id_comercio": str, "id_bandera": str, "id_sucursal": str})
    for c in ("PROVINCIA", "REGION", "sucursales_localidad"):
        if c in df.columns:
            df[c] = reparar_mojibake(df[c])
    prov = pd.read_csv(CONFIG_DIR / "provincias.csv")
    df = df.merge(prov, left_on="sucursales_provincia", right_on="iso_3166_2", how="left")
    # TODO: reclasificación por bounding box de coordenadas para sucursales sin match ISO.
    return df
