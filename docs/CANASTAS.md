# Canastas de alimentos — media y celíaca

Definición **editable** en [`config/canastas/canastas.xlsx`](../config/canastas/canastas.xlsx)
(hoja `Canasta`). Para cambiar el peso de cada producto, editá la columna **`cantidad_mensual`**
en el Excel y volvé a correr el notebook — no hace falta tocar código. El export
`config/canastas/canastas.csv` es la copia versionable en git.

## Criterios de construcción

Las dos canastas se eligieron (no se reutilizaron las de proyectos previos) según:

1. **Consumo representativo** del consumidor argentino → cantidades base **CBA/INDEC**
   (Canasta Básica Alimentaria, por adulto equivalente/mes).
2. **Amplia cobertura regional** (lat/lon): productos presentes en (casi) las 24 provincias.
   Se admite un producto **equivalente**, no idéntico, mientras la cobertura sea nacional.
3. **Amplia cobertura temporal**: marcas líderes nacionales, estables mes a mes (se valida con
   la serie completa en el notebook 03).

La selección se hizo sobre la cobertura real (join con el maestro de sucursales) del mes
2026-06: `data/processed/cobertura_productos_YYYYMM.parquet`, generado desde el agregado mensual.

## Composición (15 grupos de alimentos y bebidas)

Sólo alimentos y bebidas (sin higiene/limpieza). **5 grupos tienen diferencial celíaco** (el
motor de la prima); el resto es idéntico en ambas canastas.

| Grupo | Media (con gluten) | Celíaco (sin TACC) | Cant. base |
|-------|--------------------|--------------------|-----------|
| **Harina** | Harina 000 Favorita 1kg | Premezcla s/TACC Pureza 500g | 1,35 kg |
| **Fideos** | Fideos Tallarín Lucchetti 500g | Fideos s/Gluten Matarazzo 500g | 1,00 kg |
| **Pan** | Pan Lactal 460g | Pan de molde s/TACC Bio 220g | 1,50 kg |
| **Galletitas dulces** | Galletitas Vainilla Duquesa 115g | Galletitas Oreo s/TACC 95g | 0,40 kg |
| **Galletitas saladas** | Bizcochitos Don Satur 200g | Galletas de Arroz Grandiet s/TACC 100g | 0,30 kg |
| Arroz | Arroz Gallo Oro 500g | *(igual)* | 0,63 kg |
| Aceite girasol | Aceite Natura 900ml | *(igual)* | 1,20 L |
| Azúcar | Azúcar Ledesma 1kg | *(igual)* | 1,44 kg |
| Yerba mate | Yerba Playadito 500g | *(igual)* | 0,60 kg |
| Café molido | Café Cabrales 250g | *(igual)* | 0,10 kg |
| Leche entera | Leche La Serenísima 1L | *(igual)* | 7,35 L |
| Atún | Atún La Campagnola 170g (ya s/TACC) | *(igual)* | 0,30 kg |
| Mermelada | Mermelada Durazno Arcor 454g | *(igual)* | 0,24 kg |
| Lentejas | Lentejas Arcor 300g | *(igual)* | 0,24 kg |
| Gaseosa cola | Coca-Cola 2.25L | *(igual)* | 4,00 L |

## Cálculo del costo

Como los envases sin TACC suelen ser más chicos, la cantidad se expresa en **kg/L reales** y se
convierte a **unidades de envase** por producto:

```
unidades_X   = cantidad_mensual / envase_X          (envase en kg o L, leído de la descripción)
costo_X(g,m) = Σ_grupo  unidades_X · precio(ean_X, g, m)
prima(g,m)   = costo_celiaco / costo_media − 1
```

`precio` faltante en una geografía se imputa con el precio nacional del mismo producto y mes.

## Resultado preliminar (2026-06, nacional)

| | Costo |
|---|---|
| Canasta media | ~$87.400 |
| Canasta celíaca | ~$142.900 |
| **Prima celíaca** | **+63,4%** |

El sobreprecio se concentra en pan, harina y fideos (el trigo). Es preliminar: depende de las
cantidades (editables en el Excel) y se calcula sobre la serie completa en el notebook 03.

## Limitaciones de cobertura

- **Queso y huevos** quedaron fuera: se venden mayormente por peso (códigos de balanza/PLU y EAN
  con prefijo de tienda) → sin cobertura nacional con EAN limpio en SEPA.
- Los sin TACC de panificados tienen menor cobertura en sucursales (~1.200) que sus equivalentes
  con gluten (~2.300), aunque siguen presentes en las 24 provincias (cobertura nacional).
- Precios de lista (no incluye promociones ni descuentos por tarjeta).
