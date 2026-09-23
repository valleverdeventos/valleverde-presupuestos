"""Arma un presupuesto solo, a partir de un pedido, sin sesión de Claude.

    python sistema/auto.py pedido.json

Lo corre la GitHub Action `presupuesto-auto.yml` cuando Make despacha un
`repository_dispatch` con el pedido en `client_payload`. También se puede
correr a mano para probar.

Hace tres cosas:
1. Calcula los valores con `calcular_precio.py` (el mismo motor de /presu).
2. Escribe `sistema/datos/<slug>.json` con las reglas fijas de /presu.
3. Escribe `sistema/pedidos/<slug>.json` con el pedido original, el link y el
   mensaje para el cliente. Es lo que lee el escenario 2 de Make para mandar el
   link al aprobar, y lo que modifica para volver a despachar al ajustar.

Imprime el slug por stdout. El render y la publicación los hace la Action.

Formato del pedido (todo lo que no es obligatorio puede faltar o venir null):

{
  "tipo": "cumple_15",            obligatorio: cumple_15 | cumpleanos | casamiento |
                                   empresarial | recibida | otro
  "titulo": "Cumpleaños 50 años",  opcional, pisa el título que sale del tipo
  "edad": 50,                      opcional, sólo para cumpleanos
  "cliente": "Juan Pérez",         opcional
  "telefono": "2915123456",        opcional, se usa sólo si no hay cliente
  "fecha": "2026-12-12",           obligatorio, AAAA-MM-DD o AAAA-MM
  "horario": "21:00 a 03:00",      opcional (default 21:00 a 03:00)
  "invitados": 90,                 obligatorio salvo que vengan los desgloses
  "adultos": 30,                   en cumple de 15 son obligatorios adultos
  "adolescentes": 60,              y adolescentes
  "ninos": 0,                      menores de 12, en cualquier evento
  "catering": "si",                si | no | no_dice (no_dice = van las opciones)
  "bebida_mesa": false,            true sólo si el cliente pide que la ponga el salón
  "precios": {"salon": 15000},     opcional: precio por persona fijado a mano por Gian,
                                   pisa la tabla (claves: salon, barra, barra_teen, ninos,
                                   pizza, finger, postres, bebida; null = el de la tabla)
  "conversationId": "...",         de Zernio; sin él el link se lo manda Gian
  "slug": "..."                    sólo al ajustar: reescribe ese presupuesto
}
"""
import datetime
import json
import pathlib
import re
import sys
import unicodedata

SISTEMA = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(SISTEMA))
from calcular_precio import BARRA_ADULTOS_FIJO, calcular  # noqa: E402

DATOS = SISTEMA / "datos"
PEDIDOS = SISTEMA / "pedidos"
PAGES = "https://valleverdeventos.github.io/valleverde-presupuestos/presupuestos/"
HORARIO_DEFAULT = "21:00 a 03:00"
BLOQUE_BASE_HORAS = 6
FACTOR_BARRA_TEEN = 0.7

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
         "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

TERMINOS = [
    "Seña 35%: con la reserva del salón.",
    "Saldo 65%: 20 días antes del evento.",
    "Cancelaciones no reintegran la seña.",
    "Valores expresados a valor del día de la fecha de emisión de este presupuesto. "
    "Se actualizarán según inflación oficial (INDEC) entre la emisión y la fecha del evento.",
]

# Textos fijos de /presu. El de "sin catering" es el exacto confirmado por Gian
# el 02/08/2026; no reformular.
AVISO_SIN_CATERING = (
    "Esta propuesta corresponde a nuestra opción base \"Salón + Barra de tragos\" para el "
    "total de invitados. El catering puede estar a cargo del cliente; si están interesados, "
    "les enviamos aparte el presupuesto actualizado con nuestro catering (finger food, "
    "degustación de pizzas, mesa de postres, bebida de mesa) a elección."
)
AVISO_CON_CATERING = (
    "Esta propuesta contempla dos opciones de catering (Degustación de Pizzas y Finger Food) "
    "a modo de referencia de valores. El presupuesto final se ajusta según los servicios que "
    "efectivamente se elijan, manteniendo siempre nuestra opción base \"Salón + Barra de "
    "tragos\". Ambas opciones incluyen mesa de postres."
)
AVISO_SALON = "El servicio de salón incluye personal completo y DJ."

