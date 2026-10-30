# Plan: stencils impresos en 3D para reproducir una fotografía a color por separación CMYK

**Versión:** 0.3.1 (borrador) — 2026-10-28
**Origen:** entrevista de análisis de sistemas con el cliente + relevamiento inicial del estado del arte.
**Marcas:** **[C]** confirmado por el cliente · **[I]** inferido o calculado por el analista, a validar con pruebas · **[P]** pendiente de aclarar.

---

## 0. Cómo leer este documento

**Glosario mínimo**
- **Stencil:** plancha delgada con agujeros; la pintura pasa solo por los agujeros.
- **Trama (halftone):** patrón regular de puntos cuyo tamaño varía para simular tonos continuos.
- **Paso (p):** distancia entre centros de agujeros vecinos.
- **Puente (w):** material que queda entre dos agujeros; si es muy fino, la plancha se rompe.
- **Cobertura:** fracción del área que queda pintada (0 % = nada, 100 % = todo).
- **Ganancia de punto:** el punto pintado sale más grande que el agujero, porque la pintura se filtra bajo el borde.
- **Registro:** que las 4 capas de color y las baldosas vecinas coincidan.
- **Baldosa:** porción de la imagen que cabe en una plancha de impresión.
- **Muaré:** patrón de interferencia no deseado entre tramas superpuestas.
- **Modo A / Modo B:** dos formas de combinar colores con pintura opaca (ver §6.4).

## 1. Resumen y veredicto de factibilidad

El cliente quiere reproducir una fotografía a color en una pared de **1 m × 3 m**, de modo que **desde la vereda se vea como una fotografía**, pintando con **aerosol a través de 4 stencils** (cian, magenta, amarillo y negro) impresos en 3D, como hace la imprenta con la trama de medios tonos. **[C]** El proceso debe ser **repetible en cualquier pared y con distintos diseños**: el cliente fija el tamaño final, la aplicación genera los STL y luego los aplica. **[C]**

La solución propuesta es una **aplicación de escritorio para Linux (Python + GTK)** que recibe la foto, el tamaño final y la distancia de observación, y entrega STL por baldosa y por color, con marcas de registro y marco, listos para una **Bambu Lab A1**. **[C]** También debe poder generar **sellos de TPU** para tintas al alcohol. **[C]**

### Veredicto por aspecto **[I]**

| Aspecto | Factibilidad | Motivo |
|---|---|---|
| Imprimir la trama | Alta | Pasos de 2–3 mm y agujeros ≥0,6 mm están al alcance de la A1 con boquilla de 0,4 mm |
| Resolución visual desde la vereda | Alta | Desde ≈10 m, un paso de ≈3 mm ya se funde en tono continuo |
| Pintar con aerosol sin que los agujeros se tapen ni se filtre | Media, incierta | Depende de la pintura, la distancia y el material; se mide en la Fase 1a |
| Rango tonal y color | Media | Un stencil cubre ≈33–58 %; el aerosol es opaco; el cliente acepta colores apagados |
| Prueba de mezcla con sellos de TPU y tintas al alcohol | Alta | Tintas translúcidas y TPU ya disponibles; valida el modelo de color, no el comportamiento del aerosol |
| Logística de piezas y tiempo (pared completa) | Baja a media | ≈200–260 stencils, ≈300–800 h de impresión y ≈3,5–5,5 kg de PP por diseño |
| Software | Alta | Las piezas son conocidas; el riesgo está en la calibración, no en la programación |

**Recomendación:** avanzar con una **prueba de concepto de bajo costo** (unas horas de impresión y una o dos latas) y decidir el tamaño del primer diseño recién después de medir el tiempo por baldosa (Fase 1b) y el comportamiento del color (Fase 2). Para una obra única, encargar una impresión comercial de gran formato sería más rápido; este plan asume que el valor está en el proceso propio y repetible.

## 2. Objetivo y alcance

**Incluye (versión 1):**
- Separación de una foto a color en 4 canales (C, M, Y, K). **[C]**
- Trama de medios tonos por agujeros, con ángulos distintos por color. **[I]**
- Cálculo del paso de trama a partir del **tamaño final** y la **distancia de observación**. **[C]** (la distancia es [P])
- División en baldosas, marcas de registro y marco. **[C]**
- Salida: STL por baldosa y por color. **[C]**
- Herramienta de calibración: probeta + medición sobre foto o escaneo, para compensar la ganancia de punto. **[I]**
- **Modo reducido de 2 o 3 tintas** (por ejemplo negro + amarillo, o negro + magenta + amarillo), que baja la cantidad de piezas en un 25–50 %. **[I]**
- Exportación opcional a **SVG/DXF**, para fabricar los mismos stencils con corte láser si la impresión 3D resulta inviable (§4). **[I]**
- **Modo sello (TPU):** el mismo motor genera sellos con pines en relieve para tintas al alcohol, más un marco de registro (§6.8, Anexo A2). **[C]**
- **Prueba de laboratorio de mezcla de color** con sellos de TPU y tintas al alcohol sobre papel (§11.4). **[C]**

**Fuera de alcance por ahora:**
- Aerógrafo y compresor: el cliente no tiene y prefiere **no comprar equipo nuevo**. **[C]**
- Sellos de TPU a escala de pared: no se plantea; el modo sello es para formatos chicos y pruebas de laboratorio (§6.8). **[I]**
- Colores muy vívidos: el cliente **acepta colores no vívidos**, aunque busca un resultado fotográfico y colorido. **[C]**
- Aplicación en exteriores: la pared es **lisa e interior**. **[C]**

## 3. Decisiones cerradas con el cliente

