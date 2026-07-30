# Metodología — Artículo 1: La prima celíaca en Argentina

**Pregunta de investigación:** ¿Cuánto más gasta un consumidor celíaco que uno no celíaco al
comprar una canasta de consumo medio en Argentina? Y ese sobreprecio —la *prima celíaca*—,
¿cómo varía con (1) el tiempo, (2) la ubicación geográfica, (3) la concentración espacial de
los puntos de venta, y (4) la cadena/marca de supermercado?

> Las canastas se construyen **nuevas** para este proyecto (no se reutilizan las del proyecto
> previo). El criterio rector es la **representatividad geográfica**: los productos elegidos
> deben tener cobertura amplia en todo el país. Se permite que los productos sean **equivalentes,
> no necesariamente idénticos**, entre regiones; lo que importa es que la canasta esté
> disponible en toda la geografía.

---

## 1. Diseño de las dos canastas

Se construyen dos canastas de **consumo medio** representativo del consumidor argentino:

- **Canasta media (M):** conjunto de productos de consumo habitual (alimentos y bebidas de
  góndola), con cobertura geográfica nacional. Ver `config/canastas/canasta_tipo.csv`.
- **Canasta celíaca (C):** la misma canasta media, reemplazando **todos** los productos con
  gluten (trigo, cebada, centeno, avena) por equivalentes **sin TACC** (aptos celíacos) de
  cobertura comparable. Ver `config/canastas/canasta_celiaca.csv`.

Los ítems **naturalmente sin gluten** comunes a ambas (arroz, leche, aceite, frutas, etc.) son
idénticos en M y C; el motor del sobreprecio son los **ítems diferenciales** (harinas, pastas,
panificados, galletitas, rebozadores, cerveza, etc.).

### Criterio de selección: cobertura geográfica (no reutilizar canastas viejas)

Para cada **categoría** de consumo, se selecciona el/los producto(s) representativo(s) por su
**cobertura geográfica**, medida sobre la base real (join con el maestro de sucursales por
lat/lon). Métricas de cobertura por producto (`id_producto`):

- `n_provincias` / `n_regiones`: en cuántas provincias/regiones aparece con precio.
- `n_sucursales`: en cuántos puntos de venta.
- `dispersion_geografica`: extensión de la nube de sucursales que lo venden (bounding box o
  desviación de lat/lon) — para distinguir "muchas sucursales concentradas en AMBA" de
  "presencia realmente federal".
- `pct_meses`: estabilidad temporal (en cuántos meses del período aparece).

Un producto entra a la canasta si supera umbrales de cobertura (ej. presente en ≥20 provincias
y ≥N sucursales, con dispersión federal). **Equivalencia regional:** si ningún producto único
cubre todo el país, se admite un conjunto de productos equivalentes por región para la misma
categoría (misma función de consumo), siempre que juntos den cobertura nacional.

### Composición por categorías (a definir con los datos)

La canasta media se arma por categorías de consumo (referencia: canasta alimentaria tipo
ENGHo / INDEC, adaptada a lo que SEPA cubre con buena cobertura). Categorías candidatas con
diferencial celíaco (las que generan la prima):

| Categoría | Versión media (con gluten) | Reemplazo sin TACC |
|-----------|----------------------------|--------------------|
| Harinas | Harina de trigo 000/0000 | Harina/almidón sin TACC (maíz, arroz) |
| Pastas secas | Fideos de trigo | Fideos sin TACC (maíz/arroz) |
| Panificados | Pan lactal / galletitas de agua | Pan / galletas sin TACC |
| Galletitas dulces | Galletitas dulces de trigo | Galletitas sin TACC |
| Rebozador/pan rallado | Pan rallado de trigo | Rebozador sin TACC |
| Cerveza | Cerveza (malta/cebada) | Sidra / cerveza sin TACC |

> Las categorías **sin diferencial** (lácteos, aceites, arroz, azúcar, yerba, carnes/enlatados,
> bebidas, higiene) se incluyen igual en ambas canastas para reflejar el gasto total, pero se
> cancelan en la prima. La composición final se fija en `02_construccion_canastas.ipynb` a
> partir de la cobertura real (ver notebook).

---

## 2. Definición de la prima celíaca

Para un mes `m` y una unidad de observación `u` (puede ser una sucursal, una provincia, o el
país):

```
prima(m,u) = costo_C(m,u) / costo_M(m,u) − 1
```

donde `costo_X(m,u) = Σ_categoria precio(producto_categoria, m, u) × cantidad(categoria)`.

