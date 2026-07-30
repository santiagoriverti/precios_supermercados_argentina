# Memoria — precios_supermercados_argentina

Proyecto nuevo (2026-07-30). Plataforma de investigación reproducible sobre precios SEPA
(minorista + mayorista, diario, 2024–2026). Sucesor de `precios_minoristas_supermercados`
(que era solo minorista); se rehízo para no perder puntos de venta y sumar mayorista.

## Decisiones tomadas (con Santiago)
- **Reproducibilidad:** híbrido (datos crudos privados + agregados livianos públicos).
- **Rango:** arranca 2024 (estructura lista para sumar 2018–2023 después).
- **Motor:** DuckDB + Parquet. **Capa efectiva = agregado MENSUAL** (producto × sucursal × mes),
  NO el diario (demasiado grande: ~700 MB/quincena). Ver `agregado.py` + `scripts/02_build_mensual.py`.
- **Artículo 1:** prima celíaca. Canasta de **alimentos y bebidas SOLAMENTE** (sin higiene).
  Prima medida en 4 ejes: (1) tiempo, (2) geografía lat/lon, (3) **concentración ESPACIAL** de
  puntos de venta (densidad + distancias haversine, `concentracion.metricas_espaciales`), (4) cadena.
- **Canastas:** construidas NUEVAS (no reusar viejas) por cobertura geográfica; cantidades base
  CBA/INDEC. Definición EDITABLE en `config/canastas/canastas.xlsx` (col `cantidad_mensual`).
  Incluir sin-TACC de cobertura nacional aunque estén en menos sucursales; imputar precio nacional.

## Hallazgos verificados contra la base real (2026-07-30)
- Minorista `…COMPLETO`: 1 col precio/día (`precio_YYYYMMDD`). Mayorista: 4 cols/día
  (`precio_uni_iva`, `precio_uni`, `precio_bulto_iva`, `precio_bulto`).
- **UNIDAD = PESOS en toda la base** (minorista y mayorista, 2024–2026). Verificado con mediana
  global (DuckDB): MIN 2024-01=1355 → 2024-12=2690 → 2025-06=2999 → 2026-06=4425; MAY 2024-01=1663
  → 2026-06=3480. Crecen con inflación → mismos pesos. La base compilada ya está normalizada.
  OJO: hubo dos despistes que corregí — (a) el §4 del nb mostraba "factor 100" por un peek
  sesgado a las primeras filas (cluster caro id_comercio 2000); (b) los EANs de referencia del
  repo viejo (7793370008980, …) NO existen en esta base. Detección ahora = mediana global DuckDB.
  BUG corregido: `procesar_archivo` detectaba el factor pero NO lo aplicaba; ahora sí.
- **Universo de cadenas MUCHO más amplio** que el dict histórico de 16 banners: ~47 combos
  (id_comercio, id_bandera), ~3.611 sucursales. Anclar al maestro de sucursales, no descartar.
- Sentinelas a anular: 499999, 6999999, 62999 (planos), etc.
- Mojibake de encoding en los maestros (`Almac�n`, `Fiambrer�a`).
- Carpeta "2024 bis" = re-entrega corregida de ago–dic 2024 → preferir sobre "2024".
- Maestro productos: 176.702 filas (join `producto_sepa_id` = `id_producto`).

## Estado (2026-07-30)
- **Notebooks 00 (setup) y 01 (exploración): validados end-to-end en Colab por Santiago.**
- Paquete `precios_sepa` completo: io, ingest, **agregado** (mensual), clean, maestros, cadenas,
  canasta (lee el Excel), concentracion (HHI + **metricas_espaciales** lat/lon), indec, viz.
- **Agregado mensual minorista corriendo en background** (`scripts/02_build_mensual.py`), ~4,5
  min/mes, ~2 hs total; al 2026-07-30 iban 7 meses (2024-01..2024-07). Sale a
  `data/processed/precios_mensuales/` (gitignored, regenerable).
- **Cobertura por producto** calculada de 2026-06: `data/processed/cobertura_productos_2026-06.parquet`
  (8.038 productos food con cobertura nacional). Copia dev: `_cobertura_dev_2026-06.parquet`.
- **Canastas FINALES definidas** (15 grupos food, 5 con diferencial celíaco): `config/canastas/`
  `canastas.xlsx` (editable) + `canastas.csv`. Ver `docs/CANASTAS.md`.
- **Prima celíaca preliminar (2026-06, nacional): +63,4%** (media ~$87.4k, celíaca ~$142.9k).
  Sube respecto de estimaciones previas porque la conversión por tamaño de envase es correcta.
- Trampa recurrente resuelta: **acentos** en filtros SQL → usar `strip_accents()` de DuckDB
  (sin eso, "Atún"/"Azúcar"/"Jamón" no matchean y se eligen productos malos).
- Queso y huevos EXCLUIDOS de la canasta: se venden por peso (EAN de balanza/prefijo tienda),
  sin cobertura nacional con EAN limpio.

## Pendiente
1. **Notebook 02** (construcción de canastas: cobertura + Excel + validación geográfica).
2. **Notebook 03** (prima celíaca: serie temporal + mapa lat/lon + concentración espacial + cadena).
   Requiere el build mensual completo (para la serie).
3. Esperar a que termine el build mensual minorista; opcional: mayorista.
4. Completar `config/cadenas.csv` con los ~32 comercios regionales no identificados (fallback ok).
5. Definir IDs de Drive en `config/settings.yml` y publicar agregados livianos (modo lector).

## Ubicaciones y comandos clave
- Base local extraída: `C:/Users/sriverti/Downloads/base_sepa/`
- Build mensual: `python scripts/02_build_mensual.py --tipo minorista`
- Reconstruir canastas: `python scripts/03_construir_canastas.py`
- Repo viejo (referencia, verificar): `C:/Users/sriverti/Desktop/INECO/Repositorios/precios_minoristas_supermercados`
