"""Descubrimiento y apertura de archivos SEPA.

Responsabilidades:
- Descargar la base desde Google Drive (gdown) cuando se corre en Colab.
- Descubrir los archivos MMAAAA_… en la base extraída y clasificarlos por tipo/mes.
- Resolver el conflicto de meses duplicados "2024" vs "2024 bis" (preferir bis).
- Abrir CSV.gz en streaming a disco (anti-OOM) para leer en chunks.

Ver docs/DICCIONARIO_DATOS.md y docs/CALIDAD_DATOS.md.
"""

from __future__ import annotations

import gzip
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path

_RE_ARCHIVO = re.compile(
    r"^(?P<mes>\d{2})(?P<anio>\d{4})_pais_"
    r"(?P<mayorista>mayorista_)?parte(?P<parte>\d)"
    r".*?\.csv\.gz$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ArchivoSepa:
    path: Path
    tipo: str        # "minorista" | "mayorista"
    anio: int
    mes: int
    parte: int       # 1 = días 1–15, 2 = días 16–fin
    es_bis: bool     # proviene de "2024 bis" (re-entrega corregida)

    @property
    def periodo(self) -> str:
        return f"{self.anio:04d}-{self.mes:02d}"


def descubrir_archivos(base_dir: str | Path) -> list[ArchivoSepa]:
    """Recorre la base extraída y devuelve los ArchivoSepa, resolviendo duplicados.

    Regla de duplicados: si un (tipo, anio, mes, parte) aparece en "2024 bis" y en "2024",
    se conserva el de "2024 bis". Ver docs/CALIDAD_DATOS.md §7.
    """
    base = Path(base_dir)
    encontrados: dict[tuple, ArchivoSepa] = {}
    for p in base.rglob("*.csv.gz"):
        m = _RE_ARCHIVO.match(p.name)
        if not m:
            continue
        es_bis = "bis" in str(p.parent).lower()
        a = ArchivoSepa(
            path=p,
            tipo="mayorista" if m.group("mayorista") else "minorista",
            anio=int(m.group("anio")),
            mes=int(m.group("mes")),
            parte=int(m.group("parte")),
            es_bis=es_bis,
        )
        key = (a.tipo, a.anio, a.mes, a.parte)
        prev = encontrados.get(key)
        if prev is None or (a.es_bis and not prev.es_bis):
            encontrados[key] = a
    return sorted(encontrados.values(), key=lambda x: (x.tipo, x.anio, x.mes, x.parte))


def descargar_drive(file_id: str, destino: str | Path) -> Path:
    """Descarga un archivo de Google Drive por ID (uso en Colab)."""
    import gdown

    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    gdown.download(id=file_id, output=str(destino), quiet=False)
    return destino


def extraer_stream(zip_path: str | Path, filename: str, tmp_dir: str | Path) -> Path:
    """Extrae un miembro de un ZIP a disco en streaming (no lo carga en RAM)."""
    tmp_dir = Path(tmp_dir)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    out = tmp_dir / Path(filename).name
    with zipfile.ZipFile(zip_path) as z, z.open(filename) as src, open(out, "wb") as dst:
        shutil.copyfileobj(src, dst, length=4 * 1024 * 1024)
    return out


def abrir_csv_gz(path: str | Path):
    """Context manager de texto sobre un .csv.gz (UTF-8)."""
    return gzip.open(path, "rt", encoding="utf-8", errors="replace")
