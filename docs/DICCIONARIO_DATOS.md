# Diccionario de datos — Base SEPA

Última verificación contra los archivos reales: **2026-07-30** (muestras de `base_sepa.zip`).

## 1. Archivos de la base

`base_sepa.zip` contiene, por año, dos familias de archivos + los maestros:

| Patrón de archivo | Tipo | Contenido |
|-------------------|------|-----------|
| `MMAAAA_pais_parte{1,2}COMPLETO.csv.gz` | **Minorista** | Precio de lista al público |
| `MMAAAA_pais_mayorista_parte{1,2}.csv.gz` | **Mayorista** | Precio mayorista (unidad y bulto, con y sin IVA) |
| `Archivos_de_apoyo/Maestro de Productos Interno.xlsx` | Maestro | 176.702 productos |
| `Archivos_de_apoyo/maestro_sucursales_completo.xlsx` | Maestro | 3.611 sucursales |

- `MMAAAA` = mes (2 díg.) + año (4 díg.). Ej.: `042026` = abril 2026.
- `parte1` = **días 1–15** del mes · `parte2` = **días 16–fin de mes**.
- Formato **wide**: una fila por (producto × sucursal), una o varias columnas de precio por día.
- Separador: coma. Encoding del CSV: UTF-8. Faltantes: string literal **`NA`** (no NaN).

> **Nota sobre "2024 bis":** la carpeta `2024 bis/Agosto-diciembre 2024/` es una **re-entrega
> corregida** de ago–dic 2024 (incluye `082024_..._COMPLETOb.csv.gz`). El pipeline debe
> preferir `2024 bis` sobre `2024` para los meses solapados. Ver `docs/CALIDAD_DATOS.md`.

## 2. Columnas comunes (ambos tipos)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `id_comercio` | string | Empresa que reporta (ancla al maestro de sucursales). |
| `id_bandera` | string | Banner/grupo dentro del comercio (1–6). `(id_comercio,id_bandera)` = cadena comercial. |
| `id_sucursal` | string | Punto de venta dentro de la cadena. |
| `sucursales_provincia` | string | Código ISO 3166-2 (`AR-B`, `AR-C`, …). Ver `config/provincias.csv`. |
| `id_producto` | string | **EAN/GTIN** (mayoría 13 díg.). **Siempre leer como string** (los ceros iniciales importan). |

Clave de sucursal: **`id_comercio + id_bandera + id_sucursal`** (join con maestro de sucursales).
Clave de producto: **`id_producto`** = `producto_sepa_id` del maestro de productos.

## 3. Columnas de precio

### Minorista (`…COMPLETO`)
Una columna por día: **`precio_YYYYMMDD`** (ej. `precio_20240101`).
Un archivo de quincena tiene 15 columnas de precio (aprox.).

### Mayorista (`…mayorista`)
**Cuatro** columnas por día:

| Columna | Significado |
|---------|-------------|
| `precio_uni_iva_YYYYMMDD` | Precio unitario **con** IVA |
| `precio_uni_YYYYMMDD` | Precio unitario **sin** IVA (neto) |
| `precio_bulto_iva_YYYYMMDD` | Precio del **bulto** (caja) con IVA |
| `precio_bulto_YYYYMMDD` | Precio del bulto sin IVA |

Ejemplo real: `uni_iva=4115`, `uni=3400.83`, `bulto_iva=49380`, `bulto=40809.96`
→ el bulto contiene 12 unidades (`49380 / 4115 = 12`).

### Unidad de los precios
**Pesos argentinos (ARS), con decimales.** Los valores traen parte decimal
(ej. `3400.83`, `17.6`), lo que confirma que **no** están en centavos en esta base.
El pipeline igual autodetecta el factor por archivo con productos de referencia
(ver `docs/CALIDAD_DATOS.md` §Factor de precio), por robustez ante entregas futuras.

## 4. Maestro de Productos Interno (`.xlsx`)

176.702 filas. Columnas clave para el análisis:

| Columna | Uso |
|---------|-----|
| `producto_sepa_id` | **Join key** con `id_producto` de los CSV. |
| `producto_ean` | EAN informado por el maestro (puede diferir del sepa_id). |
| `producto_descripcion` | Nombre del producto (⚠ mojibake de encoding, ver Calidad). |
| `producto_marca` | Marca. |
| `producto_cantidad_presentacion` / `producto_unidad_medida_presentac` | Contenido (ej. 500 Gr). |
| `producto_cantidad_referencia` / `producto_unidad_medida_referenci` | Cantidad de referencia (para precio por kg/lt). |
| `rubro` → `categoria` → `subcategoria` | Jerarquía de 3 niveles. **Valores literales**, no keywords. |
| `producto_blacklist` | Marca productos a excluir. |

> **Trampa de categorías** (heredada del proyecto previo): los valores de `categoria` son
> literales del maestro (ej. `Lácteos`, no `leche`). Filtrar por el valor exacto. Categorías
> heterogéneas (`Fiambrería` mezcla fiambres y quesos; `Conservas` mezcla frutas y patés)
> requieren filtrar además por `subcategoria`. Detalle en `docs/METODOLOGIA_PRIMA_CELIACA.md`.

## 5. Maestro de sucursales (`.xlsx`)

3.611 filas. Enumera **todos** los puntos de venta. Columnas clave:

| Columna | Uso |
|---------|-----|
| `id_comercio` + `id_bandera` + `id_sucursal` | **Join key** con los CSV. |
| `sucursales_nombre`, `sucursales_tipo` | Nombre y tipo (Tienda Física / Online). |
| `sucursales_latitud`, `sucursales_longitud` | Georreferenciación (mapas). |
| `sucursales_localidad`, `sucursales_barrio`, `sucursales_codigo_postal` | Ubicación. |
| `sucursales_provincia` / `PROVINCIA` | Provincia (⚠ inconsistencias de capitalización, ver Calidad). |
| `REGION` | AMBA · Pampeana · Patagonia · Noroeste · Cuyo · Noreste. |

> **Regla de oro:** anclar el universo de sucursales a este maestro y **nunca descartar un
> punto de venta** por un problema de etiquetado (provincia mal escrita, etc.). El universo
> de cadenas de la base nueva es mucho más amplio (~47 combos `comercio/bandera`) que el
> mapeo histórico de 16 banners — ver `config/cadenas.csv`.
