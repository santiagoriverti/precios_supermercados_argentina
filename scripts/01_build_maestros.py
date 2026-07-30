#!/usr/bin/env python
"""Limpia los maestros (.xlsx) y los guarda como Parquet en data/interim/maestros/.

Repara mojibake, normaliza provincias/cadenas y deja los maestros listos para los joins.
Uso:
    python scripts/01_build_maestros.py --apoyo "C:/.../base_sepa/Archivos_de_apoyo"
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from precios_sepa import ROOT, load_settings                     # noqa: E402
from precios_sepa.maestros import cargar_productos, cargar_sucursales  # noqa: E402


def main() -> None:
    cfg = load_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--apoyo", default=str(Path(cfg["rutas"]["base_extraida"]) / "Archivos_de_apoyo"),
                    help="Carpeta con los .xlsx de apoyo.")
    args = ap.parse_args()

    apoyo = Path(args.apoyo)
    out = ROOT / "data" / "interim" / "maestros"
    out.mkdir(parents=True, exist_ok=True)

    print("Cargando maestro de productos...")
    prod = cargar_productos(apoyo / "Maestro de Productos Interno.xlsx")
    prod.to_parquet(out / "productos.parquet", index=False)
    print(f"  {len(prod):,} productos -> {out / 'productos.parquet'}")

    print("Cargando maestro de sucursales...")
    suc = cargar_sucursales(apoyo / "maestro_sucursales_completo.xlsx")
    suc.to_parquet(out / "sucursales.parquet", index=False)
    print(f"  {len(suc):,} sucursales -> {out / 'sucursales.parquet'}")

    print("Listo.")


if __name__ == "__main__":
    main()
