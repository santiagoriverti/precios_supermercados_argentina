# Calidad de datos y reglas de limpieza

Este documento registra los problemas detectados en la base y las decisiones de limpieza.
Toda regla implementada en `src/precios_sepa/clean.py` debe estar justificada acá.

> ⚠️ **Verificar, no asumir.** Varias reglas heredadas del proyecto previo
> (`precios_minoristas_supermercados`) **no aplican igual** a esta base nueva. Cada una
> se re-verificó contra los archivos reales el 2026-07-30. Las diferencias están marcadas.

---

## 1. Valores sentinela (precios falsos)

Se observaron precios "planos" repetidos idénticos en todos los días y sucursales, que
no son precios reales sino topes/placeholder:

- `499999`, `6999999`, `999999`, `9999999` y similares.
- Ejemplo real (enero 2024, minorista): producto `7798111354589` con `499999` constante;
  producto `7798192365962` con `62999` constante en todas las sucursales.

**Regla:** anular (→ NaN) los precios en la lista `limpieza.sentinelas` de `settings.yml`, y
marcar como outlier todo precio fuera de `[precio_min_plausible, precio_max_plausible]`.
No se borra la fila; solo se invalida el precio afectado (para no perder la observación de
que el producto estuvo listado).

## 2. Mojibake de encoding en los maestros

Los `.xlsx` de apoyo tienen texto con corrupción latin-1/UTF-8:
`Almac�n` → "Almacén", `Fiambrer�a` → "Fiambrería", `S�` → "Sí", `Noreste�` → "Noreste".

**Regla:** al cargar los maestros (`src/precios_sepa/maestros.py`) reparar las columnas de
texto (`producto_descripcion`, `categoria`, `subcategoria`, `REGION`, …). Estrategia: intentar
`s.encode('latin-1').decode('utf-8')`; si falla, aplicar un mapa de reemplazos conocidos
(`�`→ vocal acentuada según contexto). Guardar el maestro reparado en `data/interim/`.

## 3. `id_producto` / EAN como string

Los EAN son GTIN de 13 dígitos (algunos UPC de 8/12). Si en algún paso se convierten a
`int64`, se pierden los ceros iniciales al exportar.

**Regla:** `dtype={'id_producto': str}` siempre. Para el merge con el maestro, normalizar
con `.str.lstrip('0')` en ambos lados (o `zfill(13)` para exportar).

- **PLU codes** (prefijo `27…`/`28…`/`29…`): productos vendidos por peso en balanza. Son
  efímeros y no tienen historia consistente en SEPA → no usar en canastas de serie temporal.

## 4. Factor de precio (centavos vs. pesos)

**Hallazgo clave verificado (2026-07-30):** esta base viene **toda en PESOS**, tanto minorista
como mayorista, en **todo el rango 2024–2026**. Evidencia (mediana global por DuckDB, sin
sesgo de "primeras filas"):

| | 2024-01 | 2024-12 | 2025-06 | 2026-06 |
|---|---|---|---|---|
| Minorista | 1.355 | 2.690 | 2.999 | 4.425 |
| Mayorista | 1.663 | — | — | 3.480 |

Las medianas crecen de forma monótona con la inflación y quedan en rango de pesos; si 2024
estuviera en centavos, sería ~100× más chico. Además el minorista tiene ~24% de valores con
decimales (los centavos serían enteros). **La base que compiló Santiago ya está normalizada a
pesos** → el `factor` es 1 en todos los archivos.

> ⚠️ Esto **corrige** dos cosas: (a) la doc del proyecto previo, que decía "minorista 2024 =
> centavos" (cierto para el SEPA oficial crudo, pero **no** para esta base ya normalizada); y
> (b) los "EANs de referencia" heredados (`7793370008980`, …) que **no existen** en esta base
> y hacían que la detección por referencia fallara.

**Regla (salvaguarda, por archivo):** no asumir; detectar con la **mediana global** del archivo
(barata y sin sesgo con DuckDB), en `ingest.detectar_factor_archivo`:

```python
m = mediana_global(primera_columna_de_precio)   # via DuckDB, streaming
FACTOR = 100 if m > 10_000 else 1                # umbral_centavos (settings.yml)
```

`procesar_archivo` aplica el `FACTOR` detectado (dividiendo si es 100) y lo registra en el log
del build. Hoy siempre da 1, pero la salvaguarda protege ante entregas futuras en centavos.

## 5. Provincias — inconsistencias del maestro

El maestro de sucursales guarda algunas provincias con capitalización/acentos inconsistentes:
`"San juan"` (j minúscula), `"Neuquen"`/`"Neuquén"`, `"Entre Rios"`/`"Entre Ríos"`.

**Regla:** normalizar contra `config/provincias.csv` (código ISO como fuente primaria). Si el
nombre no matchea, **reclasificar por coordenadas** (bounding box por provincia) en lugar de
descartar la sucursal. Nunca perder un punto de venta por un error de etiquetado.

## 6. Identidad de cadenas

`id_bandera` (1–6) es el banner dentro del comercio, **no** la cadena comercial completa.
La cadena real = `(id_comercio, id_bandera)`.

**Diferencia con el proyecto previo:** la base nueva tiene **~47 combinaciones**
`comercio/bandera` y ~3.611 sucursales, contra los 16 banners del mapeo histórico. Muchos
`id_comercio` (1, 3, 4, 5, 6, 19, 20, 22, 24, 36, 47, 60–70, 2000-…) **no** están en el dict
viejo y se habrían etiquetado como "Comercio X".

**Regla:** derivar el nombre de cadena en `src/precios_sepa/cadenas.py`:
1. Usar `config/cadenas.csv` para los banners identificados.
2. Fallback: `"Comercio {id_comercio}"` para los no identificados (nunca descartar).
3. Enriquecer `config/cadenas.csv` a medida que se identifican los comercios regionales.

## 7. "2024" vs "2024 bis" — meses duplicados

Los meses ago–dic 2024 aparecen en dos carpetas (`2024/` y `2024 bis/Agosto-diciembre 2024/`).
`2024 bis` es la re-entrega corregida (`082024_..._COMPLETOb`).

**Regla:** al construir el índice de archivos, si un `(tipo, mes)` está en ambas, **preferir
`2024 bis`**. Registrar el descarte en el log.

## 8. Mes parcial (mes en curso)

El último mes disponible puede estar incompleto (solo `parte1`, o `parte2` con pocos días).

**Regla:** marcar cada `(tipo, mes)` con `mes_parcial=True` si le falta alguna parte o si la
cantidad de días con datos es menor a lo esperado. Los análisis de variación mensual deben
excluir o señalizar los meses parciales.
