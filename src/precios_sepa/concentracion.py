"""Índices de concentración de mercado por unidad geográfica.

Se usan en el Artículo 1 (prima celíaca) para testear si el sobreprecio sin TACC es mayor
donde el mercado está más concentrado. Ver docs/METODOLOGIA_PRIMA_CELIACA.md §5.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def hhi(participaciones: pd.Series) -> float:
    """Índice Herfindahl-Hirschman (0–10000) a partir de shares (fracciones que suman 1)."""
    s = participaciones.dropna()
    if s.empty:
        return np.nan
    s = s / s.sum()
    return float((s.pow(2).sum()) * 10_000)


def concentracion_por_geo(df_suc: pd.DataFrame, geo_col: str,
                          cadena_col: str = "cadena", peso_col: str | None = None) -> pd.DataFrame:
    """HHI, C4 y n_cadenas por unidad geográfica.

    df_suc: una fila por sucursal (o por sucursal×producto si se pondera por listados).
    peso_col: si None, cuenta sucursales; si se pasa, suma esa columna como peso.
    """
    def _por_grupo(g: pd.DataFrame) -> pd.Series:
        if peso_col is None:
            share = g.groupby(cadena_col).size()
        else:
            share = g.groupby(cadena_col)[peso_col].sum()
        share = share.sort_values(ascending=False)
        total = share.sum()
        frac = share / total if total else share
        return pd.Series({
            "n_cadenas": int((share > 0).sum()),
            "hhi": hhi(frac),
            "c4": float(frac.head(4).sum()),
            "n_sucursales": int(len(g)) if peso_col is None else int(g["id_sucursal"].nunique()),
        })

    return df_suc.groupby(geo_col, dropna=False).apply(_por_grupo).reset_index()


def densidad_comercial(concentracion: pd.DataFrame, provincias: pd.DataFrame,
                       geo_col: str = "PROVINCIA") -> pd.DataFrame:
    """Agrega sucursales por 100.000 habitantes usando la población del Censo 2022."""
    pob = provincias.set_index("provincia")["poblacion_censo2022"]
    out = concentracion.copy()
    out["poblacion"] = out[geo_col].map(pob)
    out["suc_por_100k"] = out["n_sucursales"] / out["poblacion"] * 100_000
    return out
