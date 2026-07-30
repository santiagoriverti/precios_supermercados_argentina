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


# ── Concentración ESPACIAL (lat/lon) ───────────────────────────────────────────
# Métricas basadas en la geometría de los puntos de venta (no solo participación de cadenas).
# Ver docs/METODOLOGIA_PRIMA_CELIACA.md §5.

_RADIO_TIERRA_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    """Distancia haversine en km (acepta escalares o arrays de numpy, en grados)."""
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * _RADIO_TIERRA_KM * np.arcsin(np.sqrt(a))


def metricas_espaciales(suc: pd.DataFrame, radios_km=(1, 3, 5),
                        lat_col: str = "sucursales_latitud", lon_col: str = "sucursales_longitud",
                        cadena_col: str = "cadena") -> pd.DataFrame:
    """Para cada sucursal, calcula métricas de competencia espacial a partir de lat/lon:

    - `dist_vecino_km`: distancia a la sucursal más cercana (cualquier cadena).
    - `dist_vecino_otra_cadena_km`: a la sucursal más cercana de OTRA cadena (competencia real).
    - `n_en_{R}km`: nº de sucursales dentro de R km.
    - `n_otras_cadenas_en_{R}km`: nº de sucursales de otras cadenas dentro de R km.

    Menor distancia / más competidores => mercado más competido (menos concentrado).
    Usa fuerza bruta O(n²); con ~3.600 sucursales es instantáneo. Para N grande, migrar a
    scipy.spatial.cKDTree con métrica de cuerda.
    """
    d = suc.dropna(subset=[lat_col, lon_col]).reset_index(drop=True).copy()
    lat = d[lat_col].to_numpy(float)
    lon = d[lon_col].to_numpy(float)
    cad = d[cadena_col].to_numpy(str) if cadena_col in d.columns else np.array([""] * len(d))
    n = len(d)

    dist_min = np.full(n, np.nan)
    dist_min_otra = np.full(n, np.nan)
    cnt = {r: np.zeros(n, int) for r in radios_km}
    cnt_otra = {r: np.zeros(n, int) for r in radios_km}

    for i in range(n):
        dk = haversine_km(lat[i], lon[i], lat, lon)
        dk[i] = np.inf  # excluir la propia
        dist_min[i] = dk.min()
        otra = cad != cad[i]
        if otra.any():
            dist_min_otra[i] = dk[otra].min()
        for r in radios_km:
            en_r = dk <= r
            cnt[r][i] = int(en_r.sum())
            cnt_otra[r][i] = int((en_r & otra).sum())

    d["dist_vecino_km"] = dist_min
    d["dist_vecino_otra_cadena_km"] = dist_min_otra
    for r in radios_km:
        d[f"n_en_{r}km"] = cnt[r]
        d[f"n_otras_cadenas_en_{r}km"] = cnt_otra[r]
    return d
