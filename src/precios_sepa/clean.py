"""Limpieza de precios SEPA. Ver docs/CALIDAD_DATOS.md para la justificación de cada regla."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Sentinelas por defecto (se puede sobreescribir desde settings.yml)
SENTINELAS = (499999, 6999999, 999999, 9999999)
PRECIO_MIN_PLAUSIBLE = 1.0
PRECIO_MAX_PLAUSIBLE = 20_000_000.0
EANS_REFERENCIA = ("7793370008980", "7790895000061", "7793370008188")  # sal, fideos, lavandina


def limpiar_precio(serie: pd.Series, sentinelas=SENTINELAS) -> pd.Series:
    """`NA`→NaN, sentinelas→NaN, fuera de rango plausible→NaN. Devuelve float32."""
    s = pd.to_numeric(serie.replace("NA", np.nan), errors="coerce")
    s = s.mask(s.isin(sentinelas))
    s = s.mask((s < PRECIO_MIN_PLAUSIBLE) | (s > PRECIO_MAX_PLAUSIBLE))
    return s.astype("float32")


def detectar_factor_precio(df: pd.DataFrame, col_precio: str = "precio",
                           col_ean: str = "id_producto",
                           eans_ref=EANS_REFERENCIA) -> int:
    """Autodetecta si los precios están en pesos (1) o centavos (100).

    Usa la mediana de productos de referencia de precio conocido. Robusto a entregas
    futuras que puedan volver a centavos. Ver docs/CALIDAD_DATOS.md §4.
    """
    ref = df.loc[df[col_ean].isin(eans_ref), col_precio].dropna()
    mediana = ref.median() if len(ref) else df[col_precio].median()
    if 30 <= mediana <= 20_000:
        return 1
    if 3_000 <= mediana <= 2_000_000:
        return 100
    raise ValueError(f"Mediana de referencia inesperada ({mediana:.1f}); revisar el archivo.")


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