1. Medio: **aerosol**, sin comprar equipo nuevo. **[C]**
2. Calidad de color: aceptable con colores **no vívidos**. **[C]**
3. Primera prueba: **sobre papel pegado en la pared**, no directo sobre la pared. **[C]**
4. Primera pintura de prueba: **un solo negro** (Rust-Oleum Ultra Cover 2X brillante). **[C]**
5. Material de los stencils: **polipropileno (PP)**, con Magigoo PP y cama con cinta de polipropileno. **[C]**
6. Impresión en la **Bambu Lab A1**, dentro de un ropero. **[C]**
7. Software en **Python + GTK**, para Linux. **[C]**
8. El software también genera **sellos de TPU** (modo sello). **[C]**
9. Se hace una **prueba de laboratorio de mezcla de color** con sellos de TPU y tintas al alcohol (cian, magenta, amarillo y negro) sobre papel. **[C]**

## 4. Estado del arte y alternativas

### 4.1 Lo encontrado
- **Investigación académica:** *3D Printed Stencils for Texturing Flat Surfaces* (Vavilala et al., 2016) descompone una imagen en capas con transparencia, calcula un punteado (stippling) por capa, genera el stencil impreso en 3D y simula el efecto del spray. Es lo más cercano a esta idea.
- **Práctica de aerografía con piezas impresas:** Prusa documenta stencils impresos para aerografía y señala que, si el stencil se sostiene separado de la superficie, necesita ser más rígido (2–3 capas) para que no vibre con el aire. En MakerWorld hay stencils de ≈0,7 mm de espesor pensados para dar contacto cercano y evitar que la pintura se corra por debajo.
- **Serigrafía en FDM:** MeshFuse Screen funde una malla dentro de una pieza FDM para hacer pantallas sin emulsión.
- **Consejos de estarcido en pared:** el contacto plano es lo más importante; una pared lisa lo facilita, una base mate o satinada reduce la filtración bajo el borde, y se recomienda rociar perpendicular, a altura constante y en capas finas.
- **No se encontró** ningún proyecto que haga CMYK fotográfico completo con stencils FDM de agujeros. Puede ser un hueco real o falta de documentación. **[I]**

### 4.2 Alternativas de fabricación **[I]**

| Opción | Ventajas | Límites | Rol en el plan |
|---|---|---|---|
| Stencil FDM perforado (este plan) | Se hace en casa; geometría libre | Horas de impresión; espesor de 0,4–0,6 mm, que filtra más que un film fino | **Principal** |
| Film fino (≈0,1–0,2 mm) cortado con láser | Mejor contacto, menos filtración, más rápido por m², agujeros chicos | Requiere un servicio de corte o equipo; costo por diseño | **Plan B**, con exportación SVG/DXF desde el mismo software |
| Sellos de TPU (pines en relieve) | Funciona con las tintas al alcohol que ya tiene el cliente; sin puentes que limiten el tono; registro simple con un marco | Formato chico; otro proceso (entintado y presión); no sirve con aerosol | **Modo de salida soportado** y prueba de laboratorio (§6.8, §11.4) |
| Pantalla de serigrafía FDM (MeshFuse Screen) | No necesita agujeros | Otro proceso; requiere tinta y rasqueta | Línea futura de investigación |

## 5. Datos y recursos del cliente

| Tema | Dato |
|---|---|
| Objetivo | Pared de 1 m × 3 m, que se vea como foto desde la vereda; repetible en otras paredes y con otros diseños **[C]**. Orientación (vertical u horizontal): **[P]** |
| Superficie | Lisa, de interior **[C]** |
| Pintura | Aerosol, sin comprar equipo nuevo **[C]** |
| Aerosoles identificados | Rust-Oleum Ultra Cover 2X brillante, 340 g (negro para las primeras pruebas); Brillospray fluorescente amarillo, 240 cc **[C]**. Cian y magenta: **[P]** |
| Impresora | Bambu Lab A1 **[C]** |
| Material | PP: lo imprime sin problemas, con Magigoo PP, cama con cinta de polipropileno e impresora dentro de un ropero que actúa como gabinete; **3 rollos** **[C]**. Peso y color de cada rollo: **[P]** |
| Prueba inicial | Papel pegado en la pared **[C]** |
| Laboratorio de sellos | Tintas al alcohol cian, magenta, amarillo y negro, y TPU, disponibles en casa **[C]**. Papel brillante o con recubrimiento: **[P]** |
| Software | Python + GTK en Linux **[C]** |

## 6. Fundamentos técnicos y cálculos

Todos los valores de esta sección son **[I]** hasta que las probetas los confirmen.

### 6.1 Resolución según la distancia de observación
El ojo resuelve detalles de ≈1 minuto de arco (≈0,000291 rad). Para que la trama se funda en tono continuo, el paso debe ser menor que ≈ `distancia × 0,000291`.

| Distancia | Paso máximo aproximado |
|---|---|
| 5 m | 1,5 mm |
| 10 m | 2,9 mm |
| 15 m | 4,4 mm |

Con boquilla de 0,4 mm se pueden imprimir agujeros de ≈0,5–0,6 mm como mínimo. Un paso de 2,5–3 mm es un rango cómodo. La distancia real desde la vereda es **[P]**.

### 6.2 Límite de cobertura por stencil
Un stencil de agujeros necesita **puentes** de material entre agujeros. Con trama hexagonal de paso `p`, diámetro `d` y puente mínimo `w` (`d = p − w`):

`cobertura = 0,9069 × (d / p)²`

| Paso p | Puente w = 0,8 mm | Puente w = 0,6 mm |
|---|---|---|
| 2,0 mm | ≈33 % | ≈44 % |
| 2,5 mm | ≈42 % | ≈52 % |
| 3,0 mm | ≈49 % | ≈58 % |

