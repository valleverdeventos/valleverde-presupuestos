"""Extrae los datos de las paginas ya publicadas hacia sistema/datos/*.json.

Se corre una sola vez, para migrar al formato nuevo lo que ya estaba hecho a mano.

    python sistema/extraer.py
"""
import html as htmlmod
import itertools
import json
import pathlib
import re

SISTEMA = pathlib.Path(__file__).resolve().parent
RAIZ = SISTEMA.parent
DATOS = SISTEMA / "datos"
DATOS.mkdir(exist_ok=True)


def limpiar(s):
    return htmlmod.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def numero(s):
    return int(re.sub(r"[^\d]", "", s))


def dato(html, campo):
    m = re.search(r'<span class="label">%s</span>([^<]*)</div>' % campo, html)
    return limpiar(m.group(1)) if m else ""


def subconjunto(totales, objetivo):
    """Indices de servicios cuya suma de totales da el objetivo, o None."""
    for r in range(1, len(totales) + 1):
        for combo in itertools.combinations(range(len(totales)), r):
            if abs(sum(totales[i] for i in combo) - objetivo) < 1:
                return list(combo)
    return None


def extraer(ruta):
    html = ruta.read_text(encoding="utf-8", errors="replace")
    d = {}

    m = re.search(r'<h1 style="margin-bottom:4px;">(.*?)</h1>', html, re.S)
    d["titulo"] = limpiar(m.group(1)) if m else ""
    d["cliente"] = dato(html, "Cliente")
    d["fecha"] = dato(html, "Fecha")
    d["horario"] = dato(html, "Horario")
    inv = dato(html, "Invitados")
    d["invitados"] = numero(inv) if re.search(r"\d", inv) else 0

    m = re.search(r'<div class="aviso-(catering|valores)">(.*?)</div>', html, re.S)
    d["aviso_clase"] = "aviso-" + m.group(1) if m else "aviso-valores"
    d["aviso"] = m.group(2).strip() if m else ""

    # --- servicios ---
    servicios = []
    for card in re.findall(r'<div class="precio-card">(.*?)</div>\s*</div>', html, re.S):
        n = re.search(r'<div class="precio-servicio">(.*?)</div>', card, re.S)
        p = re.search(r'Precio unit\.</span><span class="valor">([^<]*)</span>', card)
        q = re.search(r'Cantidad</span><span class="valor">([^<]*)</span>', card)
        if n and p:
            s = {"nombre": limpiar(n.group(1)), "precio": numero(p.group(1))}
            if q and re.search(r"\d", q.group(1)):
                s["cantidad"] = numero(q.group(1))
            servicios.append(s)
    d["servicios"] = servicios

    inv_n = d["invitados"] or 1
    totales = [s["precio"] * s.get("cantidad", inv_n) for s in servicios]

    # --- opciones ---
    # Forma nueva: cada opcion envuelta en .total-opcion con su etiqueta de color.
    con_tag = re.findall(
        r'<span class="tag"(?:\s+style="background:([^;"]*)[^"]*")?\s*>(.*?)</span>\s*'
        r'<div class="total-final">\s*<span class="label">(.*?)</span>\s*'
        r'<span class="valor">([^<]*)</span>',
        html, re.S,
    )
    ops, revisar = [], False
    if con_tag:
        for color, tag, label, valor in con_tag:
            idx = subconjunto(totales, numero(valor))
            revisar = revisar or idx is None
            ops.append({
                "tag": limpiar(tag),
                "color": color.strip(),
                "label": limpiar(label),
                "servicios": idx if idx is not None else list(range(len(totales))),
            })
    else:
        # Forma vieja: varios .total-final sueltos, sin etiqueta.
        sueltos = re.findall(
            r'<div class="total-final"([^>]*)>\s*<span class="label">(.*?)</span>\s*'
            r'<span class="valor"[^>]*>([^<]*)</span>',
            html, re.S,
        )
        if len(sueltos) > 1:
            for attrs, label, valor in sueltos:
                c = re.search(r"border-top-color:\s*([^;\"]+)", attrs)
                idx = subconjunto(totales, numero(valor))
                revisar = revisar or idx is None
                ops.append({
                    "label": limpiar(label),
                    "color": c.group(1).strip() if c else "",
                    "simple": True,
                    "servicios": idx if idx is not None else list(range(len(totales))),
                })

    if ops:
        d["opciones"] = ops
    if revisar:
        d["_revisar"] = "no se pudo reconstruir que servicios entran en cada total"

    # --- nota al pie de la tabla ---
    m = re.search(r'<p class="nota"([^>]*)>(.*?)</p>', html, re.S)
    if m:
        d["nota"] = limpiar(m.group(2))

    # --- terminos y condiciones ---
    m = re.search(
        r'>Términos y condiciones</div>(.*?)(?:</div>\s*</section>|<div class="eyebrow")',
        html, re.S,
    )
    d["terminos"] = [limpiar(x) for x in re.findall(r"<p>(.*?)</p>", m.group(1), re.S)] if m else []

    return d


def main():
    ok = revisar = 0
    for carpeta in sorted((RAIZ / "presupuestos").iterdir()):
        f = carpeta / "index.html"
        if not f.is_file() or carpeta.name == "recursos-visuales":
            continue
        d = extraer(f)
        if not d["servicios"]:
            print("  SIN PRECIOS:", carpeta.name)
            continue
        if "_revisar" in d:
            print("  REVISAR:", carpeta.name)
            revisar += 1
        (DATOS / f"{carpeta.name}.json").write_text(
            json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        ok += 1
    print(f"\n{ok} archivos de datos escritos, {revisar} para revisar.")


if __name__ == "__main__":
    main()