# Formato recibida: paquete cerrado de /presu (13/09/2026), no usa el motor.
RECIBIDA_SALON = 38000
RECIBIDA_MINIMO = "Valor mínimo de contratación: $1.750.000."
RECIBIDA_AVISO = (
    "Propuesta pensada para fiestas de recibida. El salón se entrega con personal de "
    "servicio, sonido y uso de cocina; la comida y la bebida quedan a cargo de ustedes. "
    "Disponible los días viernes."
)
RECIBIDA_NOTA = (
    "Adicionales a elección: degustación de pizzas, $14.000 por invitado. La barra de "
    "tragos también puede sumarse; si les interesa, les pasamos el valor aparte. La mesa "
    "de postres y las bebidas quedan a cargo del cliente."
)


class PedidoInvalido(ValueError):
    pass


def slugificar(texto):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")


def pesos(n):
    return "$" + f"{int(round(n)):,}".replace(",", ".")


def hoy_argentina():
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)).date()


def entero(p, clave):
    v = p.get(clave)
    if v in (None, ""):
        return 0
    try:
        return int(v)
    except (TypeError, ValueError):
        raise PedidoInvalido(f"'{clave}' tiene que ser un número: {v!r}")


def leer_fecha(texto):
    """Devuelve (fecha para mostrar, fecha para el slug, date o None)."""
    texto = str(texto or "").strip()
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", texto)
    if m:
        f = datetime.date(int(m[1]), int(m[2]), int(m[3]))
        return f"{DIAS[f.weekday()]} {f:%d/%m/%Y}", texto, f
    m = re.fullmatch(r"(\d{4})-(\d{2})", texto)
    if m:
        return f"{MESES[int(m[2])]} {m[1]} (sujeto a disponibilidad)", texto, None
    raise PedidoInvalido(f"fecha inválida: {texto!r} (va AAAA-MM-DD o AAAA-MM)")