**Consecuencia:** un solo stencil no cubre los tonos oscuros. Estos tienen que salir de la ganancia de punto, del stencil negro y de la superposición de colores. El software aplica una **curva de tonos** que comprime el rango: la reproducción tendrá menos contraste que la foto original.

### 6.3 Trama y muaré
Los ángulos clásicos (C 15°, M 75°, Y 0°, K 45°) son para tramas de puntos en **cuadrícula**, que se repiten cada 90°. En una trama **hexagonal** el patrón se repite cada 60°, y 15° y 75° coinciden: los puntos de cian y magenta quedarían exactamente superpuestos y no habría mezcla en rosetas (se detectó al revisar la vista previa del script). Para trama hexagonal se usa **C 15°, M 45°, Y 0°, K 30°**, con 15° entre todos los pares. Se ajusta con las pruebas. **[I]**

### 6.4 Ganancia de punto y opacidad del aerosol
- **Ganancia de punto:** sistemática; se compensa con una **curva de calibración** (cobertura pedida → diámetro de agujero) medida con la probeta.
- **Opacidad:** la mayoría de los aerosoles es opaca y el último color tapa al anterior. Dos modos:
  - **Modo A (superposición):** orden fijo de pintado (probable: amarillo, magenta, cian, negro) y se acepta la pérdida de mezcla.
  - **Modo B (sin superposición):** cada color usa una grilla desplazada, de modo que los puntos no se solapan y la mezcla es óptica. Si los cuatro colores comparten el área sin solaparse, cada uno puede ocupar como máximo ≈25 %: es un compromiso entre saturación y rango tonal.
  La Fase 2 define cuál conviene. El cliente acepta colores no vívidos. **[C]** La prueba de laboratorio con sellos y tintas al alcohol (§11.4) da una referencia del techo de color con tintas translúcidas. **[I]**

### 6.5 Logística de baldosas, material y tiempo

**Cantidad de piezas.** La cama de la A1 es de 256 × 256 mm. El marco ocupa parte de la plancha, así que la baldosa activa es de ≈240–250 mm. Para 1×3 m salen entre 48 y 65 baldosas por color, o sea **≈190–260 stencils por diseño**. Un modo de 3 tintas baja eso a ≈145–195; uno de 2 tintas, a ≈95–130.

**Material.** `V = A_total × espesor × (1 − cobertura_media de agujeros)`. Con `A_total` = 4 colores × 3 m² = 12 m², cobertura media de agujeros ≈25 %, marcos y registro +15 %:

| Espesor | PP (0,9 g/cm³) | PLA (1,24 g/cm³) |
|---|---|---|
| 0,4 mm | ≈3,7 kg | ≈5,1 kg |
| 0,6 mm | ≈5,6 kg | ≈7,7 kg |

Si los 3 rollos de PP son de 1 kg (**[P]**), alcanzan para ≈1,6–2,4 m² de pared en 4 colores. El diseño completo necesita 1 o 2 rollos más.

**Tiempo.** Con ≈11 500 agujeros por baldosa (paso 2,5 mm), el tiempo está dominado por los recorridos y retracciones entre agujeros más que por el volumen. Estimación gruesa: **1,5–3 h por baldosa**, o sea **≈300–800 h por diseño** (12 a 33 días de impresión continua), más un margen de impresiones fallidas. Es una de las mayores incógnitas del plan; la Fase 1b mide el tiempo real. Palancas para bajarlo: menos capas (0,4 mm en 2 capas), velocidades más altas, baldosas más chicas con menos agujeros por pieza, modo de 2 o 3 tintas, y paneles más chicos que la pared completa.

Cada diseño nuevo vuelve a pagar este costo, porque los stencils no se reutilizan entre imágenes distintas, aunque sí entre paredes que lleven el mismo diseño.

### 6.6 Comportamiento del PP
- **Ventajas probables:** buena resistencia química frente a los solventes del aerosol y baja adherencia de la pintura, que facilitaría despegar o limpiar el residuo.
- **Riesgos:** contracción de 1–2 % (en 250 mm son 2,5–5 mm, que rompen el registro entre baldosas), deformación de planchas finas y flexibilidad que hace vibrar la plancha con el aire del aerosol.
- **Mitigaciones:** calibrar la **escala por eje** en el software, usar un **marco más grueso** que dé rigidez, y fijar con cinta.

### 6.7 Detalles de diseño de la plancha
- **Cara de contacto plana:** se imprime apoyada sobre la cama (la primera capa es la cara que toca el papel o la pared) y el marco, más grueso, se levanta del lado exterior, hacia quien pinta. Un marco del lado del contacto separaría la plancha de la pared y aumentaría la filtración.
- **Compensación de agujeros:** la primera capa se aplasta contra la cama y el agujero sale algo más chico de ese lado. Se calibra con un parámetro de compensación de agujeros (la A1 y Bambu Studio traen una compensación XY de agujeros) y se mide en la probeta.
- **Muescas de alineación:** 8 muescas en V en el borde exterior del marco, a la altura de las líneas de la grilla (ver §9.6). Profundidad menor que el ancho del marco, para no debilitarlo.
- **Consumo de pintura:** desconocido. Se mide en las Fases 3 y 5 (**[P]**).

### 6.8 Modo sello (TPU)

Además de los stencils, el software genera **sellos de TPU**. **[C]** En lugar de una plancha con agujeros, el sello es una base con **pines en relieve** que se entinta y se apoya sobre el papel. La separación CMYK, los ángulos de trama y la curva de tonos son los mismos; solo cambia la geometría de salida (pines en lugar de agujeros) y se agrega un **marco de registro** (Anexo A2).

