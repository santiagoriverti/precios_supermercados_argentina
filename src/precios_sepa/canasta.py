"""Costo de canastas, imputación y series históricas.

Una canasta es un conjunto de (id_producto, cantidad_mensual). El costo por unidad geográfica
y mes usa el precio mediano del producto; si falta en la geografía, se imputa con el mediano
nacional del mismo producto y mes. Ver docs/METODOLOGIA_PRIMA_CELIACA.md §2.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import CONFIG_DIR


def cargar_canasta(nombre: str) -> pd.DataFrame:
    """Carga config/canastas/{nombre}.csv (comentarios '#' ignorados)."""
    path = CONFIG_DIR / "canastas" / f"{nombre}.csv"
    return pd.read_csv(path, dtype={"ean": str, "ean_tipo": str, "ean_celiaco": str}, comment="#")


def costo_canasta(precios_geo: pd.DataFrame, canasta: pd.DataFrame,
                  precios_nac: pd.DataFrame | None = None,
                  ean_col: str = "ean", qty_col: str = "cantidad_mensual") -> pd.DataFrame:
    """Costo de una canasta por (mes, geo).

    precios_geo: columnas [mes, geo, id_producto, precio_mediano].
    precios_nac: [mes, id_producto, precio_mediano] para imputar faltantes (opcional).
    Devuelve [mes, geo, costo, n_items, n_imputados].
    """
    can = canasta[[ean_col, qty_col]].dropna(subset=[ean_col]).rename(
        columns={ean_col: "id_producto", qty_col: "qty"})
    df = precios_geo.merge(can, on="id_producto", how="inner")
    if precios_nac is not None:
        nac = precios_nac.rename(columns={"precio_mediano": "precio_nac"})
        df = df.merge(nac, on=["mes", "id_producto"], how="left")
        df["_imputado"] = df["precio_mediano"].isna()
        df["precio_mediano"] = df["precio_mediano"].fillna(df["precio_nac"])
    else:
        df["_imputado"] = False
    df["costo_item"] = df["precio_mediano"] * df["qty"]
    return (df.groupby(["mes", "geo"])
              .agg(costo=("costo_item", "sum"),
                   n_items=("id_producto", "nunique"),
                   n_imputados=("_imputado", "sum"))
              .reset_index())


def prima_celiaca(costo_tipo: pd.DataFrame, costo_celiaca: pd.DataFrame) -> pd.DataFrame:
    """prima = costo_celiaca / costo_tipo − 1, por (mes, geo)."""
    m = costo_tipo.merge(costo_celiaca, on=["mes", "geo"], suffixes=("_tipo", "_celiaca"))
    m["prima"] = m["costo_celiaca"] / m["costo_tipo"] - 1
    return m
