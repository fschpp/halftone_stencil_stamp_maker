# PROGRESS

_Última actualización: 2026-10-30 00:30 (America/Argentina/Buenos_Aires) · rama: `main` (commit inicial)_

## Current Focus
Primera versión publicada: núcleo, CLI y GUI GTK4 escritos y 23 tests en verde. Falta ejecutar la GUI en una máquina con GTK4 y corregir lo que aparezca.

## Todo List
### [ ] Todo
- [ ] Probar la GUI en una máquina con GTK4 (en el entorno de desarrollo no hay GTK4)
- [ ] Paralelizar la exportación por baldosa (multiprocessing)

### [/] In Progress
- [/] Validación de la GUI en una máquina con GTK4 (pendiente del usuario)

### [x] Done
- [x] Repo clonado (estaba vacío) y plan guardado en `docs/`
- [x] `hsm/tools.py`: script `halftone_tools.py` del usuario incorporado tal cual (probeta + sellos); atajo en la raíz
- [x] `hsm/screen.py`: separación CMYK con GCR, rejilla hexagonal global, calibración, paso sugerido por distancia
- [x] `hsm/project.py`: proyecto JSON según Anexo B (+ `gcr`, `marco_alto_mm`)
- [x] `hsm/stencil.py`: stencil por baldosa (agujeros, marco exterior, 8 muescas en V), informe de diseño
- [x] `hsm/preview.py` y `hsm/session.py`: vistas (general, detalle de trama, mapa de baldosas) y lógica sin GTK
- [x] `hsm/cli.py`: `info`, `stencil`, `sellos`, `probeta`, `gui`
- [x] `hsm/gui.py`: GTK4 con controles por grupo, vista general/detalle/mapa/informe, exportación en hilo
- [x] Tests (`tests/`): 23 en verde (núcleo, CLI, grilla continua, mallas estancas, cableado de la GUI con `gi` simulado)
- [x] README, `requirements.txt`, `pyproject.toml`, `.gitignore`; commit inicial y push a `main`

## Latest Blockers/Discoveries
- **Triangulación lenta:** `trimesh.creation.extrude_polygon` (earcut) tardaba ~33–43 s por plancha de ~10 000 agujeros y el anillo del marco salía no estanco. Se reemplazó por `manifold3d` (CrossSection + extrusión por bandas de 25 mm + unión): ~5–10 s por plancha, malla estanca y de un solo cuerpo (verificado en 3 planchas de 250×250 mm).
- **Pared 1×3 m a 10 m:** el informe da 65 baldosas, 260 stencils, 266–533 h y ≈7,6 kg de PP (estimación del plan, a medir en la Fase 1b).
- **Sin GTK4 en el entorno de desarrollo:** `gi` está compilado para Python 3.12 y no hay typelib de Gtk 4.0; la GUI no se pudo ejecutar acá. El usuario interrumpió el intento de `apt-get install`, no se reintentó.
- `ejemplos.zip` del usuario (salidas de `halftone_tools.py`) no se subió al repo: STL de ~5 MB cada uno.
- Modo B (rejillas desplazadas) es experimental: falta validarlo en Fase 2.