**Parámetros por defecto** **[I]**: TPU 95A impreso con alimentación directa (la A1 no lo admite en el AMS); base de 1,2 mm pegada a un taco rígido de 3–5 mm; pines de ≥0,6 mm de diámetro y 0,6–0,8 mm de alto (más altos se doblan); separación mínima entre pines de 0,4 mm; paso de 2,0–2,5 mm.

**Rango de cobertura.** Como no hay puentes que se rompan, el límite lo fija la separación entre pines (`d = p − 0,4 mm`):

| Paso p | Cobertura mínima (pin de 0,6 mm) | Cobertura máxima (separación 0,4 mm) |
|---|---|---|
| 2,0 mm | ≈8 % | ≈58 % |
| 2,5 mm | ≈5 % | ≈64 % |

La presión del sello ensancha los puntos, así que la cobertura real será mayor; la prueba la mide.

| Aspecto | Stencil | Sello |
|---|---|---|
| Geometría | Agujeros en una plancha | Pines en relieve sobre una base |
| Límite de tono | Puentes ≥0,6–0,8 mm (≈33–58 %) | Separación entre pines ≥0,4 mm (≈58–64 %) |
| Pintura | Aerosol | Tintas al alcohol u otras tintas de contacto |
| Registro | Grilla de líneas y muescas | Marco de registro con ventana |
| Escala | Pared, por baldosas | Formato chico y pruebas |
| Material | PP | TPU |

**Qué cubre y qué no.** Con tintas translúcidas, el sello permite validar el modelo de color (mezcla por superposición), los ángulos de trama y el registro sin usar aerosol. No valida la filtración bajo el borde, la opacidad ni el tapado de agujeros del aerosol. El modo sello no se propone para la pared completa: haría falta la misma cantidad de piezas y estampar con presión pareja a esa escala es otro problema. **[I]**

## 7. Arquitectura propuesta

**Lenguaje y toolkit:** Python 3 + GTK4 (PyGObject). **[C]**

| Capa | Tecnología | Rol |
|---|---|---|
| Interfaz | GTK4 | Cargar foto, fijar tamaño final y distancia, parámetros, vista previa, mapa de baldosas, exportación |
| Imagen | Pillow, numpy, scikit-image | Separación CMYK, curva de tonos, simulación de la trama |
| Trama | numpy | Rejillas hexagonales rotadas por canal, diámetro de agujero por celda |
| Geometría | shapely + triangulación (mapbox-earcut) o trimesh / manifold3d | Plancha con agujeros y marco, extrusión a STL |
| Calibración | numpy / Pillow | Medir la cobertura real en una foto o escaneo de la probeta |
| Proyecto | JSON | Foto, parámetros y curva de calibración (ver Anexo B) |

Notas de diseño **[I]**:
- Una baldosa de 250 × 250 mm con paso de 2,5 mm tiene ≈11 500 agujeros. Conviene **generar la malla directamente** (polígonos con agujeros extruidos) y no restar agujeros con booleanos, que sería lento.
- La herramienta trabaja en **milímetros finales** y expone el factor de compensación de escala por eje.
- Se desarrolla primero como **biblioteca y línea de comandos**; la interfaz GTK llega cuando el proceso esté validado.
- El modo sello reutiliza la separación y la trama; solo cambia la geometría de salida (pines en lugar de agujeros) y suma el marco de registro.

## 8. Flujo de uso

1. **Cargar foto.**
2. **Fijar el tamaño final** (por ejemplo 1000 × 3000 mm) y la **distancia de observación**; la app propone el paso de trama.
3. **Elegir salida** (stencil o sello de TPU), modo de trama (A o B), cantidad de tintas, material y curva de calibración.
4. **Vista previa** simulada de cada color y del resultado combinado, con aviso del rango tonal alcanzable.
5. **Mapa de baldosas** numerado, con las líneas de la grilla.
6. **Generar:** STL por baldosa y color + informe de validación (§10).
7. **Aplicar:** imprimir, marcar la grilla en el papel o la pared, fijar cada stencil y pintar color por color.

## 9. Módulos y algoritmos

1. **Separación CMYK** con generación de negro (reemplazo de gris), con opción de perfil ICC. A futuro, un **perfil de pinturas**: se pintan muestras de cada aerosol, se escanean y la simulación usa sus colores reales.
2. **Curva de tonos y calibración** (ver §11.2): mapea el tono deseado a la cobertura de stencil, respetando el máximo de §6.2 y la ganancia de punto medida.
3. **Trama por agujeros:** rejilla hexagonal rotada, con diámetro de cada agujero según la cobertura de su celda; diámetro mínimo y puente mínimo garantizados.
4. **Grilla global:** la rejilla se calcula en coordenadas de toda la imagen, y no por baldosa, para que los puntos sean continuos entre baldosas vecinas.
5. **Baldosas y marco:** el marco queda **fuera** del área activa, de modo que las áreas activas de baldosas vecinas se toquen exactamente. El marco de la baldosa siguiente cubre un borde ya pintado de la anterior. Orden de pintado y tiempos de secado: **[P]**.
6. **Registro por grilla de líneas y muescas:** se marca una sola vez, en el papel o la pared, una grilla de líneas verticales y horizontales cada `A` mm (el tamaño de la zona activa), con nivel láser, hilo con tiza o regla larga; las líneas coinciden con los bordes de las zonas activas. Cada stencil lleva **8 muescas en V** (2 por lado) en el borde exterior del marco, a la altura de esas líneas; al apoyarlo, la línea entra en cada muesca y el stencil queda ubicado y sin girar. Los 4 stencils de una baldosa tienen las muescas en el mismo lugar, así que el registro entre colores y entre baldosas depende de la grilla y no de apilar stencils. Se descartaron las ventanas en cruz: una ventana en la zona activa deja pasar pintura y tapa su propia marca, y las marcas bajo el marco del vecino quedan tapadas. Si la línea es de lápiz o tiza, se repasa donde la pintura la cubra. La precisión real se mide en la Fase 2. **[I]**
7. **Exportación:** STL binario en mm, agrupado por plancha para Bambu Studio. Opcional: SVG/DXF para corte láser.
8. **Modo sello:** genera pines en relieve en lugar de agujeros, con diámetro según la cobertura, y un marco de registro con ventana (§6.8, Anexo A2).

