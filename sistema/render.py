"""Arma el index.html de un presupuesto a partir de su archivo de datos.

    python sistema/render.py mariana-cumpleanos-40-2026-09-26
    python sistema/render.py --todos

Lee  sistema/datos/<slug>.json
Usa  sistema/plantilla.html
Deja presupuestos/<slug>/index.html
"""
import datetime
import json
import pathlib
import sys

SISTEMA = pathlib.Path(__file__).resolve().parent
RAIZ = SISTEMA.parent
DATOS = SISTEMA / "datos"
PLANTILLA = SISTEMA / "plantilla.html"

# Colores de etiqueta ya calibrados: base, catering mas barato, catering mas caro.
COLORES = ["#8E0E3E", "#2F6690", ""]

# Bloque "Recepcion" de la Opcion A (Degustacion de pizzas). Por default se
# muestra igual que siempre; un presupuesto puntual puede pedir omitirlo con
# "pizza_sin_recepcion": true en su JSON, sin afectar a ningun otro cliente.
PIZZA_RECEPCION_HTML = """        <div class="subtitulo-menu">Recepción</div>
        <ul class="lista">
          <li>Variedad de canastitas, pionono y chips</li>
          <li>Bocaditos de pollo en salsa de crema y verdeo</li>
        </ul>
"""


def fecha_emision(d):
    """Fecha desde la cual corre el ajuste por inflacion.

    Se toma de "emitido" en el JSON; si no esta, es la fecha de hoy y queda
    congelada en el archivo la primera vez que se renderiza, para que un
    re-render mas adelante no corra la fecha hacia adelante.
    """
    if d.get("emitido"):
        return d["emitido"]
    return datetime.date.today().strftime("%d/%m/%Y")


def pesos(n):
    """1310000 -> $1.310.000"""
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def total_de(servicio, invitados):
    return servicio["precio"] * servicio.get("cantidad", invitados)


def bloque_datos(d):
    """Grilla de portada. Sin nombre de cliente va a 3 columnas."""
    campos = []
    if d.get("cliente"):
        campos.append((d.get("cliente_label", "Cliente"), d["cliente"]))
    campos.append(("Fecha", d["fecha"]))
    campos.append(("Horario", d["horario"]))
    campos.append(("Invitados", d.get("invitados_texto", d["invitados"])))
    campos.append(("Emitido", fecha_emision(d)))

    # 5 campos (con cliente) llevan clase propia; 4 usan el default de la
    # plantilla, que ya son 2 columnas en móvil y 4 en escritorio.
    clase = " cols-5" if len(campos) == 5 else ""
    filas = [
        f'        <div class="dato"><span class="label">{k}</span>{v}</div>'
        for k, v in campos
    ]
    return (f'<div class="datos-grid{clase}">\n' + "\n".join(filas) + "\n      </div>")


def tarjeta(servicio, invitados):
    cantidad = servicio.get("cantidad", invitados)
    return f"""      <div class="precio-card">
        <div class="precio-servicio">{servicio['nombre']}</div>
        <div class="precio-datos">
          <div class="precio-dato"><span class="label">Cantidad</span><span class="valor">{cantidad}</span></div>
          <div class="precio-dato"><span class="label">Precio unit.</span><span class="valor">{pesos(servicio['precio'])}</span></div>
          <div class="precio-dato total"><span class="label">Total</span><span class="valor">{pesos(total_de(servicio, invitados))}</span></div>
        </div>
      </div>"""


