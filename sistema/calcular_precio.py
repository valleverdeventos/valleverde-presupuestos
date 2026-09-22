#!/usr/bin/env python3
"""
Motor de calculo de precios VALLEVERDE Eventos.
Replica exacta (misma logica, mismos numeros) del archivo Excel
Motor_Calculo_Valleverde_v2.xlsx (hojas BASE / INPUT / CALC / OUTPUT),
calibrado con el caso real de Manuel (50 invitados -> total $4.413.887).

Uso:
    python3 calcular_precio.py --invitados 50 --finger --barra --salon
    python3 calcular_precio.py --json inputs.json

Tambien se puede importar y usar la funcion calcular(**kwargs).
"""
import argparse
import json
import sys

# ---------------------------------------------------------------------------
# Tabla BASE (precio por invitado segun escala de invitados), tal cual la
# hoja BASE del Excel. NO modificar estos numeros sin recalibrar contra
# un presupuesto real ya confirmado por Gian.
# ---------------------------------------------------------------------------
BASE = {
    20: {"salon": 51696, "barra": 39459, "finger": 29434, "pizza": 19941, "postre": 15706, "bebida": 13500},
    30: {"salon": 39388, "barra": 29813, "finger": 29434, "pizza": 19941, "postre": 15706, "bebida": 13500},
    40: {"salon": 30772, "barra": 20606, "finger": 28256, "pizza": 18802, "postre": 15706, "bebida": 13500},
    50: {"salon": 27079, "barra": 18414, "finger": 27079, "pizza": 17662, "postre": 15706, "bebida": 13500},
    60: {"salon": 24617, "barra": 17537, "finger": 25902, "pizza": 16523, "postre": 15706, "bebida": 13500},
    70: {"salon": 23386, "barra": 16222, "finger": 25000, "pizza": 15383, "postre": 15706, "bebida": 13500},
    80: {"salon": 22771, "barra": 15564, "finger": 25000, "pizza": 14814, "postre": 15706, "bebida": 13500},
    90: {"salon": 22156, "barra": 14907, "finger": 25000, "pizza": 14244, "postre": 15706, "bebida": 13500},
}

# La barra de tragos (adultos) ya NO se busca en la tabla BASE por escala de
# invitados: es un valor FIJO por persona, independiente de la cantidad de
# invitados. La columna "barra" de BASE queda sin uso para este calculo (se
# deja documentada por si se vuelve a pedir escalonarla en el futuro).
#
# Historial del valor:
#   11/07/2026 -> 19500
#   03/08/2026 -> 21500  (vigente)
BARRA_ADULTOS_FIJO = 21500

# Pisos por persona (fijados por Gian el 17/09/2026). El salon y la degustacion
# de pizzas nunca bajan de estos valores; en escalas chicas, donde la tabla ya
# da mas, se mantiene el valor de la tabla.
SALON_PISO = 29000
# Sin catering salado (ni finger food ni pizzas) el piso del salon sube (17/09/2026).
SALON_PISO_SIN_CATERING = 33000
PIZZA_PISO = 18500

# Finger food: desde la escala 70 va fijo a $25.000 por persona (22/09/2026).
# Antes: 70 -> 24724, 80 -> 23547, 90 -> 22370.


def _escala(invitados: int) -> int:
    """CALC!B3 : IF(B2>=40, MAX(40, MIN(90, INT((B2+2)/10)*10)), IF(B2>=30, 30, 20))"""
    if invitados >= 40:
        return max(40, min(90, int((invitados + 2) / 10) * 10))
    elif invitados >= 30:
        return 30
    else:
        return 20


def _factor_ajuste(invitados: int) -> float:
    """CALC!B4 : IF(B2>=40, 1, IF(B2>=30, 1.15, 1.25))"""
    if invitados >= 40:
        return 1.0
    elif invitados >= 30:
        return 1.15
    else:
        return 1.25


