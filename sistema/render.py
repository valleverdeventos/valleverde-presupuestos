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


# ---------------------------------------------------------------------------
# Formato "recibida": propuesta economica para fiestas de egresados. El salon va
# pelado, la comida y la bebida las trae el cliente, y el unico catering que se
# ofrece es la degustacion de pizzas recortada a 5 gustos y sin recepcion.
# Se activa con "formato": "recibida" en el JSON del presupuesto.

PIZZAS_RECIBIDA = """        <div class="subtitulo-menu">Principal — 5 variedades</div>
        <ul class="lista">
          <li>Margherita — mozzarella, tomate, albahaca</li>
          <li>Muzza y Roquefort — mozzarella y queso azul</li>
          <li>Muzza y Mix de Tomates — mozzarella, tomates confitados y cherry</li>
          <li>Calabresa — mozzarella y longaniza</li>
          <li>Salchicha y Cebolla — mozzarella, salchicha y cebolla salteada</li>
        </ul>"""

# En una recibida la barra no viene incluida ni lleva precio en el documento,
# pero conviene que se vea: es el adicional que mas margen deja. Por eso en vez
# de una linea de texto va un cartel grande, calcando el recuadro de la portada.
BARRA_OPCIONAL = """No incluida en esta propuesta.</p>

    <div style="margin:22px 0 6px; padding:30px 22px; border:2px solid var(--accent); border-radius:3px; background:rgba(232,121,43,0.12); text-align:center;">
      <div style="font:700 11px/1.3 'Poppins',sans-serif; letter-spacing:2px; text-transform:uppercase; color:var(--accent); margin-bottom:10px;">Servicio opcional</div>
      <div style="font:300 32px/1.15 'Poppins',sans-serif; color:var(--accent); letter-spacing:0.5px;">Consultanos por nuestra<br><b style="font-weight:700;">Opción Barra</b></div>
      <div style="width:40px; height:2px; background:var(--accent); margin:16px auto;"></div>
      <div style="font:400 14px/1.5 'Poppins',sans-serif; color:var(--accent);">Barra completa con barman y tragos preparados en el momento.<br>Te pasamos el valor para tu cantidad de invitados.</div>
    </div>

    <p style="display:none;">"""


def quitar_seccion(html, etiqueta):
    """Saca del HTML la <section> con ese data-screen-label."""
    marca = 'data-screen-label="%s"' % etiqueta
    pos = html.find(marca)
    if pos == -1:
        return html
    ini = html.rfind("<section", 0, pos)
    fin = html.find("</section>", pos)
    if ini == -1 or fin == -1:
        return html
    return html[:ini] + html[fin + len("</section>"):]


def aplicar_formato_recibida(html):
    """Recorta la propuesta gastronomica a lo que entra en una recibida."""
    # Fuera la pagina entera de Finger Food.
    html = quitar_seccion(html, "05")

    # La degustacion de pizzas queda en 5 gustos, sin recepcion.
    ini = html.find('<div class="subtitulo-menu">Principal — 6 variedades a elección</div>')
    if ini != -1:
        fin = html.find("</ul>", ini)
        if fin != -1:
            html = html[:ini] + PIZZAS_RECIBIDA + html[fin + len("</ul>"):]

    # La barra se muestra, pero marcada como opcional y a cotizar aparte.
    html = html.replace(
        "Incluida en el servicio base, con opción adicional de barra sin alcohol "
        "para adolescentes.", BARRA_OPCIONAL)

    return html


def aplicar_barra_propia(html, tragos):
    """Reemplaza la carta de la pagina 07 por los tragos pactados para este evento.

    Se activa con "barra_tragos" en el JSON: lista de {"nombre", "chips"}.
    Saca tambien la barra de adolescentes, que no aplica a una barra acotada.
    """
    ini = html.find('<div class="barra-bloque">')
    fin = html.find('<p class="nota">Tragos preparados en el momento')
    if ini == -1 or fin == -1:
        return html
    tiles = []
    for t in tragos:
        chips = t.get("chips", [])
        chip_html = "".join(
            f'<span class="chip{" chip-accent" if i == 0 else ""}">{c}</span>'
            for i, c in enumerate(chips))
        tiles.append(f'        <div class="barra-tile"><div class="name">{t["nombre"]}</div>'
                     f'<div class="chip-row">{chip_html}</div></div>')
    bloque = (
        '<div class="barra-bloque" style="margin-bottom:10px;">\n'
        '      <div class="barra-head">\n'
        '        <span class="num">01</span>\n'
        '        <span class="label">Barra para adultos</span>\n'
        '        <span class="sub">— con alcohol</span>\n'
        '      </div>\n'
        '      <div class="barra-grid">\n'
        + "\n".join(tiles) + "\n"
        '      </div>\n'
        '    </div>\n\n    ')
    html = html[:ini] + bloque + html[fin:]
    return html.replace(
        "Incluida en el servicio base, con opción adicional de barra sin alcohol "
        "para adolescentes.", "Incluida en el servicio base.")


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
    if d.get("formato") == "recibida":
        # En una recibida cada servicio se muestra con su propio total y no se
        # arma una suma general: el cliente elige si suma las pizzas o no.
        pass
    elif not opciones:
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
        "PIZZA_RECEPCION": "" if (d.get("pizza_sin_recepcion")
                                or d.get("formato") == "recibida")
                             else PIZZA_RECEPCION_HTML,
    }
    for k, v in reemplazos.items():
        html = html.replace("{{%s}}" % k, str(v))

    if d.get("formato") == "recibida":
        html = aplicar_formato_recibida(html)
    if d.get("barra_tragos"):
        html = aplicar_barra_propia(html, d["barra_tragos"])

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