- **Precio** = precio mediano del producto en la unidad `u` y mes `m` (robusto a outliers).
- **Imputación:** si un producto no está en `u`, se imputa con su precio mediano nacional del
  mes (o el equivalente regional de su categoría, si se usa el esquema de equivalencia).
- Se reporta la **prima total** (canasta completa) y la **prima diferencial** (solo ítems que
  cambian) para aislar el efecto "sin TACC".

La unidad de observación más fina posible es la **sucursal** (con lat/lon), lo que habilita los
ejes geográfico y de concentración.

---

## 3. Eje TIEMPO

Serie mensual de `costo_M`, `costo_C` y `prima` desde `2024-01`. Índices base 100 en `2024-03`.
Comparación con IPC INDEC (Nivel general y Alimentos) para ver si la prima acompaña la inflación
general o tiene dinámica propia. Fuente IPC: `src/precios_sepa/indec.py`.

---

## 4. Eje GEOGRÁFICO (lat/lon)

- Prima por **sucursal** (georreferenciada), **provincia** y **región**.
- **Mapas**: coroplético de prima por provincia + mapa de sucursales (Folium) con la prima o el
  costo celíaco por punto de venta.
- Interpolación/superficie: opcionalmente, superficie de prima sobre el mapa (kriging o vecinos
  cercanos) para visualizar gradientes espaciales.

---

## 5. Eje CONCENTRACIÓN ESPACIAL de puntos de venta (hipótesis central)

**Hipótesis:** la prima celíaca es mayor donde hay **menos competencia espacial** entre puntos
de venta (mercado más concentrado → mayor poder de fijación de precios sobre un producto de
demanda inelástica como el sin TACC).

La concentración se mide con la **geometría de los puntos de venta** (lat/lon), no solo con la
participación de cadenas. Métricas por unidad geográfica `g` o por entorno de cada sucursal
(`src/precios_sepa/concentracion.py`):

1. **Densidad espacial**: sucursales por km² (o por cada 100.000 habitantes, Censo 2022) en `g`.
2. **Distancia al vecino más cercano**: para cada sucursal, distancia (haversine) a la sucursal
   más próxima; y **nº de competidores dentro de un radio R** (ej. 1, 3, 5 km). Menor distancia
   / más competidores = mercado más competido.
3. **Competidores de otras cadenas en el radio**: distingue competencia real (otra cadena) de
   sucursales de la misma cadena.
4. **HHI / C4** de cadenas dentro de `g` (participación por nº de sucursales), como métrica
   complementaria de estructura de mercado.

**Análisis:** panel `sucursal × mes` (o `provincia × mes`) regresando la `prima` contra las
métricas de concentración, con efectos fijos de tiempo y controles (densidad poblacional,
ingreso regional). Se espera signo **positivo** entre concentración y prima.

---

## 6. Eje CADENA / MARCA

- Prima y costo celíaco por **cadena** (`config/cadenas.csv`; las no identificadas se etiquetan
  sin descartar). ¿Hay cadenas sistemáticamente más caras para el consumidor celíaco?
- Interacción cadena × región: ¿la prima de una cadena varía según dónde opera?
- Filtro previo: quedarse con las cadenas que **venden alimentos** (excluir formatos no
  alimentarios como electro/departamental detectados en la exploración, ej. `id_comercio 2000`).

---

## 7. Salidas del notebook `03_prima_celiaca.ipynb`

| Salida | Archivo |
|--------|---------|
| Serie temporal de la prima nacional + IPC | `outputs/figures/prima_serie.png` |
| Mapa de sucursales con la prima | `outputs/figures/prima_mapa.html` |
| Coroplético de prima por provincia | `outputs/figures/prima_coropletico.png` |
| Dispersión prima vs. concentración espacial | `outputs/figures/prima_vs_concentracion.png` |
| Panel sucursal/provincia × mes (prima, densidad, vecino cercano, HHI, cadena) | `outputs/tables/panel_prima.csv` |
| Tabla de resultados para el paper (+ LaTeX) | `outputs/tables/resultados_prima.xlsx` |

---

## 8. Limitaciones a declarar en el paper

- SEPA publica **precios de lista**, no precios efectivos (sin promos ni descuentos por tarjeta).
- Cobertura sin TACC: no todos los reemplazos ideales existen en SEPA con buena cobertura
  (pan y pastas de arroz son escasos). Los reemplazos se eligen por cobertura → la prima es una
  **cota** de la real.
- SEPA cubre las cadenas obligadas a reportar; excluye dietéticas y comercios de proximidad,
  donde suele venderse buena parte del sin TACC.
- La concentración se mide sobre los puntos de venta SEPA, no sobre el total del mercado.
