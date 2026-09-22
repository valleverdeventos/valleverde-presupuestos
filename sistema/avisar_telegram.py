"""Manda a Gian, por el bot de presupuestos, el presupuesto armado por auto.py.

    python sistema/avisar_telegram.py <slug> [--url URL]
    python sistema/avisar_telegram.py --error <archivo con el error> [pedido.json]

Lee `sistema/pedidos/<slug>.json`. Con `--url` cambia el link (por ejemplo al
espejo de Cloudflare si Pages no respondió) y lo reescribe en el registro y en
el mensaje para el cliente.

Botones: "Aprobar y enviar" (sólo si el pedido vino de un WhatsApp, callback
`ok:<slug>`), "Ajustar" (callback `aj:<slug>`) y "Ver presupuesto" (link).
Los callbacks los atiende el escenario 2 de Make.

Necesita TELEGRAM_PRESUPUESTOS_TOKEN y TELEGRAM_PRESUPUESTOS_CHAT_ID en el entorno.
"""
import html
import json
import os
import pathlib
import sys
import urllib.request

SISTEMA = pathlib.Path(__file__).resolve().parent
PEDIDOS = SISTEMA / "pedidos"


def pesos(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def enviar(texto, botones=None):
    token = os.environ["TELEGRAM_PRESUPUESTOS_TOKEN"]
    cuerpo = {
        "chat_id": os.environ["TELEGRAM_PRESUPUESTOS_CHAT_ID"],
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    if botones:
        cuerpo["reply_markup"] = {"inline_keyboard": botones}
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps(cuerpo).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def avisar_presupuesto(slug, url=None):
    archivo = PEDIDOS / f"{slug}.json"
    reg = json.loads(archivo.read_text(encoding="utf-8"))
    if url and url != reg["url"]:
        reg["mensaje_cliente"] = reg["mensaje_cliente"].replace(reg["url"], url)
        reg["url"] = url
        archivo.write_text(json.dumps(reg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    p = reg["pedido"]
    e = html.escape
    quien = p.get("cliente") or p.get("telefono") or "sin nombre"
    lineas = [f"🧾 <b>Presupuesto listo — {e(str(quien))}</b>", ""]
    lineas += [f"{e(k)}: <b>{pesos(v)}</b>" for k, v in reg["totales"]]
    if reg["avisos"]:
        lineas += [""] + [f"• {e(a)}" for a in reg["avisos"]]
    if not reg.get("conversationId"):
        lineas += ["", "No vino de un WhatsApp: el link lo mandás vos."]
    lineas += ["", e(reg["url"]), "", "Mensaje para el cliente:",
               f"<pre>{e(reg['mensaje_cliente'])}</pre>"]

    fila = []
    if reg.get("conversationId"):
        fila.append({"text": "✅ Aprobar y enviar", "callback_data": f"ok:{slug}"})
    fila.append({"text": "✏️ Ajustar", "callback_data": f"aj:{slug}"})
    enviar("\n".join(lineas), [fila, [{"text": "Ver presupuesto", "url": reg["url"]}]])


def avisar_error(archivo_error, archivo_pedido=None):
    error = pathlib.Path(archivo_error).read_text(encoding="utf-8", errors="replace").strip() or "error sin detalle"
    texto = f"⚠️ <b>No se pudo armar el presupuesto automático</b>\n\n{html.escape(error[-1500:])}"
    if archivo_pedido and pathlib.Path(archivo_pedido).exists():
        pedido = pathlib.Path(archivo_pedido).read_text(encoding="utf-8")
        texto += f"\n\nPedido:\n<pre>{html.escape(pedido[:1500])}</pre>"
    enviar(texto)


def main():
    args = sys.argv[1:]
    if args[:1] == ["--error"] and len(args) >= 2:
        avisar_error(*args[1:3])
    elif args and not args[0].startswith("--"):
        url = args[args.index("--url") + 1] if "--url" in args else None
        avisar_presupuesto(args[0], url)
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
