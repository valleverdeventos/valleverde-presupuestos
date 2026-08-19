# Sistema de presupuestos

Los presupuestos ya no se escriben a mano en HTML. Se escribe un archivo de datos
chico y el HTML lo arma un script a partir de una plantilla única.

## Por qué

Cada página pesa ~37 KB. Entre dos presupuestos distintos, el 81% del contenido es
idéntico: sólo cambian el cliente, la fecha, los invitados y los precios. Escribir la
página entera cada vez significaba que el modelo produjera ~9.300 tokens de los cuales
~7.500 eran siempre lo mismo.

Con este sistema el modelo escribe sólo el archivo de datos: ~390 tokens. **24 veces menos.**

Además resuelve un problema que venía de arrastre: había 7 versiones distintas del CSS
conviviendo entre presupuestos, y 5 redacciones distintas de los términos y condiciones.
Ahora hay una sola plantilla, así que todos salen visualmente iguales y cambiar el diseño
los actualiza a todos de una.

## Cómo se usa

Para un presupuesto nuevo, crear `sistema/datos/<slug>.json` y correr:

```
python sistema/render.py <slug>
```

Para regenerar todos (por ejemplo después de tocar la plantilla):

```
python sistema/render.py --todos
```

El slug es el nombre de la carpeta en `presupuestos/`, con el formato
`<cliente>-<tipo-evento>-<AAAA-MM-DD>`.

## Formato del archivo de datos

```json
{
  "titulo": "Cumpleaños 40 años",
  "cliente": "Mariana",
  "fecha": "26/09/2026",
  "horario": "21:00 a 03:00",
  "invitados": 50,
  "aviso": "Propuesta: Salón + Barra de tragos + Finger Food...",
  "servicios": [
    { "nombre": "Salón (incluye personal completo y DJ)", "precio": 26200 },
    { "nombre": "Barra de tragos (con alcohol)", "precio": 21000 }
  ],
  "terminos": [
    "Seña 35%: con la reserva del salón.",
    "Saldo 65%: 20 días antes del evento."
  ]
}
```

Campos:

- `precio` es el valor **por persona**. El total lo calcula el script.
- `cantidad` es opcional dentro de cada servicio. Si no está, usa `invitados`. Sirve para
  los casos de barra dividida — por ejemplo 25 adultos y 75 adolescentes en un 15 años.
- `aviso_clase` es opcional: `aviso-catering` (naranja, para propuestas con opciones) o
  `aviso-valores` (neutro). Si no está, se elige según haya opciones o no.
- `nota` es opcional: un párrafo al pie de la tabla de precios.
- `cliente` es opcional. Si no está, la portada sale con 3 columnas (Fecha / Horario /
  Invitados), sin el campo Cliente, tal como pide la regla de "presupuesto sin nombre".
- `cliente_label` es opcional: cambia el rótulo de esa celda, por ejemplo a `"Teléfono"`
  cuando hay WhatsApp pero no nombre.
- `invitados_texto` es opcional: cambia sólo lo que se muestra en la portada, sin tocar
  el número que se usa para calcular.
- `opciones` es opcional. Sin ella se muestra un total único con la suma de todos los
  servicios. Con ella se muestra un total por opción:

```json
"opciones": [
  { "tag": "Opción Base — Salón + Barra",
    "label": "Total (Salón + Barra de tragos)",
    "servicios": [0, 1] },
  { "tag": "Opción A — con Finger Food",
    "label": "Total (incluye Salón, Barra y Finger Food)",
    "servicios": [0, 1, 2] }
]
```

`servicios` son los índices del array `servicios`, empezando en 0. El color de cada
etiqueta se asigna solo, o se fija con `"color": "#8E0E3E"`.

Para la forma antigua de mostrar totales — sueltos, uno debajo del otro, sin etiqueta de
color — se agrega `"simple": true` a cada opción y se omite `tag`.

## Archivos

| Archivo | Para qué |
|---|---|
| `plantilla.html` | La plantilla única, con marcadores `{{...}}` |
| `render.py` | Arma el `index.html` de un presupuesto desde su JSON |
| `datos/*.json` | Un archivo por presupuesto |
| `build_plantilla.py` | Regenera la plantilla desde una página existente. Se corrió una vez |
| `extraer.py` | Migró los 43 presupuestos que ya existían al formato nuevo. Se corrió una vez |

`build_plantilla.py` y `extraer.py` son herramientas de migración. En el uso diario
alcanza con `render.py`.

## Validación

La migración se verificó comparando los 43 presupuestos generados contra los originales:
todos los importes coinciden, salvo un caso donde el original estaba mal (ver abajo).

**Corrección aplicada — `vanesa-cumpleanos-40-2026-09-19`:** la página publicada mostraba
cantidad 60 y precio unitario $24.617, pero el subtotal del salón decía $1.230.850, que
corresponde a 50 personas. El total general ya usaba 60 ($2.647.020). El sistema recalcula
el subtotal como $1.477.020, que es el valor consistente con el resto de la página.
