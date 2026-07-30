# Memoria — precios_supermercados_argentina

Proyecto nuevo (2026-07-30). Plataforma de investigación reproducible sobre precios SEPA
(minorista + mayorista, diario, 2024–2026). Sucesor de `precios_minoristas_supermercados`
(que era solo minorista); se rehízo para no perder puntos de venta y sumar mayorista.

## Decisiones tomadas (con Santiago)
- **Reproducibilidad:** híbrido (datos crudos privados + agregados livianos públicos).
- **Rango:** arranca 2024 (estructura lista para sumar 2018–2023 después).
- **Motor:** DuckDB + Parquet particionado.
- **Artículo 1:** prima celíaca (canasta típica vs. celíaca) — evolución temporal, geográfica,
  y relación con la concentración de mercado (HHI).

## Hallazgos verificados contra la base real (2026-07-30)
- Minorista `…COMPLETO`: 1 col precio/día (`precio_YYYYMMDD`). Mayorista: 4 cols/día
  (`precio_uni_iva`, `precio_uni`, `precio_bulto_iva`, `precio_bulto`).
- **Precios en PESOS con decimales, NO centavos** — contradice la doc del repo viejo
  (que decía "2024 = centavos"). Igual se autodetecta el factor por archivo.
- **Universo de cadenas MUCHO más amplio** que el dict histórico de 16 banners: ~47 combos
  (id_comercio, id_bandera), ~3.611 sucursales. Anclar al maestro de sucursales, no descartar.
- Sentinelas a anular: 499999, 6999999, 62999 (planos), etc.
- Mojibake de encoding en los maestros (`Almac�n`, `Fiambrer�a`).
- Carpeta "2024 bis" = re-entrega corregida de ago–dic 2024 → preferir sobre "2024".
- Maestro productos: 176.702 filas (join `producto_sepa_id` = `id_producto`).

## Estado
- Arquitectura creada: config/, src/precios_sepa/, scripts/, docs/, notebooks/ (pendientes).
- src backbone funcional: io.descubrir_archivos, ingest.wide_a_long/procesar_archivo, clean.
- Pipeline validado en muestra (ver git log del primer commit).

## Pendiente
1. Notebooks 00–03 (00 setup, 01 exploración, 02 canastas, 03 prima celíaca).
2. Extraer los EANs completos de la canasta "Media" desde el nb02 del repo viejo
   (`precios_minoristas_supermercados/notebooks/02_...ipynb`) para completar
   `config/canastas/canasta_tipo.csv`.
3. Completar `config/cadenas.csv` con los comercios regionales no identificados.
4. Definir IDs de Drive en `config/settings.yml` (base cruda + agregados públicos).
5. Correr el build completo y publicar los agregados livianos.

## Ubicaciones
- Base local extraída: `C:/Users/sriverti/Downloads/base_sepa/`
- Repo viejo (referencia, verificar): `C:/Users/sriverti/Desktop/INECO/Repositorios/precios_minoristas_supermercados`
