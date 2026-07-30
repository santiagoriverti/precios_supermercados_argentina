"""Limpieza de precios SEPA. Ver docs/CALIDAD_DATOS.md para la justificación de cada regla."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Sentinelas por defecto (se puede sobreescribir desde settings.yml)
SENTINELAS = (499999, 6999999, 999999, 9999999)
PRECIO_MIN_PLAUSIBLE = 1.0
PRECIO_MAX_PLAUSIBLE = 20_000_000.0

# Umbral del heurístico de unidad: una mediana global de precios por encima de este valor
# indica centavos (÷100). Verificado: esta base viene en PESOS (mediana ~1.300–4.500).
UMBRAL_CENTAVOS = 10_000.0


def limpiar_precio(serie: pd.Series, sentinelas=SENTINELAS) -> pd.Series:
    """`NA`→NaN, sentinelas→NaN, fuera de rango plausible→NaN. Devuelve float32."""
    s = pd.to_numeric(serie.replace("NA", np.nan), errors="coerce")
    s = s.mask(s.isin(sentinelas))
    s = s.mask((s < PRECIO_MIN_PLAUSIBLE) | (s > PRECIO_MAX_PLAUSIBLE))
    return s.astype("float32")


def detectar_factor_precio(precios, col_precio: str = "precio") -> int:
    """Detecta si los precios están en pesos (1) o centavos (100) por la mediana global.

    `precios` puede ser una Series de precios o un DataFrame (usa `col_precio`).
    Heurístico: mediana global > UMBRAL_CENTAVOS => centavos (÷100).

    NOTA: esta base viene en PESOS en todo el rango (minorista y mayorista, 2024–2026).
    La detección se mantiene como salvaguarda ante entregas futuras que pudieran venir en
    centavos. La detección robusta a nivel archivo (sin sesgo) está en
    `ingest.detectar_factor_archivo` (mediana vía DuckDB). Ver docs/CALIDAD_DATOS.md §4.
    """
    s = precios[col_precio] if isinstance(precios, pd.DataFrame) else precios
    m = pd.to_numeric(s, errors="coerce").median()
    return 100 if (pd.notna(m) and m > UMBRAL_CENTAVOS) else 1


def reparar_mojibake(s: pd.Series) -> pd.Series:
    """Repara texto con doble-encoding latin-1/UTF-8 (Almac�n → Almacén)."""
    def _fix(x):
        if not isinstance(x, str):
            return x
        try:
            return x.encode("latin-1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return x
    return s.map(_fix)