def calcular(
    invitados: int,
    adultos: int = None,
    adolescentes: int = 0,
    ninos: int = 0,
    solo_salon: bool = False,
    finger_food: bool = False,
    pizza: bool = False,
    mesa_postres: bool = False,
    bebida_mesa: bool = False,
    horas_extra: int = 0,
    factor_teen_salon: float = 1.0,
    factor_teen_barra: float = 0.7,
    teen_con_barra: bool = False,
    ajuste_general_pct: float = 0.0,
):
    """
    Reproduce la hoja OUTPUT del Excel. Devuelve un dict con:
      - invitados_reales
      - items: lista de {servicio, precio_unitario, cantidad, total}
      - total_final

    Notas de negocio (para no perder el criterio original):
    - "invitados" es el numero total de invitados que se usa para buscar el
      precio unitario en la tabla BASE (segun la escala de invitados).
    - "adultos" son los invitados que efectivamente pagan salon/barra a tarifa
      completa. Si no se especifica, se asume igual a `invitados`.
    - Los adolescentes pagan salon a `factor_teen_salon` (default 1.0 = igual
      que un adulto) y, si `teen_con_barra` es True y no es "solo salon",
      pagan ademas barra a `factor_teen_barra` (default 0.7).
    - Los ninos (<12) pagan 50% del valor de salon (ajustado), no pagan barra,
      y no se contemplan como parte del catering (finger/pizza) salvo que
      Gian indique lo contrario para un evento puntual.
    - El catering (finger food, pizza, mesa de postres, bebida de mesa) se
      cobra por la cantidad de "invitados reales" (adultos + adolescentes +
      ninos*0.5, redondeado), NO por invitados totales de la escala.
    """
    if adultos is None:
        adultos = invitados

    escala = _escala(invitados)
    factor_ajuste = _factor_ajuste(invitados)
    equiv_catering = round(adultos + adolescentes + (ninos * 0.5))

    base = BASE[escala]

    piso_salon = SALON_PISO if (finger_food or pizza) else SALON_PISO_SIN_CATERING
    salon_ajustado = max(base["salon"] * factor_ajuste, piso_salon)
    barra_ajustado = BARRA_ADULTOS_FIJO

    salon_c_horas = round(salon_ajustado * (1 + (horas_extra / 6)))
    barra_c_horas = round(barra_ajustado * (1 + (horas_extra / 6)))

    salon_teen_pp = round(salon_c_horas * factor_teen_salon)
    barra_teen_pp = round(barra_c_horas * factor_teen_barra)

    factor_general = 1 + ajuste_general_pct

    items = []

    # Salon (adultos)
    precio_salon = round(salon_c_horas * factor_general)
    items.append({"servicio": "Salón", "precio_unitario": precio_salon, "cantidad": adultos,
                   "total": round(precio_salon * adultos)})

    # Salon (adolescentes)
    if adolescentes > 0:
        precio_salon_teen = round(salon_teen_pp * factor_general)
        items.append({"servicio": "Salón (Adolescentes)", "precio_unitario": precio_salon_teen,
                       "cantidad": adolescentes, "total": round(precio_salon_teen * adolescentes)})

    # Barra adultos
    if not solo_salon:
        precio_barra = round(barra_c_horas * factor_general)
        items.append({"servicio": "Barra adultos", "precio_unitario": precio_barra, "cantidad": adultos,
                       "total": round(precio_barra * adultos)})

    # Barra adolescentes
    if adolescentes > 0 and teen_con_barra and not solo_salon:
        precio_barra_teen = round(barra_teen_pp * factor_general)
        items.append({"servicio": "Barra adolescentes", "precio_unitario": precio_barra_teen,
                       "cantidad": adolescentes, "total": round(precio_barra_teen * adolescentes)})

    # Catering
    if finger_food:
        pu = round(base["finger"] * factor_general)
        items.append({"servicio": "Finger Food", "precio_unitario": pu, "cantidad": equiv_catering,
                      "total": round(pu * equiv_catering)})
    if pizza:
        pu = round(max(base["pizza"], PIZZA_PISO) * factor_general)
        items.append({"servicio": "Degustación de Pizzas", "precio_unitario": pu, "cantidad": equiv_catering,
                      "total": round(pu * equiv_catering)})
    if mesa_postres:
        pu = round(base["postre"] * factor_general)
        items.append({"servicio": "Mesa de Postres", "precio_unitario": pu, "cantidad": equiv_catering,
                      "total": round(pu * equiv_catering)})
    if bebida_mesa:
        pu = round(base["bebida"] * factor_general)
        items.append({"servicio": "Bebida de Mesa", "precio_unitario": pu, "cantidad": equiv_catering,
                      "total": round(pu * equiv_catering)})

    # Ninos
    if ninos > 0:
        pu = round(salon_c_horas * 0.5)
        items.append({"servicio": "Niños (<12) - Tarifa 50% Salón", "precio_unitario": pu, "cantidad": ninos,
                      "total": round(pu * ninos)})

    total_final = sum(i["total"] for i in items)

    return {
        "invitados_reales": invitados,
        "escala_usada": escala,
        "items": items,
        "total_final": total_final,
    }


def _fmt(n):
    return f"${n:,.0f}".replace(",", ".")


def main():
    ap = argparse.ArgumentParser(description="Motor de precios VALLEVERDE Eventos")
    ap.add_argument("--json", help="Archivo JSON con los parametros de calcular()")
    ap.add_argument("--invitados", type=int)
    ap.add_argument("--adultos", type=int)
    ap.add_argument("--adolescentes", type=int, default=0)
    ap.add_argument("--ninos", type=int, default=0)
    ap.add_argument("--solo-salon", action="store_true")
    ap.add_argument("--finger", action="store_true")
    ap.add_argument("--pizza", action="store_true")
    ap.add_argument("--postres", action="store_true")
    ap.add_argument("--bebida", action="store_true")
    ap.add_argument("--horas-extra", type=int, default=0)
    ap.add_argument("--teen-con-barra", action="store_true",
                    help="Los adolescentes llevan barra sin alcohol")
    ap.add_argument("--ajuste-pct", type=float, default=0.0)
    args = ap.parse_args()

    if args.json:
        with open(args.json) as f:
            params = json.load(f)
    else:
        if args.invitados is None:
            ap.error("Falta --invitados (o usa --json)")
        params = dict(
            invitados=args.invitados,
            adultos=args.adultos,
            adolescentes=args.adolescentes,
            ninos=args.ninos,
            solo_salon=args.solo_salon,
            finger_food=args.finger,
            pizza=args.pizza,
            mesa_postres=args.postres,
            bebida_mesa=args.bebida,
            teen_con_barra=args.teen_con_barra,
            horas_extra=args.horas_extra,
            ajuste_general_pct=args.ajuste_pct,
        )

    result = calcular(**params)
    print(f"Invitados reales: {result['invitados_reales']} (escala tabla: {result['escala_usada']})\n")
    print(f"{'Servicio':<28}{'Precio unit.':>14}{'Cant.':>8}{'Total':>16}")
    for it in result["items"]:
        print(f"{it['servicio']:<28}{_fmt(it['precio_unitario']):>14}{it['cantidad']:>8}{_fmt(it['total']):>16}")
    print("-" * 66)
    print(f"{'TOTAL PRESUPUESTO':<50}{_fmt(result['total_final']):>16}")
    print()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