## 10. Validaciones automáticas

- Puente mínimo entre agujeros ≥ `w` (0,6–0,8 mm) y diámetro mínimo ≥ 0,5 mm. **[I]**
- Sin islas de material sueltas (partes del stencil desconectadas).
- Cobertura pedida ≤ máximo alcanzable; aviso si el tono se satura.
- Dimensiones tras la compensación de escala del material.
- Malla estanca (watertight), sin bordes no manifold.
- Informe por diseño: cantidad de baldosas, tiempo y material estimados, y zonas fuera de rango tonal.
- Modo sello: diámetro de pin ≥0,6 mm, separación entre pines ≥0,4 mm, altura de pin ≤0,8 mm, y que el sello entre en el marco de registro con la holgura prevista.

## 11. Plan de pruebas

### 11.1 Fase 1a: diseño de la probeta de punto
Plaquita de ≈100 × 100 mm, 0,6 mm de espesor, marco del lado exterior (§6.7) y 18 celdas: 3 pasos (2,0 / 2,5 / 3,0 mm) × 6 coberturas objetivo (8 / 16 / 24 / 32 / 40 / 48 %). Las celdas con puente menor que `w_min` se marcan y se imprimen igual, como prueba de límite. Más una **ventana abierta** de referencia (cobertura de pintura al 100 %). Detalle en el Anexo A.

Variables a probar sobre papel mate de 200–300 g pegado en la pared **[I]**:

| Variable | Valores |
|---|---|
| Material del stencil | PP y PLA (línea base) |
| Distancia de rociado | 15, 25 y 35 cm |
| Pasadas | 1 y 2 livianas |
| Repetición | 3 usos seguidos del mismo stencil |
| Pintura | Rust-Oleum negro; después otras |

### 11.2 Protocolo de medición y calibración
1. Pegar el papel plano, con una **regla o escala de referencia** a la vista.
2. Rociar con el protocolo de la tabla; despegar el stencil con cuidado.
3. Fotografiar con luz pareja (o escanear) y corregir perspectiva con la escala.
4. Binarizar (umbral automático) y calcular la **cobertura real de cada celda**.
5. Ajustar una curva monótona `cobertura real = f(cobertura del stencil)` por paso, distancia y pintura.
6. Guardar la curva en el proyecto (Anexo B) y usarla para invertir la corrección y para la vista previa.
7. Repetir cada celda 2 veces para estimar la dispersión.

### 11.3 Registro de tiempo
En cada impresión de prueba se anotan **horas y gramos** de la probeta y de las baldosas de 1b, para extrapolar el tiempo y material del diseño completo (§6.5).

### 11.4 Prueba de laboratorio con sellos de TPU

**Objetivo.** Verificar, a escala chica y sin aerosol, cómo se mezclan los 4 colores al superponer puntos de tinta translúcida, y validar la cadena de software (separación, trama, ángulos, simulación) y el registro con un marco. **[C]**

**Materiales.** TPU, tintas al alcohol cian, magenta, amarillo y negro, papel brillante o con recubrimiento (**[P]**), esponja o fieltro para entintar, taco rígido para cada sello, cinta, escáner o cámara con regla.

**Diseño.** 4 sellos de 40 × 40 mm (uno por tinta) y un marco de registro (Anexo A2). Imagen de prueba: una **carta de 3 × 3 parches** de 12 × 12 mm (cian, magenta, amarillo, rojo, verde, azul, los tres juntos, negro al 50 % y negro al 100 %), y opcionalmente una mini foto. Paso de 2,0 mm; repetir con 2,5 mm. Ángulos: C 15°, M 45°, Y 0°, K 30° (trama hexagonal; ver §6.3). **[I]**

**Procedimiento** **[I]**:
1. Imprimir los 4 sellos en TPU y el marco en PLA o PP; pegar cada sello a su taco.
2. Fijar el marco con cinta sobre el papel.
3. Entintar con esponja (unas gotas de tinta) y sellar en orden amarillo, magenta, cian, negro, con ≈30 s de espera entre capas. Repetir en otra hoja con el orden inverso.
4. Escanear a ≥600 dpi, o fotografiar con una regla en el cuadro.
5. Medir: cobertura real vs diseñada por parche (ganancia de punto del sello), color de cada parche, desplazamiento de cada capa respecto de la grilla esperada y arrastre entre capas.
6. Comparar con la simulación del software y ajustar la curva de tonos por canal.

**Criterios de éxito** **[I]**: ganancia de punto ≤+30 % de área; error de registro ≤0,3 mm; rojo, verde y azul reconocibles y parecidos a la simulación; sin arrastre que borre puntos.

**Qué decide.** Si el color con tintas translúcidas es aceptable (y entonces vale la pena buscar pinturas translúcidas para el stencil), la curva de tonos inicial por canal, y si el marco de registro alcanza la precisión esperada.

## 12. Fases, esfuerzo y criterios go / no-go

