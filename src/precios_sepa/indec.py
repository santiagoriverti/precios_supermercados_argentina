"""Series oficiales del INDEC vía la API de datos.gob.ar (series de tiempo).

Se usan para contrastar la prima celíaca y los índices SEPA con la inflación oficial.
"""

from __future__ import annotations

import pandas as pd
import requests

BASE_URL = "https://apis.datos.gob.ar/series/api/series/"

SERIES = {
    "ipc_general": "148.3_INIVELGENERAL_DICI_M_26",
    "ipc_alimentos": "148.3_IALIMENTOSY_DICI_M_26",
    "cba": "103.1_I2N_DICI_M_19",   # Canasta Básica Alimentaria
}


def get_serie(serie_id: str, start_date: str = "2024-01-01") -> pd.DataFrame:
    """Descarga una serie por ID. Devuelve DataFrame [fecha, valor]."""
    params = {"ids": serie_id, "start_date": start_date, "limit": 5000, "format": "json"}
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["data"], columns=["fecha", "valor"])
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def get_ipc(start_date: str = "2024-01-01") -> pd.DataFrame:
    """IPC Nivel general + Alimentos y bebidas, indexado por mes (YYYY-MM)."""
    g = get_serie(SERIES["ipc_general"], start_date).rename(columns={"valor": "ipc_general"})
    a = get_serie(SERIES["ipc_alimentos"], start_date).rename(columns={"valor": "ipc_alimentos"})
    df = g.merge(a, on="fecha", how="outer").sort_values("fecha")
    df["mes"] = df["fecha"].dt.strftime("%Y-%m")
    return df
