# Metodología — Artículo 1: La prima celíaca en Argentina

**Pregunta de investigación:** ¿Cuánto más caro es alimentarse sin gluten (dieta apta
celíaca) que con una canasta de consumo típica en Argentina? ¿Cómo evoluciona ese sobreprecio
—la *prima celíaca*— en el tiempo, cómo se distribuye geográficamente, y aumenta o disminuye
según la concentración de centros de comercialización?

> Antecedente: el proyecto previo estimó una prima celíaca de **~9%** (abril 2026) sobre la
> canasta "Media". Este artículo la formaliza sobre la base nueva (minorista + mayorista,
> universo ampliado de sucursales) y agrega los ejes geográfico y de concentración.

---

## 1. Diseño de las dos canastas

- **Canasta típica (T):** canasta de consumo representativa (base "Media" ENGHo). Ver
  `config/canastas/canasta_tipo.csv`.
- **Canasta celíaca (C):** idéntica a T, salvo que **todos** los productos con gluten (trigo,
  cebada, centeno, avena) se reemplazan por equivalentes **sin TACC** de cobertura comparable.
  El mapeo de reemplazos está en `config/canastas/canasta_celiaca.csv`.

Los ítems **sin gluten comunes** a ambas canastas (arroz, leche, aceite, etc.) se cancelan al
comparar; el motor del sobreprecio son los **ítems diferenciales** (pastas, harina, galletitas,
cacao, caldo, cerveza→sidra, …).

## 2. Definición de la prima celíaca

Para un mes `m` y una unidad geográfica `g` (país / región / provincia):

```
prima_celiaca(m,g) = costo_C(m,g) / costo_T(m,g) − 1
```

donde `costo_X(m,g) = Σ_p precio_mediano(p, m, g) × cantidad(p, X)`.

- **Precio mediano** por producto×mes×geografía (robusto a outliers) desde `data/processed`.
- **Imputación:** si un producto no tiene precio en `g`, se imputa con el precio mediano
  nacional del mismo producto en `m` (misma regla que el proyecto previo).
- Se reporta también la **prima diferencial** (solo ítems que cambian) para aislar el efecto
  "sin TACC" del ruido de la canasta completa.

## 3. Eje temporal

Serie mensual de `costo_T`, `costo_C` y `prima_celiaca` desde `2024-01`. Índices base 100 en
`2024-03`. Comparación con IPC INDEC (Nivel general y Alimentos y bebidas) para ver si la prima
se mueve con la inflación general o tiene dinámica propia.

## 4. Eje geográfico

- Prima por **provincia** y **región** (24 jurisdicciones, 6 regiones).
- **Mapa coroplético** de la prima por provincia + **mapa de sucursales** (Folium) con el costo
  celíaco por punto de venta.
- Test de dispersión: ¿la prima es mayor donde hay menos oferta sin TACC?

## 5. Eje de concentración de mercado (la hipótesis central)

**Hipótesis:** la prima celíaca es mayor donde el mercado de comercialización está más
concentrado (menos competencia → mayor poder de fijación de precios sobre un producto de
demanda inelástica como el sin TACC).

Medición de concentración por unidad geográfica `g` (`src/precios_sepa/concentracion.py`):

- **HHI** (Herfindahl-Hirschman) sobre la participación de cadenas en cantidad de sucursales
  (y, alternativamente, en cantidad de productos listados) dentro de `g`.
- **C4** (participación de las 4 cadenas más grandes).
- **Densidad**: sucursales por cada 100.000 habitantes (usando `poblacion_censo2022`).

**Análisis:** correlación / regresión de `prima_celiaca(g)` contra `HHI(g)`, controlando por
ingreso/densidad. Unidad de observación: provincia (y robustez a nivel de aglomerado si la
cobertura lo permite). Se explota la dimensión temporal (panel provincia×mes) para estimar con
efectos fijos.

## 6. Salidas del notebook `03_prima_celiaca.ipynb`

| Salida | Archivo |
|--------|---------|
| Serie temporal prima nacional + IPC | `outputs/figures/prima_serie.png` |
| Mapa coroplético de prima por provincia | `outputs/figures/prima_mapa.html` |
| Dispersión prima vs. HHI | `outputs/figures/prima_vs_hhi.png` |
| Tabla panel provincia×mes (prima, HHI, C4, densidad) | `outputs/tables/panel_prima.csv` |
| Tabla de resultados para el paper (con LaTeX) | `outputs/tables/resultados_prima.xlsx` |

## 7. Limitaciones a declarar en el paper

- SEPA publica **precios de lista**, no precios efectivos (sin promos ni descuentos por tarjeta).
- Cobertura sin TACC: no todos los reemplazos ideales existen en SEPA (pan y pastas de arroz
  tienen cobertura pobre; ver `docs/CALIDAD_DATOS.md`). Los reemplazos se eligen por cobertura.
- El SEPA cubre cadenas obligadas a reportar; excluye dietéticas y comercios de proximidad,
  donde suele venderse buena parte del sin TACC → la prima estimada es una **cota**.
- Concentración medida sobre sucursales SEPA, no sobre el total del mercado minorista.
