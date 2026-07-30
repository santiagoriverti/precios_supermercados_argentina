"""Canastas (media y celiaca), costos y series historicas.

La canasta se define en `config/canastas/canastas.xlsx` (EDITABLE: modificar las cantidades
a mano) con su export `canastas.csv`. Una fila por grupo de consumo, con el producto de la
canasta media y su equivalente sin TACC. Ver docs/CANASTAS.md y docs/METODOLOGIA_PRIMA_CELIACA.md.

Costo por unidad geografica y mes:
  costo_X(g,m) = Σ_grupo (cantidad_mensual / envase_X) * precio(ean_X, g, m)
donde el precio faltante en g se imputa con el precio nacional del mismo producto y mes.
La prima celiaca = costo_celiaca / costo_media - 1.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import CONFIG_DIR


def cargar_canastas(path: str | Path | None = None) -> pd.DataFrame:
    """Carga la definicion de canastas. Prefiere el Excel editable; si no, el CSV.

    Devuelve una fila por grupo con: cantidad_mensual, unidad, tiene_gluten,
    ean_media, envase_media, ean_celiaco, envase_celiaco (y descripciones/marcas).
    """
    base = Path(path) if path else CONFIG_DIR / "canastas"
    xlsx, csv = base / "canastas.xlsx", base / "canastas.csv"
    if xlsx.exists():
        df = pd.read_excel(xlsx, sheet_name="Canasta", skiprows=2,
                           dtype={"ean_media": str, "ean_celiaco": str})
    else:
        df = pd.read_csv(csv, dtype={"ean_media": str, "ean_celiaco": str})
    return df[df["grupo"].notna()].reset_index(drop=True)


def _costo_una(canastas: pd.DataFrame, precios: pd.DataFrame, ean_col: str, env_col: str,
               precios_nac: pd.DataFrame | None, geo_col: str) -> pd.DataFrame:
    """Costo de UNA canasta (media o celiaca) por (geo). precios: [geo, id_producto, precio]."""
    can = canastas[["grupo", "cantidad_mensual", ean_col, env_col]].rename(
        columns={ean_col: "id_producto", env_col: "envase"})
    can["unidades"] = can["cantidad_mensual"] / can["envase"]
    df = precios.merge(can, on="id_producto", how="inner")
    if precios_nac is not None:
        df = df.merge(precios_nac.rename(columns={"precio": "precio_nac"}),
                      on="id_producto", how="left")
        df["_imputado"] = df["precio"].isna()
        df["precio"] = df["precio"].fillna(df["precio_nac"])
    else:
        df["_imputado"] = False
    df["costo_item"] = df["precio"] * df["unidades"]
    return (df.groupby(geo_col)
              .agg(costo=("costo_item", "sum"), n_items=("id_producto", "nunique"),
                   n_imputados=("_imputado", "sum")).reset_index())


def costo_canastas(canastas: pd.DataFrame, precios: pd.DataFrame,
                   precios_nac: pd.DataFrame | None = None, geo_col: str = "geo") -> pd.DataFrame:
    """Costo de ambas canastas y prima por unidad geografica.

    precios: [geo_col, id_producto, precio] (precio mensual del producto en esa geografia).
    precios_nac: [id_producto, precio] nacional del mes, para imputar faltantes (opcional).
    Devuelve [geo, costo_media, costo_celiaco, prima, ...].
    """
    m = _costo_una(canastas, precios, "ean_media", "envase_media", precios_nac, geo_col)
    c = _costo_una(canastas, precios, "ean_celiaco", "envase_celiaco", precios_nac, geo_col)
    out = m.merge(c, on=geo_col, suffixes=("_media", "_celiaco"))
    out["prima"] = out["costo_celiaco"] / out["costo_media"] - 1
    return out