Esfuerzos de desarrollo **[I]**, sin contar el tiempo de impresión.

| Fase | Entregable | Esfuerzo | Criterio de aceptación | Si falla |
|---|---|---|---|---|
| **0. Script de probeta** | Script Python que genera el STL de la probeta (Anexo A) | 1–2 días | Se imprime en PP y PLA sin errores | Revisar geometría o configuración de impresión |
| **0b. Laboratorio de sellos de TPU** | 4 sellos de 40 × 40 mm, marco de registro y carta de parches (Anexo A2); prueba sobre papel con tintas al alcohol (§11.4) | 1–2 días, sobre el motor de la Fase 0 | Ganancia de punto ≤+30 %; registro ≤0,3 mm; mezcla comparable con la simulación | Ajustar altura y diámetro de pines, entintado y papel; revisar el modelo de color |
| **1a. Probeta, negro solo** | Datos de ganancia de punto y tapado, PP vs PLA | 2–3 días | Curva repetible (±10 %); agujeros que sobreviven ≥3 usos con <10 % de pérdida de área | Cambiar pintura, distancia o técnica; subir el diámetro mínimo a ≥1 mm; evaluar el plan B de film cortado con láser |
| **1b. Foto en escala de grises** | 1 stencil de ≈200 × 200 mm | 3–5 días | Foto reconocible a 3 m; tiempo por baldosa medido | Ajustar curva y trama; replantear el tamaño del primer diseño con el tiempo medido |
| **2. Negro + amarillo** | 2 stencils con registro por grilla | 2–3 días | Error de registro < 1 mm; se define modo A o B | Revisar registro; probar modo B |
| **3. CMYK completo** | 4 stencils de ≈200 × 200 mm | 1–2 días | Foto reconocible a color a la distancia objetivo | Evaluar aerosoles translúcidos o el modo de 2–3 tintas |
| **4. Aplicación GTK** | Interfaz con tamaño final, distancia, vista previa, mapa de baldosas y elección de salida (stencil o sello) | 2–3 semanas | Una foto nueva se convierte en STL sin tocar código | Mantener la línea de comandos como interfaz |
| **5. Panel mediano** | ≈0,5–1 m², primero sobre papel y luego sobre pared | Según tiempo de impresión | Registro entre baldosas aceptable; consumo de pintura medido | Reducir el tamaño de baldosa o la cantidad de tintas |
| **6. Pared 1×3 m** | Diseño completo | Según tiempo de impresión | Se ve como foto desde la vereda | Dividir en etapas |

## 13. Riesgos y mitigaciones

| # | Riesgo | Mitigación |
|---|---|---|
| R1 | Cantidad de piezas y horas de impresión por diseño (≈190–260 stencils, ≈300–800 h) | Medir en 1b; panel chico primero; menos capas; modo de 2–3 tintas; baldosas con menos agujeros |
| R2 | Agujeros que se tapan con la pintura | Pasadas livianas; limpiar el stencil; PP por baja adherencia; medir en 1a |
| R3 | Ganancia de punto fuerte con la Rust-Oleum Ultra Cover 2X (pintura de alta cobertura) | Curva de calibración; probar distancias; probar otras pinturas |
| R4 | Aerosol opaco: no mezcla al superponerse | Modo B; buscar aerosoles translúcidos |
| R5 | Rango tonal limitado (≈33–58 % por stencil) | Curva de tonos; aceptar menor contraste |
| R6 | Contracción y deformación del PP rompen el registro | Compensar escala por eje; marco rígido del lado exterior; baldosas más chicas; registro por grilla de pared |
| R7 | Los solventes del aerosol dañan el PLA si se usa de línea base | Probar con plaquita de descarte; el PP resiste mejor |
| R8 | Impresión dentro de un ropero: la A1 no está diseñada para un gabinete cerrado y puede sobrecalentarse; riesgo de calor y humos | Vigilar la temperatura ambiente, ventilar, no dejar impresiones largas sin supervisión, detector de humo cerca |
| R9 | Pintar con aerosol en interior (solventes, overspray) | Ventilar, respirador adecuado, proteger piso y paredes cercanas |
| R10 | La pared tiene textura leve o pintura brillante y filtra más | Base blanca mate; fijar con cinta o adhesivo removible; probar en la pared real |
| R11 | Falta de transparencia y de cian/magenta adecuados | Alcance reducido a 2–3 tintas como entregable intermedio |
| R12 | Costos y consumo de pintura desconocidos | Medir en 3 y 5 antes de comprometer la pared completa |
| R13 | Las tintas al alcohol se reactivan con la capa siguiente y arrastran el color | Esperar entre capas; probar el orden inverso; papel brillante o con recubrimiento |
| R14 | Los pines de TPU se doblan o salen irregulares | Altura ≤0,8 mm; diámetro ≥0,6 mm; impresión lenta |
| R15 | La tinta se corre en papel común y borra los puntos | Papel brillante, con recubrimiento o sintético |

## 14. Preguntas abiertas

1. **[P]** Distancia real de observación desde la vereda (define el paso de trama).
2. **[P]** Orientación de la pared (vertical u horizontal) y proporción de las fotos.
3. **[P]** Cuántas horas de impresión y cuánto filamento por diseño está dispuesto a invertir el cliente.
4. **[P]** Peso y color de cada rollo de PP.
5. **[P]** Dónde conseguir aerosoles translúcidos o, al menos, cian y magenta.
6. **[P]** Cómo se fija cada stencil (cinta, adhesivo removible, imanes) y cómo se traza la grilla de líneas (nivel láser, hilo con tiza, regla larga).
7. **[P]** Cómo se medirá la probeta (escáner o foto con regla de referencia).
8. **[P]** Si se aceptan baldosas más chicas que la cama si la deformación del PP lo exige.
9. **[P]** Orden de pintado y tiempos de secado entre baldosas vecinas.
10. **[P]** Ventilación y temperatura ambiente del ropero donde se imprime (ver R8).
11. **[P]** Qué papel hay disponible para la prueba de sellos (brillante, con recubrimiento o sintético).
12. **[P]** Marca y tipo de las tintas al alcohol, y de qué material será el taco rígido de los sellos.