def bloque_precios(d):
    invitados = d["invitados"]
    servicios = d["servicios"]
    partes = ['    <div id="tabla-precios">']
    partes += [tarjeta(s, invitados) for s in servicios]

    opciones = d.get("opciones") or []
    if not opciones:
        total = sum(total_de(s, invitados) for s in servicios)
        partes.append(f"""      <div class="total-final">
        <span class="label">Total</span>
        <span class="valor">{pesos(total)}</span>
      </div>""")
    elif all(op.get("simple") for op in opciones):
        # Forma vieja: totales sueltos, uno debajo del otro, sin etiqueta.
        for op in opciones:
            total = sum(total_de(servicios[j], invitados) for j in op["servicios"])
            color = op.get("color", "")
            attr = f' style="border-top-color:{color};"' if color else ""
            valor = f'<span class="valor" style="color:{color};">' if color else '<span class="valor">'
            partes.append(f"""      <div class="total-final"{attr}>
        <span class="label">{op['label']}</span>
        {valor}{pesos(total)}</span>
      </div>""")
    else:
        partes.append('      <div class="total-opciones">')
        for i, op in enumerate(opciones):
            total = sum(total_de(servicios[j], invitados) for j in op["servicios"])
            color = op.get("color", COLORES[i] if i < len(COLORES) else "")
            tag = f'<span class="tag" style="background:{color}; color:#F7F1E6;">' if color else '<span class="tag">'
            partes.append(f"""        <div class="total-opcion">
          {tag}{op['tag']}</span>
          <div class="total-final">
            <span class="label">{op['label']}</span>
            <span class="valor">{pesos(total)}</span>
          </div>
        </div>""")
        partes.append("      </div>")

    partes.append("    </div>")
    if d.get("nota"):
        partes.append(f'    <p class="nota" style="margin-top:14px;">{d["nota"]}</p>')
    return "\n".join(partes)


# La clausula de inflacion se reescribe con la fecha de emision concreta, para
# que quede escrito desde que dia corre el ajuste. Se reconoce por el arranque
# del texto, asi los JSON viejos no hay que tocarlos.
CLAUSULA_VIEJA = "Valores expresados a valor del día de la fecha de emisión de este presupuesto."
CLAUSULA_NUEVA = ("Valores expresados al {fecha}, fecha de emisión de este presupuesto. "
                  "Se actualizarán según inflación oficial (INDEC) entre esa fecha "
                  "y la fecha del evento.")


def bloque_terminos(d):
    terminos = [
        CLAUSULA_NUEVA.format(fecha=fecha_emision(d))
        if t.startswith(CLAUSULA_VIEJA) else t
        for t in (d.get("terminos") or [])
    ]
    filas = []
    for i, t in enumerate(terminos):
        ultimo = ' style="margin-bottom:0;"' if i == len(terminos) - 1 else ""
        filas.append(f'    <div class="feature"{ultimo}><span class="tri"></span><p>{t}</p></div>')
    return "\n".join(filas)


def render(slug):
    d = json.loads((DATOS / f"{slug}.json").read_text(encoding="utf-8"))
    html = PLANTILLA.read_text(encoding="utf-8")

    # Regla fija de Gian (02/08/2026): toda nota que aclare a que corresponde el
    # valor va en .aviso-valores. .aviso-catering solo sobrevive en las paginas
    # viejas que ya lo tenian, y solo si el JSON lo pide explicitamente.
    clase = d.get("aviso_clase") or "aviso-valores"
    reemplazos = {
        "TITULO": d["titulo"],
        "DATOS_GRID": bloque_datos(d),
        "AVISO": f'<div class="{clase}">{d["aviso"]}</div>' if d.get("aviso") else "",
        "TABLA_PRECIOS": bloque_precios(d).lstrip(),
        "TERMINOS": bloque_terminos(d).lstrip(),
        "PIZZA_RECEPCION": "" if d.get("pizza_sin_recepcion") else PIZZA_RECEPCION_HTML,
    }
    for k, v in reemplazos.items():
        html = html.replace("{{%s}}" % k, str(v))

    destino = RAIZ / "presupuestos" / slug
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "index.html").write_text(html, encoding="utf-8")
    return destino / "index.html"


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return 1
    slugs = sorted(p.stem for p in DATOS.glob("*.json")) if args[0] == "--todos" else args
    for slug in slugs:
        render(slug)
    print(f"{len(slugs)} presupuesto(s) generado(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
