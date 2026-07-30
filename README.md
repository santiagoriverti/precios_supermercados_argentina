# Precios de Supermercados de Argentina (SEPA)

Base de precios **minoristas y mayoristas** de los supermercados de Argentina con
granularidad **diaria**, a partir del Sistema Electrónico de Publicidad de Precios
Argentinos ([SEPA](https://datos.produccion.gob.ar/dataset/sepa-precios)).

Este repositorio es una **plataforma de investigación reproducible**: pule la base,
la deja consultable con DuckDB/Parquet y ofrece notebooks ejecutables en Google Colab,
cada uno pensado como insumo de un artículo científico.

> **Cobertura actual:** enero 2024 → junio 2026 (diaria) · ~3.600 sucursales · ~176.000 productos · minorista + mayorista.
> La estructura está preparada para incorporar el histórico 2018–2023 cuando esté disponible.

---

## Líneas de investigación

| # | Artículo | Notebook | Estado |
|---|----------|----------|--------|
| **1** | **Prima celíaca**: canasta de alimentos media vs. su versión con reemplazo apto celíaco. Sobreprecio y su variación en (1) tiempo, (2) geografía por lat/lon, (3) concentración espacial de puntos de venta, (4) cadena/marca. | `03_prima_celiaca.ipynb` | 🚧 Canastas definidas; prima preliminar **+63%** (2026-06) |
| 2 | (a definir) | — | 💡 Backlog |

> Cada artículo nace de un notebook autocontenido. Las canastas (media y celíaca) están en el
> **Excel editable** [`config/canastas/canastas.xlsx`](config/canastas/canastas.xlsx); ver
> [`docs/CANASTAS.md`](docs/CANASTAS.md) y [`docs/METODOLOGIA_PRIMA_CELIACA.md`](docs/METODOLOGIA_PRIMA_CELIACA.md).

---

## Notebooks (ejecutables en Colab)

Abrí cualquiera con un click. Corren sobre datos que se descargan/montan desde Google Drive
(ver [Acceso a los datos](#acceso-a-los-datos)).

| Notebook | Descripción | Abrir |
|----------|-------------|-------|
| `00_setup_datos.ipynb` | Descarga/monta la base, valida el esquema y arma el Parquet consultable. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_supermercados_argentina/blob/main/notebooks/00_setup_datos.ipynb) |
| `01_exploracion_base.ipynb` | Esquema, unidades, cobertura por cadena/provincia/día, calidad de datos, mapa de sucursales. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_supermercados_argentina/blob/main/notebooks/01_exploracion_base.ipynb) |
| `02_construccion_canastas.ipynb` | Construye la canasta de consumo típica y su variante apta celíaca (reemplazo sin TACC). | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_supermercados_argentina/blob/main/notebooks/02_construccion_canastas.ipynb) |
| `03_prima_celiaca.ipynb` | **Artículo 1.** Mide la prima celíaca, su evolución, distribución geográfica y su relación con la concentración de mercado. | [![Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/santiagoriverti/precios_supermercados_argentina/blob/main/notebooks/03_prima_celiaca.ipynb) |

---

## Arquitectura del proyecto

```
precios_supermercados_argentina/
├── README.md                     ← este archivo (portal de notebooks)
├── requirements.txt              ← dependencias (DuckDB, Polars, gdown, folium…)
├── config/                       ← configuración versionada
│   ├── settings.yml              ← rutas, IDs de Drive, parámetros globales
│   ├── cadenas.csv               ← (id_comercio,id_bandera) → cadena + grupo corporativo
│   ├── provincias.csv            ← ISO 3166-2 → provincia, región, población (Censo 2022)
│   └── canastas/
│       ├── canasta_tipo.csv      ← EANs + cantidades de la canasta de consumo típica
│       └── canasta_celiaca.csv   ← reemplazos sin TACC (mapeados a la canasta tipo)
├── src/precios_sepa/             ← paquete Python reutilizable (la lógica vive acá)
│   ├── io.py         · ingest.py · clean.py
│   ├── maestros.py   · cadenas.py
│   ├── canasta.py    · concentracion.py
│   ├── indec.py      · viz.py
├── scripts/                      ← ETL pesado que corre local (una sola vez)
│   ├── 00_build_parquet.py       ← base_sepa.zip → data/processed/*.parquet
│   └── 01_build_maestros.py      ← maestros .xlsx → parquet limpio
├── notebooks/                    ← notebooks Colab (un artículo por notebook)
├── data/
│   ├── raw/         (gitignored)  ← base_sepa extraída
│   ├── interim/     (gitignored)  ← parquets intermedios
│   ├── processed/                 ← agregados livianos publicables
│   └── external/                  ← IPC, GeoJSON de provincias, Censo
├── outputs/
│   ├── figures/                   ← gráficos y mapas (regenerables)
│   └── tables/                    ← Excel/CSV/LaTeX para los papers
└── docs/                          ← diccionario de datos, metodología, calidad
```

**Motor:** los CSV.gz se convierten **una sola vez** a **Parquet particionado** (por tipo /
año / mes) y se consultan con **DuckDB** (SQL sobre disco, sin cargar todo en RAM). Esto
permite trabajar los ~100+ GB descomprimidos incluso en Colab gratuito.

**Modelo de reproducibilidad (híbrido):**
- **Datos crudos** (`base_sepa.zip`, privado): se procesan una vez con `scripts/00_build_parquet.py`.
- **Agregados livianos** (series de canastas, precios mensuales medianos por producto/provincia/cadena):
  se publican como Parquet chico para que cualquiera reproduzca los análisis y gráficos **sin** bajar los 8,5 GB.

---

## Acceso a los datos

La base cruda (`base_sepa.zip`, ~8,5 GB) vive en Google Drive, no en el repo. Estructura:

```
base_sepa.zip
├── 2024/                MMAAAA_pais_parteN_COMPLETO.csv.gz   (minorista)
├── 2024 bis/            MMAAAA_pais_mayorista_parteN.csv.gz  (mayorista)
├── 2025/  · 2026/       … se suman meses nuevos (07/2026, 08/2026, …)
└── Archivos_de_apoyo/   Maestro de Productos Interno.xlsx
                         maestro_sucursales_completo.xlsx
```

- **Solo Santiago (build local):** montar Drive o usar la copia local y correr `scripts/00_build_parquet.py`.
- **Cualquier lector (reproducir análisis):** los notebooks bajan los **agregados livianos** ya procesados.

> Configurá los IDs de Drive y las rutas en [`config/settings.yml`](config/settings.yml).

---

## Cómo empezar (local)

```bash
git clone https://github.com/santiagoriverti/precios_supermercados_argentina.git
cd precios_supermercados_argentina
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt

# 1) Agregado MENSUAL de precios (recomendado: producto x sucursal x mes, ~1-2 GB)
python scripts/02_build_mensual.py --tipo minorista

# 2) Construir/actualizar las canastas (Excel editable + CSV)
python scripts/03_construir_canastas.py

#    (opcional) ETL diario completo, mucho mas pesado:
#    python scripts/00_build_parquet.py --tipo minorista
```

Después, abrí los notebooks en `notebooks/` (local o Colab). Para cambiar las cantidades de la
canasta, editá `config/canastas/canastas.xlsx` (columna `cantidad_mensual`) y reejecutá.

---

## La base de precios (resumen técnico)

Dos esquemas distintos conviven en la base. Detalle completo en
[`docs/DICCIONARIO_DATOS.md`](docs/DICCIONARIO_DATOS.md) y
[`docs/CALIDAD_DATOS.md`](docs/CALIDAD_DATOS.md).

| | Minorista (`…COMPLETO`) | Mayorista (`…mayorista`) |
|---|---|---|
| Columnas fijas | `id_comercio, id_bandera, id_sucursal, sucursales_provincia, id_producto` | idem |
| Precio por día | 1 col: `precio_YYYYMMDD` | 4 cols: `precio_uni_iva`, `precio_uni`, `precio_bulto_iva`, `precio_bulto` |
| Unidad | pesos ARS (con decimales) | pesos ARS (con decimales) |
| Faltantes | string `NA` | string `NA` |
| Partición temporal | `parteN`: 1 = días 1–15, 2 = días 16–fin de mes | idem |

**Puntos de atención resueltos en el pipeline de limpieza:**
1. **Valores sentinela** (`499999`, `6999999`, precios planos) → se detectan y anulan.
2. **Mojibake de encoding** en los maestros (`Almac�n`, `Fiambrer�a`, `S�`) → se reparan.
3. **`id_producto` como string** (EAN-13) → nunca convertir a int (pierde ceros iniciales).
4. **Cadenas ancladas al maestro de sucursales** (3.611 puntos de venta) → no se pierde ninguno.

---

## Documentación

- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) — diseño del proyecto y flujo de datos.
- [`docs/DICCIONARIO_DATOS.md`](docs/DICCIONARIO_DATOS.md) — esquema, columnas y unidades.
- [`docs/CALIDAD_DATOS.md`](docs/CALIDAD_DATOS.md) — limpieza, sentinelas, encoding, factor de precio.
- [`docs/CANASTAS.md`](docs/CANASTAS.md) — composición de las canastas media y celíaca (editable).
- [`docs/METODOLOGIA_PRIMA_CELIACA.md`](docs/METODOLOGIA_PRIMA_CELIACA.md) — Artículo 1.

---

## Licencia y cita

- **Código:** MIT (ver [`LICENSE`](LICENSE)).
- **Datos:** SEPA, Secretaría de Comercio de Argentina (datos públicos).
- Autor: Santiago Riverti — INECO.
