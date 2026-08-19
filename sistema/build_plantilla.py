"""Genera sistema/plantilla.html a partir de la pagina mas completa del repo.

Se corre una sola vez, o cuando se quiera re-basar la plantilla sobre otra pagina.
El flujo diario usa unicamente plantilla.html + render.py.
"""
import re
import pathlib

RAIZ = pathlib.Path(__file__).resolve().parent.parent
BASE = RAIZ / "presupuestos" / "valeria-cumple-15-2027-09-18" / "index.html"
SALIDA = pathlib.Path(__file__).resolve().parent / "plantilla.html"

CSS_FALTANTE = (
    "  .aviso-valores { margin: 18px 0 24px; padding: 20px 22px; "
    "background: rgba(247,241,230,0.04); border: 1px solid rgba(247,241,230,0.18); "
    "border-left: 5px solid var(--accent); border-radius: 3px; font-size: 16px; "
    "line-height: 1.65; color: var(--text); }\n"
)

html = BASE.read_text(encoding="utf-8")

# 1. CSS canonico: base + la regla que le faltaba.
if ".aviso-valores" not in html:
    html = html.replace("</style>", CSS_FALTANTE + "</style>", 1)

# 2. Titulo del evento en la portada.
html = re.sub(r'(<h1 style="margin-bottom:4px;">)[^<]*(</h1>)', r"\1{{TITULO}}\2", html, count=1)

# 3. Datos del cliente.
for campo in ("Cliente", "Fecha", "Horario", "Invitados"):
    html = re.sub(
        r'(<span class="label">%s</span>)[^<]*(</div>)' % campo,
        r"\1{{%s}}\2" % campo.upper(),
        html,
        count=1,
    )

# 4. Aviso previo a la tabla: cambia de texto y de clase segun la propuesta.
html = re.sub(
    r'[ \t]*<div class="aviso-(?:catering|valores)">.*?</div>\n',
    "    {{AVISO}}\n",
    html,
    count=1,
    flags=re.S,
)

# 5. Bloque de precios completo, hasta el encabezado de terminos.
html = re.sub(
    r'[ \t]*<div id="tabla-precios">.*?(?=\n[ \t]*<div class="eyebrow")',
    "    {{TABLA_PRECIOS}}",
    html,
    count=1,
    flags=re.S,
)

# 6. Terminos y condiciones: el texto cambia segun el tipo de evento.
html = re.sub(
    r'(<div class="eyebrow"[^>]*>Términos y condiciones</div>\n)'
    r'(?:[ \t]*<div class="feature".*?</div>\n)+',
    r"\1    {{TERMINOS}}\n",
    html,
    count=1,
    flags=re.S,
)

SALIDA.write_text(html, encoding="utf-8")

marcadores = re.findall(r"\{\{([A-Z_]+)\}\}", html)
print("plantilla.html escrita:", len(html), "bytes")
print("marcadores:", ", ".join(marcadores))