def horas_extra(horario):
    m = re.fullmatch(r"\s*(\d{1,2})[:.](\d{2})\s*a\s*(\d{1,2})[:.](\d{2})\s*", horario)
    if not m:
        return 0
    ini = int(m[1]) * 60 + int(m[2])
    fin = int(m[3]) * 60 + int(m[4])
    dur = (fin - ini) % (24 * 60)
    return max(0, -(-(dur - BLOQUE_BASE_HORAS * 60) // 60))


def titulo_y_tipo(p):
    tipo = p.get("tipo") or "otro"
    edad = p.get("edad")
    base = {
        "cumple_15": ("Cumpleaños de 15", "cumpleanos-15"),
        "casamiento": ("Casamiento", "casamiento"),
        "empresarial": ("Evento empresarial", "empresarial"),
        "recibida": ("Fiesta de Recibida", "recibida"),
    }
    if tipo in base:
        titulo, tipo_slug = base[tipo]
    elif tipo == "cumpleanos":
        titulo = f"Cumpleaños {edad} años" if edad else "Cumpleaños"
        tipo_slug = f"cumpleanos-{edad}" if edad else "cumpleanos"
    elif tipo == "otro":
        titulo, tipo_slug = "Evento", "evento"
    else:
        raise PedidoInvalido(f"tipo desconocido: {tipo!r}")
    if p.get("titulo"):
        titulo = p["titulo"]
        if tipo == "otro":
            tipo_slug = slugificar(titulo)[:30] or "evento"
    return tipo, titulo, tipo_slug


def armar_slug(p, tipo_slug, fecha_slug):
    if p.get("slug"):
        return slugificar(p["slug"])
    if p.get("cliente"):
        quien = "-".join(slugificar(p["cliente"]).split("-")[:2])
        slug = f"{quien}-{tipo_slug}-{fecha_slug}"
    elif p.get("telefono"):
        slug = f"{tipo_slug}-{fecha_slug}-tel-{re.sub(r'[^0-9]', '', str(p['telefono']))[-8:]}"
    else:
        slug = f"{tipo_slug}-{fecha_slug}"
    slug = slug[:55].strip("-")  # callback_data de Telegram: 64 bytes con "ok:"
    candidato, n = slug, 2
    while (DATOS / f"{candidato}.json").exists():
        candidato, n = f"{slug}-v{n}", n + 1
    return candidato


def servicios_con_motor(tipo, adultos, adolescentes, ninos, catering, bebida, extra):
    """Corre el motor y traduce sus ítems al formato de datos de render.py.

    Devuelve (servicios, índices por clave) con cantidades explícitas.
    """
    invitados = adultos + adolescentes + ninos
    r = calcular(
        invitados=invitados, adultos=adultos, adolescentes=adolescentes, ninos=ninos,
        finger_food=catering, pizza=catering, mesa_postres=catering, bebida_mesa=bebida,
        horas_extra=extra,
    )
    items = {i["servicio"]: i for i in r["items"]}
    quince = tipo == "cumple_15"
    servicios, idx = [], {}

    def agregar(clave, nombre, precio, cantidad):
        idx[clave] = len(servicios)
        servicios.append({"nombre": nombre, "precio": precio, "cantidad": cantidad})

    # En cumple de 15 el salón va en una sola línea con el total (regla 17/08/2026).
    agregar("salon", "Salón (incluye personal completo y DJ)",
            items["Salón"]["precio_unitario"], adultos + adolescentes)
    barra = items["Barra adultos"]["precio_unitario"]
    if quince:
        agregar("barra", "Barra de tragos adultos (con alcohol)", barra, adultos)
        if adolescentes:
            # El motor no calcula la barra adolescentes: 70% de la barra vigente.
            teen = round(BARRA_ADULTOS_FIJO * (1 + extra / 6) * FACTOR_BARRA_TEEN)
            agregar("barra_teen", "Barra de tragos adolescentes (sin alcohol)", teen, adolescentes)
    else:
        agregar("barra", "Barra de tragos (con alcohol)", barra, adultos)
    if ninos:
        n = items["Niños (<12) - Tarifa 50% Salón"]
        agregar("ninos", "Salón niños (menores de 12)", n["precio_unitario"], ninos)
    for clave, nombre in [("pizza", "Degustación de Pizzas"), ("finger", "Finger Food"),
                          ("postres", "Mesa de Postres"), ("bebida", "Bebida de Mesa")]:
        if nombre in items:
            agregar(clave, nombre, items[nombre]["precio_unitario"], items[nombre]["cantidad"])
    return servicios, idx


def armar_datos(p):
    """Devuelve (slug, datos para render.py, avisos internos para Gian)."""
    tipo, titulo, tipo_slug = titulo_y_tipo(p)
    fecha_txt, fecha_slug, fecha = leer_fecha(p.get("fecha"))
    horario = p.get("horario") or HORARIO_DEFAULT
    avisos = []

    adultos, adolescentes, ninos = (entero(p, k) for k in ("adultos", "adolescentes", "ninos"))
    invitados = entero(p, "invitados")
    if tipo == "cumple_15":
        if not (adultos and adolescentes):
            raise PedidoInvalido("cumple de 15 sin adultos y adolescentes separados")
    else:
        # "Adolescentes" sólo existe en cumple de 15: el resto va como adulto.
        adultos += adolescentes
        adolescentes = 0
    if not adultos:
        adultos = invitados - ninos
    total = adultos + adolescentes + ninos
    if total <= 0:
        raise PedidoInvalido("faltan los invitados")
    if invitados and invitados != total:
        avisos.append(f"El pedido decía {invitados} invitados; el desglose suma {total} y se usó ese.")
    if total > 120:
        avisos.append(f"{total} invitados supera la capacidad de 120.")
    elif total > 90:
        avisos.append("Más de 90 invitados: los unitarios salen de la escala 90.")

    datos = {
        "emitido": hoy_argentina().strftime("%d/%m/%Y"),
        "titulo": titulo,
    }
    if p.get("cliente"):
        datos["cliente"] = str(p["cliente"]).strip()
    elif p.get("telefono"):
        datos["cliente"] = str(p["telefono"]).strip()
        datos["cliente_label"] = "Teléfono"
    datos.update({"fecha": fecha_txt, "horario": horario, "invitados": total})
    if tipo == "cumple_15":
        datos["invitados_texto"] = f"{adultos} adultos + {adolescentes} adolescentes"
    elif ninos:
        datos["invitados_texto"] = f"{adultos} adultos + {ninos} niños"

    if tipo == "recibida":
        datos.update({
            "formato": "recibida",
            "aviso": RECIBIDA_AVISO,
            "servicios": [{"nombre": "Salón (incluye personal de servicio, DJ y uso de cocina)",
                           "precio": RECIBIDA_SALON}],
            "nota": RECIBIDA_NOTA,
            "terminos": [RECIBIDA_MINIMO] + TERMINOS,
        })
        if fecha and fecha.weekday() != 4:
            avisos.append("La recibida se ofrece sólo viernes y la fecha pedida no es viernes.")
        return armar_slug(p, tipo_slug, fecha_slug), datos, avisos

    catering = (p.get("catering") or "no_dice") != "no"
    bebida = bool(p.get("bebida_mesa"))
    extra = horas_extra(horario)
    if extra:
        avisos.append(f"Horario de {BLOQUE_BASE_HORAS + extra} h: salón y barra llevan {extra} h extra.")
    if (p.get("catering") or "no_dice") == "no_dice":
        avisos.append("El cliente no dijo si quiere catering: van las opciones A y B.")

    servicios, idx = servicios_con_motor(tipo, adultos, adolescentes, ninos, catering, bebida, extra)
    # Precios que Gian fija a mano desde el bot ("poné el salón a 15.000"): pisan la tabla.
    for clave, precio in (p.get("precios") or {}).items():
        if precio and clave in idx:
            s = servicios[idx[clave]]
            avisos.append(f"{s['nombre']}: precio a mano {pesos(precio)} (tabla {pesos(s['precio'])}).")
            s["precio"] = int(precio)
    base = [idx[k] for k in ("salon", "barra", "barra_teen", "ninos") if k in idx]
    datos["servicios"] = servicios

    if catering:
        datos["aviso"] = f"{AVISO_CON_CATERING} {AVISO_SALON}"
        adicionales = [idx["postres"]] + ([idx["bebida"]] if bebida else [])
        extra_label = " y Mesa de Postres" if not bebida else ", Mesa de Postres y Bebida de Mesa"
        datos["opciones"] = [
            {"tag": "Opción Base — Salón + Barra", "label": "Total (Salón + Barra de tragos)",
             "servicios": base},
            {"tag": "Opción A — Degustación de Pizzas",
             "label": f"Total (incluye Salón, Barra, Degustación de Pizzas{extra_label})",
             "servicios": base + [idx["pizza"]] + adicionales},
            {"tag": "Opción B — Finger Food",
             "label": f"Total (incluye Salón, Barra, Finger Food{extra_label})",
             "servicios": base + [idx["finger"]] + adicionales},
        ]
    else:
        datos["aviso"] = f"{AVISO_SIN_CATERING} {AVISO_SALON}"
    datos["terminos"] = list(TERMINOS)
    return armar_slug(p, tipo_slug, fecha_slug), datos, avisos


def totales(datos):
    inv = datos["invitados"]
    s = datos["servicios"]
    sub = lambda i: s[i]["precio"] * s[i].get("cantidad", inv)  # noqa: E731
    if datos.get("formato") == "recibida":
        return [("Total salón", sub(0))]
    if datos.get("opciones"):
        return [(op["tag"], sum(sub(i) for i in op["servicios"])) for op in datos["opciones"]]
    return [("Total", sum(sub(i) for i in range(len(s))))]


def mensaje_cliente(p, datos, url, fecha):
    """Mensaje de WhatsApp de /presu 5b, con la firma obligatoria."""
    nombre = str(p.get("cliente") or "").strip().split(" ")[0].capitalize()
    saludo = f"Hola {nombre}!" if nombre else "Hola!"
    if fecha:
        cuando = f"del {fecha:%d/%m}"
    else:
        cuando = "de " + datos["fecha"].split(" ")[0].lower()
    detalle = ("Ahí tenés las opciones de catering con sus valores y las condiciones."
               if datos.get("opciones") else
               "Ahí tenés el detalle de servicios, valores y condiciones.")
    return (f"{saludo} Acá va la propuesta para tu evento {cuando}, armada con lo que nos "
            f"comentaste.\n\n{url}\n\n{detalle} La fecha se reserva con la seña.\n\n"
            "Cualquier consulta o ajuste que necesiten, escribinos.\n\nGracias y saludos,\nGian")


def procesar(p):
    slug, datos, avisos = armar_datos(p)
    url = f"{PAGES}{slug}/"
    _, _, fecha = leer_fecha(p.get("fecha"))
    DATOS.mkdir(exist_ok=True)
    PEDIDOS.mkdir(exist_ok=True)
    (DATOS / f"{slug}.json").write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    registro = {
        "slug": slug,
        "url": url,
        "conversationId": p.get("conversationId"),
        "mensaje_cliente": mensaje_cliente(p, datos, url, fecha),
        "totales": [[k, v] for k, v in totales(datos)],
        "avisos": avisos,
        "pedido": {k: v for k, v in p.items() if k != "slug"},
    }
    (PEDIDOS / f"{slug}.json").write_text(
        json.dumps(registro, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return registro


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    pedido = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
    try:
        registro = procesar(pedido)
    except PedidoInvalido as e:
        print(f"Pedido inválido: {e}", file=sys.stderr)
        return 2
    print(registro["slug"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