## 15. Primera semana

1. Escribir el script de la probeta (Fase 0) e imprimirla en **PP y PLA**, anotando horas y gramos.
2. Conseguir: papel mate de 200–300 g, cinta de enmascarar de baja adherencia, una regla o escala de referencia, hilo con tiza o nivel láser para la grilla, respirador con filtro para vapores orgánicos y protección para el piso.
3. Armar el sitio de prueba: papel plano pegado en la pared, ventilación, protección del entorno.
4. Rociar con el negro a 2–3 distancias y 1–2 pasadas; repetir 3 veces con el mismo stencil.
5. Fotografiar o escanear, medir la cobertura de cada celda y trazar la primera curva.
6. Decidir con los criterios de la §12 si se sigue con 1b o se ajusta antes.
7. En paralelo, y con lo que ya hay en casa: imprimir los 4 sellos de TPU y el marco (Fase 0b) y hacer la prueba de mezcla con las tintas al alcohol (§11.4).

---

## Anexo A. Especificación del script de probeta (Fase 0)

**Entrada (parámetros):**
- `--size` (mm, por defecto 100), `--thickness` (mm, por defecto 0,6), `--frame` (ancho y alto del marco; el marco se levanta del lado exterior).
- `--pitches` (por defecto 2,0 2,5 3,0), `--coverages` (por defecto 8 16 24 32 40 48), `--w-min` (por defecto 0,6), `--d-min` (por defecto 0,5), `--hole-comp` (compensación de agujeros, por defecto 0).
- `--angle` (ángulo de la trama, por defecto 45), `--scale` (factor de escala por eje para compensar la contracción del material).

**Cálculo por celda:** `d = p × sqrt(c / 0,9069)`, con `c` la cobertura objetivo; puente `w = p − d`. Si `w < w-min` o `d < d-min`, la celda se marca como "fuera de límite" y se genera igual.

**Valores calculados de referencia (diámetro d en mm):**

| Cobertura | p = 2,0 | p = 2,5 | p = 3,0 |
|---|---|---|---|
| 8 % | 0,59 | 0,74 | 0,89 |
| 16 % | 0,84 | 1,05 | 1,26 |
| 24 % | 1,03 | 1,29 | 1,54 |
| 32 % | 1,19 | 1,49 | 1,78 |
| 40 % | 1,33 | 1,66 | 1,99 |
| 48 % | 1,46 (w = 0,54, fuera de límite) | 1,82 | 2,18 |

**Salida:**
- `probeta_<material>_t<espesor>.stl`: plancha con agujeros, marco y una ventana abierta de referencia.
- `probeta_layout.json`: para cada celda, su posición, paso, diámetro, cobertura objetivo, puente y si está dentro de límite.

**Verificaciones:** malla estanca, dimensiones totales, cantidad de agujeros por celda, ausencia de agujeros que crucen el marco, resumen impreso en consola.

## Anexo A2. Especificación del modo sello y del marco de registro (Fase 0b)

**Entrada (parámetros):**
- `--source` (`chart` o `photo`), `--image` (ruta de la foto, si `photo`), `--size` (mm, por defecto 40), `--pitch` (mm, por defecto 2,0), `--angles` (por defecto C 15, M 45, Y 0, K 30, para trama hexagonal), `--gcr` (reemplazo de gris por negro en modo foto; por defecto 0,6).
- `--base` (espesor de la base, por defecto 1,2 mm), `--pin-h` (altura de pin, por defecto 0,7 mm), `--pin-min` (diámetro mínimo, por defecto 0,6 mm), `--gap-min` (separación mínima entre pines, por defecto 0,4 mm).
- `--chamfer` (chaflán de una esquina, para evitar colocar el sello girado; por defecto 3 mm).
- `--jig-clearance` (holgura de la ventana, por defecto 0,3 mm), `--jig-thickness` (por defecto 4 mm), `--jig-margin` (ancho del marco alrededor de la ventana, por defecto 15 mm).

**Cobertura y diámetro:** `d = p × sqrt(c / 0,9069)`, acotado a `pin-min ≤ d ≤ p − gap-min`. El valor "100 %" de una tinta equivale a la cobertura máxima del sello.

**Carta de parches** (3 × 3, parches de 12 mm con 1 mm de separación dentro de los 40 mm): cian, magenta, amarillo, magenta+amarillo (rojo), cian+amarillo (verde), cian+magenta (azul), cian+magenta+amarillo, negro al 50 %, negro al 100 %.

**Geometría:**
- Sello: base de `size × size × base` con un chaflán en una esquina; pines cilíndricos que se hunden 0,1 mm en la base; se descartan los pines que queden a menos de 1 mm del borde.
- Marco de registro: placa de `size + 2 × jig-margin` de lado y `jig-thickness` de alto, con una ventana pasante de `size + jig-clearance` y el mismo chaflán.

**Salida:**
- `sello_C.stl`, `sello_M.stl`, `sello_Y.stl`, `sello_K.stl` y `marco_registro.stl`.
- `layout.json`: parámetros usados, cantidad de pines por sello y cobertura diseñada por parche.
- `preview.png`: simulación sobre papel blanco, con las 4 capas superpuestas.

