"""Gráficos y mapas estándar del proyecto.

- Series de tiempo con etiquetas de mes en español (evita el locale inglés de Colab).
- Mapas Folium por sucursal (lat/lon) y coropléticos por provincia.
"""

from __future__ import annotations

import matplotlib.dates as mdates
import matplotlib.ticker as mticker

_MESES_ES = {1: "ene", 2: "feb", 3: "mar", 4: "abr", 5: "may", 6: "jun",
             7: "jul", 8: "ago", 9: "sep", 10: "oct", 11: "nov", 12: "dic"}


def formatear_eje_meses(ax):
    """Formatea el eje X de fechas como 'ene-24' en español."""
    def _fmt(x, pos):
        try:
            ts = mdates.num2date(x)
            return f"{_MESES_ES[ts.month]}-{str(ts.year)[2:]}"
        except Exception:
            return ""
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(_fmt))
    return ax


def mapa_sucursales(df_suc, valor_col: str, popup_cols=None):
    """Mapa Folium con un CircleMarker por sucursal, coloreado por `valor_col`.

    df_suc debe tener sucursales_latitud, sucursales_longitud y valor_col.
    Implementación completa (lazy popup para archivos livianos) en notebooks/03.
    """
    raise NotImplementedError("Se implementa en notebooks/03_prima_celiaca.ipynb (mapa Folium).")
