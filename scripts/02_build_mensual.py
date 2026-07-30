#!/usr/bin/env python
"""Construye el agregado MENSUAL de precios (producto × sucursal × mes) desde la base SEPA.

Es la capa de análisis (compacta) que reemplaza al Parquet diario para este proyecto.
Salida: data/processed/precios_mensuales/tipo={tipo}/anio={a}/mes={m}.parquet

Uso:
    python scripts/02_build_mensual.py --tipo minorista                 # todos los meses
    python scripts/02_build_mensual.py --tipo minorista --solo-mes 2026-06
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from precios_sepa import ROOT, load_settings          # noqa: E402
from precios_sepa.io import descubrir_archivos         # noqa: E402
from precios_sepa.agregado import construir_mensual     # noqa: E402


def main() -> None:
    cfg = load_settings()
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=cfg["rutas"]["base_extraida"])
    ap.add_argument("--out", default=str(ROOT / "data" / "processed" / "precios_mensuales"))
    ap.add_argument("--tipo", choices=["minorista", "mayorista"], default=None)
    ap.add_argument("--solo-mes", default=None, help="YYYY-MM")
    args = ap.parse_args()

    archivos = descubrir_archivos(args.base)
    if args.tipo:
        archivos = [a for a in archivos if a.tipo == args.tipo]
    if args.solo_mes:
        archivos = [a for a in archivos if a.periodo == args.solo_mes]
    if not archivos:
        sys.exit("No hay archivos con esos filtros.")

    meses = sorted({(a.tipo, a.periodo) for a in archivos})
    print(f"Base: {args.base}\nSalida: {args.out}\nMeses a construir: {len(meses)}\n")
    t0 = time.time()
    construir_mensual(archivos, args.out)
    print(f"\nListo en {(time.time()-t0)/60:.1f} min.")


if __name__ == "__main__":
    main()
