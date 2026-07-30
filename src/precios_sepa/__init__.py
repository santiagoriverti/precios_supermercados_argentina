"""precios_sepa — utilidades para procesar y analizar la base de precios SEPA.

La lógica reutilizable del proyecto vive en este paquete; los notebooks solo orquestan
y visualizan. Ver docs/ARQUITECTURA.md.

Módulos:
    io            descubrimiento/descarga de archivos, apertura de CSV.gz en streaming
    ingest        wide→long y escritura de Parquet particionado
    clean         limpieza (sentinelas, NA, factor de precio, outliers)
    maestros      carga y reparación de los maestros de productos y sucursales
    cadenas       derivación de nombre de cadena desde (id_comercio, id_bandera)
    canasta       costo de canastas, imputación y series históricas
    concentracion índices de concentración de mercado (HHI, C4, densidad)
    indec         series oficiales (IPC, CBA, CBT) desde datos.gob.ar
    viz           gráficos y mapas estándar
"""

from pathlib import Path

__version__ = "0.1.0"

# Raíz del repo (…/precios_supermercados_argentina), robusto ante el cwd.
ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
OUTPUTS_DIR = ROOT / "outputs"


def load_settings(path: str | Path | None = None) -> dict:
    """Carga config/settings.yml como dict."""
    import yaml

    path = Path(path) if path else CONFIG_DIR / "settings.yml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)
