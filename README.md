# halftone_stencil_stamp_maker

Convierte una fotografía en **stencils** (planchas con agujeros para pintar con aerosol) o **sellos de TPU**
(pines en relieve para tintas al alcohol) mediante separación CMYK y trama de medios tonos, listos para
imprimir en 3D. Implementa el plan de `docs/plan_stencils_impresos_3d_color_mejorado.md` (v0.3.1).

## Qué hace hoy

| Función | Estado |
|---|---|
| Separación CMYK con reemplazo de gris, curva de calibración, paso sugerido por distancia | listo |
| Stencils por baldosa y por tinta (agujeros, marco en relieve del lado exterior, 8 muescas en V) | listo, mallas estancas verificadas |
| Grilla de trama global (puntos continuos entre baldosas vecinas) | listo, con test |
| Informe: baldosas, stencils, horas y material estimados, avisos | listo (estimaciones del plan, **[I]**) |
| Vista previa: resultado general, detalle de trama real, mapa de baldosas | listo |
| Sellos de TPU, marco de registro y probeta (Fases 0 y 0b, script original `halftone_tools.py`) | listo, desde CLI y GUI |
| GUI GTK4 | escrita; **no se pudo ejecutar donde se desarrolló** (ver abajo) |
| Exportación SVG/DXF (plan B con corte láser), perfil de pinturas, medición automática de la probeta | pendiente |

## Instalación (Debian/Ubuntu)

```bash
sudo apt install python3-gi gir1.2-gtk-4.0 python3-numpy python3-scipy python3-pil
python3 -m venv --system-site-packages .venv && . .venv/bin/activate
pip install shapely trimesh mapbox-earcut manifold3d
```

Sin GUI alcanza con `pip install -r requirements.txt`.

## Uso

```bash
python3 -m hsm gui                       # interfaz gráfica (o: python3 -m hsm gui --project mi.json)

# informe de diseño sin generar nada
python3 -m hsm info --width 1000 --height 3000 --distance 10000

# una baldosa de prueba, solo negro y amarillo
python3 -m hsm stencil --image foto.jpg --width 480 --height 240 --distance 10000 \
        --inks KY --tiles 0,0 --out salida/

# toda la pared (65 baldosas x 4 tintas: tarda; ~5-10 s por plancha)
python3 -m hsm stencil --image foto.jpg --width 1000 --height 3000 --distance 10000 --out salida/

# fases 0 y 0b del plan
python3 -m hsm probeta --out salida/ --material PP
python3 -m hsm sellos --source chart --out salida/
python3 halftone_tools.py sellos --source photo --image foto.jpg --size 100 --pitch 2.5 --out salida/
```

Cada exportación de stencils escribe `stencil_xNN_yNN_<tinta>.stl`, `proyecto.json` (reabrible desde la GUI o con
`--project`), `informe.json` y `mapa_baldosas.png`.

## Detalles que conviene saber

- **Orientación:** el STL del stencil se imprime con la cara de contacto sobre la cama; el marco sube del lado
  exterior. Al apoyarlo en la pared se ve desde el mismo lado que en el slicer (no hay espejado). Los sellos sí se
  exportan listos para imprimir y hay que darlos vuelta alrededor del eje Y (esa orientación está **sin validar**
  con una impresión real, ver el plan, Anexo A3).
- **Registro:** marcá en el papel o la pared una grilla cada `zona activa` mm (240 por defecto); las muescas del
  marco se apoyan sobre esas líneas.
- **Rango tonal:** un stencil cubre como mucho ≈52 % con paso 2,5 mm y puente 0,6 mm; la vista general lo muestra.
- **Calibración:** la curva medida va en `calibracion.curva` del proyecto como `[[cobertura del stencil, cobertura
  real], ...]`; todavía no hay herramienta para medirla automáticamente.
- **Modo B** (rejillas desplazadas por tinta) es experimental.

## Tests

```bash
python3 -m pytest
```

La prueba de la GUI usa un `gi` simulado (verifica el cableado de los controles, no el aspecto).

## Estructura

```
hsm/screen.py    separación CMYK, rejilla hexagonal global, calibración
hsm/stencil.py   plancha por baldosa (manifold3d), informe de diseño
hsm/tools.py     probeta y sellos (script original de las Fases 0 y 0b)
hsm/preview.py   vistas simuladas
hsm/session.py   lógica de la app (sin GTK)
hsm/gui.py       interfaz GTK4
hsm/cli.py       línea de comandos
docs/            plan del proyecto
```
