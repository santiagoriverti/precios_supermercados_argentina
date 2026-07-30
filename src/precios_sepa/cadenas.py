"""Derivación del nombre de cadena desde (id_comercio, id_bandera).

`id_bandera` (1–6) es el banner dentro del comercio, no la cadena completa. La identidad
comercial real es la combinación (id_comercio, id_bandera). Ver docs/CALIDAD_DATOS.md §6.

Regla de oro: nunca descartar un comercio no identificado; se etiqueta "Comercio {id}".
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import CONFIG_DIR


def cargar_mapeo(path: str | Path | None = None) -> pd.DataFrame:
    """Carga config/cadenas.csv (id_comercio, id_bandera, cadena, grupo_corporativo)."""
    path = Path(path) if path else CONFIG_DIR / "cadenas.csv"
    return pd.read_csv(path, dtype={"id_comercio": str, "id_bandera": str})


def asignar_cadena(df: pd.DataFrame, mapeo: pd.DataFrame | None = None) -> pd.DataFrame:
    """Agrega columnas 'cadena' y 'grupo_corporativo' a df (vectorizado, sin apply).

    df debe tener 'id_comercio' e 'id_bandera' como string.
    """
    if mapeo is None:
        mapeo = cargar_mapeo()
    lut_cad = {(r.id_comercio, r.id_bandera): r.cadena for r in mapeo.itertuples()}
    lut_grp = {(r.id_comercio, r.id_bandera): r.grupo_corporativo for r in mapeo.itertuples()}

    key = list(zip(df["id_comercio"], df["id_bandera"]))
    df = df.copy()
    df["cadena"] = pd.Series(key, index=df.index).map(lut_cad)
    df["grupo_corporativo"] = pd.Series(key, index=df.index).map(lut_grp)

    # Fallback: no descartar comercios no identificados.
    falta = df["cadena"].isna()
    df.loc[falta, "cadena"] = "Comercio " + df.loc[falta, "id_comercio"].astype(str)
    df.loc[df["grupo_corporativo"].isna(), "grupo_corporativo"] = df.loc[
        df["grupo_corporativo"].isna(), "cadena"
    ]
    return df
