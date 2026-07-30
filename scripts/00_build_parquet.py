#!/usr/bin/env python
"""ETL: base_sepa (CSV.gz) → Parquet particionado (long).

Corre UNA vez en local (es pesado). Idempotente por partición: reprocesar un mes
sobreescribe solo su Parquet.

Uso:
    python scripts/00_build_parquet.py                      # usa rutas de settings.yml
    python scripts/00_build_parquet.py --base "C:/.../base_sepa"
    python scripts/00_build_parquet.py --tipo minorista --solo-mes 2026-06
    python scripts/00_build_parquet.py --limit 2            # prueba: procesa 2 archivos

Ver docs/ARQUITECTURA.md.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Permitir importar el paquete src/ sin instalar
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from precios_sepa import ROOT, load_settings              # noqa: E402
from precios_sepa.io import descubrir_archivos            # noqa: E402
from precios_sepa.ingest import procesar_archivo          # noqa: E402


def main() -> None:
    cfg = load_settings()
    ap = argparse.ArgumentParser(description="Construye el Parquet particionado desde la base SEPA.")
    ap.add_argument("--base", default=cfg["rutas"]["base_extraida"],
                    help="Directorio con la base extraída (carpetas 2024, 2025, ...).")
    ap.add_argument("--out", default=str(ROOT / "data" / "interim" / "sepa"),
                    help="Raíz de salida del Parquet particionado.")
    ap.add_argument("--tipo", choices=["minorista", "mayorista"], default=None)
    ap.add_argument("--solo-mes", default=None, help="Procesar solo YYYY-MM.")
    ap.add_argument("--limit", type=int, default=None, help="Procesar como mucho N archivos (prueba).")
    args = ap.parse_args()

    base = Path(args.base)
    if not base.exists():
        sys.exit(f"ERROR: no existe la base extraída: {base}")

    archivos = descubrir_archivos(base)
    if args.tipo:
        archivos = [a for a in archivos if a.tipo == args.tipo]
    if args.solo_mes:
        archivos = [a for a in archivos if a.periodo == args.solo_mes]
    if args.limit:
        archivos = archivos[: args.limit]

    if not archivos:
        sys.exit("No se encontraron archivos que procesar con esos filtros.")

    print(f"Base: {base}")
    print(f"Salida: {args.out}")
    print(f"Archivos a procesar: {len(archivos)}\n")

    t0 = time.time()
    for i, a in enumerate(archivos, 1):
        print(f"[{i}/{len(archivos)}] {a.path.name}{'  (bis)' if a.es_bis else ''}")
        procesar_archivo(a, args.out)
    print(f"\nListo en {time.time() - t0:,.0f} s.")


if __name__ == "__main__":
    main()
