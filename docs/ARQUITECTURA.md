# Arquitectura del proyecto

## Objetivo

Plataforma de investigación reproducible sobre los precios SEPA (minorista + mayorista,
diario, 2024–2026). Cada línea de investigación produce un artículo científico a partir de
un notebook autocontenido, ejecutable en Google Colab desde el README.

## Principios de diseño

1. **Procesar una vez, consultar muchas.** Los CSV.gz (~100+ GB descomprimidos) se convierten
   a **Parquet particionado** y se consultan con **DuckDB** (SQL sobre disco). Nunca se carga
   toda la base en RAM.
2. **La lógica vive en `src/`, no en los notebooks.** Los notebooks orquestan y visualizan;
   las funciones reutilizables están en el paquete `precios_sepa`. Esto evita duplicar código
   entre notebooks y hace testeable el pipeline.
3. **Reproducibilidad híbrida.** Datos crudos privados; agregados livianos públicos. Un lector
   reproduce los análisis sin bajar los 8,5 GB.
4. **Nunca perder puntos de venta.** El universo de sucursales se ancla al maestro (3.611).
   Los problemas de etiquetado se corrigen, no se descartan.
5. **Verificar la base, no asumir.** Las reglas heredadas del proyecto previo se re-verifican
   contra los datos reales (ver `docs/CALIDAD_DATOS.md`).

## Flujo de datos

```
                          (una vez, local, pesado)
  base_sepa.zip  ──►  scripts/00_build_parquet.py  ──►  data/interim/sepa/
   (Drive/local)        · lee CSV.gz por partes            tipo=minorista|mayorista/
                        · limpia (sentinelas, NA, factor)   anio=YYYY/mes=MM/*.parquet
                        · normaliza tipos                         │
                                                                  ▼
  maestros.xlsx  ──►  scripts/01_build_maestros.py  ──►  data/interim/maestros/*.parquet
                        · repara mojibake                         │
                        · normaliza provincias/cadenas            │
                                                                  ▼
                                              ┌───────────────────────────────────┐
                                              │  DuckDB (consulta SQL sobre disco) │
                                              └───────────────────────────────────┘
                                                                  │
                        (agregación a nivel producto/mes/provincia/cadena)
                                                                  ▼
                                       data/processed/*.parquet  (LIVIANO, publicable)
                                       · precio_mediano_mensual por producto×geo×cadena
                                       · series de costo de canastas
                                                                  │
                                                                  ▼
     notebooks/  ──►  outputs/figures/*.png|html   +   outputs/tables/*.xlsx|csv|tex
     (Colab)          gráficos y mapas                  insumos para los papers
```

## Layout de Parquet (particionado Hive)

```
data/interim/sepa/
  tipo=minorista/anio=2024/mes=01/parte1.parquet
  tipo=mayorista/anio=2026/mes=06/parte2.parquet
  ...
```

Formato **long** (no wide): cada fila es `(id_comercio, id_bandera, id_sucursal, provincia,
id_producto, fecha, precio, [tipo_precio])`. Se pasa de wide a long durante el build. DuckDB
lee solo las particiones necesarias vía predicados sobre `tipo`, `anio`, `mes`.

> Para el mayorista, `tipo_precio` ∈ {uni_iva, uni, bulto_iva, bulto} preserva las 4 medidas.

## Capa de agregado mensual (la que usa este proyecto)

El Parquet **diario** (`ingest`) resultó demasiado grande (~700 MB por quincena → decenas de GB
el histórico). Como el análisis es mensual + geográfico, la capa efectiva es el **agregado
mensual** (`agregado.py`, `scripts/02_build_mensual.py`):

```
data/processed/precios_mensuales/tipo=minorista/anio=2026/mes=06.parquet
  → una fila por (id_producto, id_sucursal): precio_prom (pesos), n_dias
```

Es ~34–64 MB por mes (el histórico entra en ~1–2 GB). Desde acá se calculan la **cobertura por
producto** (`cobertura_productos_YYYYMM.parquet`), la selección de canastas y las series de la
prima. Los scripts:

| Script | Rol |
|--------|-----|
| `scripts/00_build_parquet.py` | ETL diario (opcional; formato completo). |
| `scripts/02_build_mensual.py` | **Agregado mensual** (recomendado): CSV.gz → precios_mensuales. |
| `scripts/03_construir_canastas.py` | Arma `config/canastas/canastas.xlsx` (editable) + `.csv`. |

## El paquete `src/precios_sepa`

| Módulo | Responsabilidad |
|--------|-----------------|
| `io.py` | Descarga desde Drive (gdown), descubrimiento de archivos, apertura de CSV.gz en streaming. |
| `ingest.py` | Wide→long, escritura de Parquet particionado (diario), factor de precio por archivo. |
| `agregado.py` | **Capa de análisis**: agrega a precio promedio MENSUAL por producto × sucursal (sin `melt`, liviano). Reemplaza al diario para este proyecto. |
| `clean.py` | Sentinelas, `NA`→NaN, factor de precio autodetectado, marcado de outliers y meses parciales. |
| `maestros.py` | Carga y repara los maestros (mojibake), normaliza provincias por coordenadas. |
| `cadenas.py` | Deriva nombre de cadena desde `(id_comercio,id_bandera)` con fallback sin descartar. |
| `canasta.py` | Costo de canasta por sucursal/mes, imputación por precio nacional, series históricas. |
| `concentracion.py` | Índices de concentración de mercado (HHI, C4) por geografía. |
| `indec.py` | IPC / CBA / CBT desde la API de series de tiempo (datos.gob.ar). |
| `viz.py` | Gráficos estándar (series con locale ES) y mapas Folium por sucursal. |

## Notebooks

| # | Notebook | Rol |
|---|----------|-----|
| 00 | `setup_datos` | Descarga/monta datos, valida esquema, construye/verifica el Parquet. |
| 01 | `exploracion_base` | Cobertura, calidad, cadenas, mapa de sucursales. |
| 02 | `construccion_canastas` | Canasta típica + variante celíaca (selección de EANs). |
| 03 | `prima_celiaca` | **Artículo 1** (ver `METODOLOGIA_PRIMA_CELIACA.md`). |

Cada notebook: (1) instala `requirements`, (2) importa `precios_sepa`, (3) lee `data/processed`
o consulta DuckDB, (4) produce figuras/tablas en `outputs/`.

## Incorporar meses/años nuevos

- **Mes nuevo** (ej. `072026`): agregar los 4 archivos a la carpeta del año en Drive y correr
  `scripts/00_build_parquet.py --solo-mes 2026-07`. Idempotente por partición.
- **Histórico 2018–2023:** misma estructura de particiones; solo hay que ubicar los archivos.