**Verificaciones:** malla estanca, diámetro y separación mínimos, ajuste del sello en la ventana, resumen impreso en consola.

## Anexo A3. Script `halftone_tools.py` (Fases 0 y 0b)

Primera versión del script de línea de comandos que implementa los Anexos A y A2. Dependencias: `numpy`, `shapely` (≥2), `trimesh`, `mapbox-earcut`, `manifold3d` y `pillow`.

```
python3 halftone_tools.py probeta --out salida/ --material PP
python3 halftone_tools.py sellos  --source chart --out salida/
python3 halftone_tools.py sellos  --source photo --image foto.jpg --size 100 --pitch 2.5 --out salida/
```

**Estado de validación:** las salidas de ejemplo se generaron con éxito y todas las mallas resultaron estancas; la vista previa se revisó a ojo. **Falta** imprimir las piezas, confirmar que los pines de TPU salen bien, que el sello entra en la ventana del marco y que el sello girado sobre el eje Y queda con la orientación correcta sobre el papel. **[P]**

**Notas de uso:**
- Los sellos se exportan listos para imprimir con los pines hacia arriba; para usarlos se les da vuelta alrededor de su lado vertical (eje Y). La esquina con chaflán evita colocarlos girados.
- Con un sello de 40 mm y paso de 2 mm hay solo ≈20 puntos de lado: sirve para la carta de parches, pero una foto necesita un sello más grande o un paso más fino (por ejemplo 100 mm con paso de 2,5 mm).
- En modo foto, `--gcr` controla cuánto gris se imprime con negro (0 = nada, 1 = todo).
- El script avisa si dos ángulos de trama son equivalentes en una trama hexagonal.

## Anexo B. Esquema del archivo de proyecto (borrador)

```json
{
  "version": 1,
  "imagen": "foto.jpg",
  "ancho_mm": 3000,
  "alto_mm": 1000,
  "distancia_observacion_mm": 10000,
  "tintas": ["C", "M", "Y", "K"],
  "salida": "stencil",
  "trama": {
    "modo": "A",
    "paso_mm": 2.5,
    "angulos": {"C": 15, "M": 45, "Y": 0, "K": 30},
    "puente_min_mm": 0.6,
    "diametro_min_mm": 0.5
  },
  "material": {
    "nombre": "PP",
    "factor_escala": [1.0, 1.0],
    "compensacion_agujero_mm": 0.1
  },
  "plancha": {
    "espesor_mm": 0.6,
    "baldosa_activa_mm": [240, 240],
    "marco_mm": 5
  },
  "sello": {
    "base_mm": 1.2,
    "pin_alto_mm": 0.7,
    "pin_min_mm": 0.6,
    "separacion_min_mm": 0.4
  },
  "calibracion": {
    "pintura": "Rust-Oleum Ultra Cover 2X negro",
    "distancia_rociado_mm": 250,
    "curva": [[0, 0], [0.5, 0.5]]
  }
}
```

Los valores son ejemplos, no medidas.

## Anexo C. Fuentes (consultadas 2026-10-28)

- https://deepai.org/publication/3d-printed-stencils-for-texturing-flat-surfaces
- https://blog.prusa3d.com/airbrushing-tricks-with-3d-printed-stencils_136901/
- https://makerworld.com/models/2214009
- https://www.makerworld.com/en/models/2497606
- https://forum.bambulab.com/t/printing-with-polypropylene-pp-filament-and-magigoo-pp/60868
- https://shop.spectrumfilaments.com/eng_m_Our-offer_Materials_PP-2628.html

## Registro de cambios

**v0.3** (2026-10-28)
- Se incorpora el **modo sello (TPU)** como salida del software (§6.8, Anexo A2) y la **prueba de laboratorio** con tintas al alcohol (§11.4, Fase 0b).
- Los sellos dejan de estar descartados: pasan a ser modo de salida soportado, para formatos chicos y pruebas.
- Nuevos riesgos (R13–R15), pendientes (11–12) y recursos (tintas al alcohol, TPU).

**v0.3.1** (2026-10-28)
- Corregidos los ángulos de trama: con trama hexagonal, 15° y 75° coinciden; el valor por defecto pasa a C 15°, M 45°, Y 0°, K 30° (§6.3).
- Primera versión del script `halftone_tools.py` (probeta de stencil, sellos de TPU y marco de registro), probada con salidas de ejemplo.

**v0.2.1** (2026-10-28)
- Corregido el método de registro: se reemplazan las ventanas en cruz por una grilla de líneas y muescas en el borde del marco (§9.6, §6.7).

**v0.2** (2026-10-28)
- Corregidas al alza las estimaciones de tiempo (≈300–800 h) y de material (PP ≈3,7–5,6 kg), con la fórmula a la vista; la cantidad de stencils pasa a ≈190–260 por el espacio del marco.
- Agregados: veredicto de factibilidad, glosario, decisiones cerradas, alternativas de fabricación (film cortado con láser como plan B, exportación SVG/DXF) y modo reducido de 2–3 tintas.
- Diseño de la plancha: cara de contacto plana con el marco del lado exterior y compensación de agujeros.
- Registro por grilla de pared y grilla global de trama para continuidad entre baldosas.
- Plan de pruebas detallado: variables, protocolo de medición y calibración; fases con esfuerzo y criterios go / no-go.
- Anexos: especificación del script de probeta, esquema del proyecto y fuentes.
- Nuevos pendientes: orientación de la pared, peso de los rollos, fijación y grilla, orden de pintado.
- Se quitaron del documento datos del entorno de desarrollo del cliente que no hacían falta.

**v0.1** (2026-10-28): primera versión, a partir de la entrevista.
