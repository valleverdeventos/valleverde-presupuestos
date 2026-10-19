# "El cuaderno del 15": video completo. Cámara que recorre una hoja de diseñadora con 6 paradas.
import math, json, os, html

PAPEL = "#f6f1e7"
GRAFITO = "#2b2733"
LILA = "#6b3fc4"
ROJO = "#c9474f"
WW, WH = 4500, 7900

# caja (esquina sup. izq.) de cada parada en la hoja
A = (0, 0)
EST = [
    {"box": (1400, 200), "num": "12", "unidad": "meses antes", "img": "lista2", "tl": "12 meses",
     "t": [("Invitados", "El número elige el lugar."), ("El lugar", "Visitalo a la hora de la fiesta.")]},
    {"box": (2900, 700), "num": "10", "unidad": "meses antes", "img": "musica2", "tl": "10 meses",
     "t": [("Foto y video", "Pedí ver una fiesta entera."), ("Música", "Decile al DJ qué *NO* querés.")]},
    {"box": (2400, 2900), "num": "6", "unidad": "meses antes", "img": None, "tl": "6 meses",
     "t": [("Vestido", "1.ª prueba ya. La última, 2 semanas antes."), ("Segundo look", "Decidilo antes de cerrar el vestido.")]},
    {"box": (900, 3300), "num": "3", "unidad": "meses antes", "img": "maquillaje2", "dy": 300, "tl": "3 meses",
     "t": [("Maquillaje", "Probalo con luz de noche."), ("Invitaciones", "Con fecha límite para confirmar.")]},
    {"box": (300, 5500), "num": "2", "unidad": "meses antes", "img": "zapatos", "dy": 260, "tl": "2 meses",
     "t": [("Vals", "Ensayalo con los zapatos de la fiesta."), ("Las 15 velas", "Avisá antes a las quince personas.")]},
    {"box": (1800, 5900), "num": "2", "unidad": "semanas antes", "img": "mesas", "dy": 170, "tl": "2 semanas",
     "t": [("Mesas", "Primero, los que no pueden estar juntos."), ("Brindis", "Leelo en voz alta tres veces.")]},
]
F = (3300, 5400)
GUIA = ["12 meses · invitados y lugar", "10 meses · foto, video y música", "6 meses · vestido y segundo look",
        "3 meses · maquillaje e invitaciones", "2 meses · vals y las 15 velas", "2 semanas · mesas y brindis"]

T_PULL = 2.6
W0 = 3.8          # primer barrido
STEP = 4.4        # barrido + parada
WHIP = 0.8
T_FINAL_W = W0 + STEP * len(EST)
T_END = T_FINAL_W + WHIP + 5.6

ANCHO_NUM = {"12": 330, "10": 330, "6": 170, "3": 170, "2": 170}


def garabato_elipse(cx, cy, rx, ry, vueltas=1.18, seed=1.0, n=90):
    pts = []
    for k in range(n + 1):
        t = k / n * 2 * math.pi * vueltas - 0.6
        j = 1 + 0.045 * math.sin(3 * t + seed) + 0.03 * math.sin(7 * t + 2 * seed)
        drift = 1 + 0.06 * (k / n)
        pts.append((cx + rx * j * drift * math.cos(t), cy + ry * j * math.sin(t)))
    return "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)


def flecha(x1, y1, x2, y2, curva=0.25):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    cx, cy = mx - dy * curva, my + dx * curva
    ang = math.atan2(y2 - cy, x2 - cx)
    a1 = (x2 - 34 * math.cos(ang - 0.45), y2 - 34 * math.sin(ang - 0.45))
    a2 = (x2 - 34 * math.cos(ang + 0.45), y2 - 34 * math.sin(ang + 0.45))
    return (f"M{x1},{y1} Q{cx:.0f},{cy:.0f} {x2},{y2}",
            f"M{a1[0]:.0f},{a1[1]:.0f} L{x2},{y2} L{a2[0]:.0f},{a2[1]:.0f}")


def ondita(x, y, w, seed=0.0, amp=6):
    pts = [(x + w * k / 20, y + amp * math.sin(k * 0.9 + seed)) for k in range(21)]
    return "M" + " L".join(f"{a:.0f},{b:.0f}" for a, b in pts)


def caja(x, y, s, seed):
    # cuadradito a mano
    j = lambda k: 3 * math.sin(k * 2.3 + seed)
    return (f"M{x + j(1):.0f},{y + j(2):.0f} L{x + s + j(3):.0f},{y + j(4):.0f} L{x + s + j(5):.0f},{y + s + j(6):.0f} "
            f"L{x + j(7):.0f},{y + s + j(8):.0f} Z")


def tilde(x, y, s):
    return f"M{x + s * .15:.0f},{y + s * .55:.0f} L{x + s * .42:.0f},{y + s * .82:.0f} L{x + s * 1.05:.0f},{y - s * .15:.0f}"


def curva_por(puntos):
    # Catmull-Rom → Bézier
    d = f"M{puntos[0][0]},{puntos[0][1]}"
    for i in range(len(puntos) - 1):
        p0 = puntos[max(i - 1, 0)]; p1 = puntos[i]; p2 = puntos[i + 1]; p3 = puntos[min(i + 2, len(puntos) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.0f},{c1[1]:.0f} {c2[0]:.0f},{c2[1]:.0f} {p2[0]},{p2[1]}"
    return d


paths_fondo, paths = [], []


def P(lista, pid, d, color=GRAFITO, w=6):
    lista.append((pid, d, color, w))


def svg_de(lista):
    return "".join(
        f'<path id="{pid}" d="{d}" pathLength="1" stroke="{c}" stroke-width="{w}" fill="none" '
        f'stroke-linecap="round" stroke-linejoin="round" stroke-dasharray="1" stroke-dashoffset="1" />'
        for pid, d, c, w in lista)


def texto(t):
    out = html.escape(t)
    while "*" in out:
        out = out.replace("*", f'<span style="color:{ROJO}">', 1).replace("*", "</span>", 1)
    return out


# línea de tiempo que une las paradas por abajo
puntos = [(540, 2000)] + [(e["box"][0] + 540, e["box"][1] + 1990) for e in EST] + [(F[0] + 540, F[1] + 1990)]
P(paths_fondo, "tl", curva_por(puntos), GRAFITO, 4)
etiquetas_tl = "".join(
    f'<div class="abs hand tl-lab" style="left:{e["box"][0] + 600}px; top:{e["box"][1] + 2010}px; font-size:56px;">{e["tl"]}</div>'
    for e in EST)

estaciones_html = []
for i, e in enumerate(EST):
    bx, by = e["box"]
    w = ANCHO_NUM[e["num"]]
    es6 = e["img"] is None
    if es6:
        nx, ny, fs = 80, 150, 440
        P(paths, f"circ-{i}", garabato_elipse(bx + 200, by + 360, 190, 215, seed=2.1), GRAFITO, 7)
        unidad = f'<div class="abs hand wo" id="u-{i}" style="left:{bx + 70}px; top:{by + 640}px; font-size:92px; transform:rotate(-4deg);">{e["unidad"]}</div>'
        fl = flecha(bx + 600, by + 1060, bx + 760, by + 960, -0.3)
        P(paths, f"fl-{i}-a", fl[0], GRAFITO, 5)
        P(paths, f"fl-{i}-b", fl[1], GRAFITO, 5)
        tareas_top = 1060
        extra = f'''
    <div class="abs card" id="card" style="left:{bx + 580}px; top:{by + 200}px; width:420px; height:720px;"><img src="assets/img/figurin-n.jpg" alt="" /></div>
    <div class="tape" id="card-tape" style="left:{bx + 680}px; top:{by + 170}px; transform:rotate(-6deg);"></div>
    <div class="abs" id="stamp" style="left:{bx + 610}px; top:{by + 720}px;">1.ª PRUEBA</div>'''
        ill = ""
    else:
        nx, ny, fs = (110 if w > 200 else 90), 90, 300
        P(paths, f"circ-{i}", garabato_elipse(bx + nx + w / 2 + 5, by + 245, w / 2 + 45, 165, seed=0.7 + i), GRAFITO, 7)
        unidad = f'<div class="abs hand wo" id="u-{i}" style="left:{bx + nx + w + 110}px; top:{by + 230}px; font-size:92px; transform:rotate(-4deg);">{e["unidad"]}</div>'
        tareas_top = 470
        extra = ""
        if e["img"] and os.path.exists(f"assets/img/{e['img']}-n.jpg"):
            src = e["img"]
            ill = f'''
    <div class="abs ill" style="left:{bx}px; top:{by + e.get("dy", 0)}px; width:1080px; height:1920px;">
      <div class="ill-in" id="ill-{i}">
        <img class="pencil" id="pen-{i}" src="assets/img/{src}-n-lapiz.jpg" alt="" />
        <img class="wash" id="w{i}a" src="assets/img/{src}-n.jpg" alt="" style="opacity:.45" />
        <img class="wash" id="w{i}b" src="assets/img/{src}-n.jpg" alt="" style="opacity:.6" />
        <img class="wash" id="w{i}c" src="assets/img/{src}-n.jpg" alt="" />
      </div>
    </div>'''
        else:
            ill = ""
    tareas = "".join(f'''
      <div class="tarea"><div class="lab" id="lab-{i}-{j}">{html.escape(lab.upper())}</div>
      <div class="hand vuelta wo" id="v-{i}-{j}">{texto(v)}</div></div>''' for j, (lab, v) in enumerate(e["t"]))
    estaciones_html.append(f'''
    <!-- parada {e["tl"]} -->{ill}{extra}
    <div class="abs num wo" id="n-{i}" style="left:{bx + nx}px; top:{by + ny}px; font-size:{fs}px;">{e["num"]}</div>
    {unidad}
    <div class="abs tareas" style="left:{bx + 70}px; top:{by + tareas_top}px;">{tareas}</div>''')
    if e["num"] == "10":
        # subrayado rojo del "NO" (posición aproximada en la segunda línea)
        P(paths, f"no-{i}", ondita(bx + 555, by + 775, 110, 2.0), ROJO, 8)

# página final: la guía como checklist
fx, fy = F
P(paths, "g-sub", ondita(fx + 90, fy + 330, 560, 0.8), LILA, 7)
filas = []
for k, g in enumerate(GUIA):
    y = fy + 430 + k * 140
    P(paths, f"box-{k}", caja(fx + 90, y + 14, 56, k), GRAFITO, 5)
    P(paths, f"tick-{k}", tilde(fx + 90, y + 14, 56), LILA, 9)
    filas.append(f'<div class="abs hand wo fila" id="fila-{k}" style="left:{fx + 180}px; top:{y}px; font-size:66px; font-weight:500;">{html.escape(g)}</div>')

T = {"T_PULL": T_PULL, "W0": W0, "STEP": STEP, "WHIP": WHIP, "T_FINAL_W": T_FINAL_W, "T_END": T_END,
     "est": [{"cx": e["box"][0] + 540, "cy": e["box"][1] + 960, "es6": e["img"] is None,
              "ill": bool(e["img"] and os.path.exists(f"assets/img/{e['img']}-n.jpg")), "no": e["num"] == "10"} for e in EST],
     "fcx": fx + 540, "fcy": fy + 960, "guia": len(GUIA)}

page = f'''<!doctype html>
<html lang="es" data-resolution="portrait">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=1080, height=1920" />
<script src="assets/lib/gsap.min.js"></script>
<style>
@font-face {{ font-family: "Caveat"; src: url("assets/fonts/caveat-latin-500-normal.woff2") format("woff2"); font-weight: 500; }}
@font-face {{ font-family: "Caveat"; src: url("assets/fonts/caveat-latin-700-normal.woff2") format("woff2"); font-weight: 700; }}
@font-face {{ font-family: "Playfair"; src: url("assets/fonts/playfair-display-latin-900-italic.woff2") format("woff2"); font-weight: 900; font-style: italic; }}
@font-face {{ font-family: "Archivo"; src: url("assets/fonts/archivo-latin-700-normal.woff2") format("woff2"); font-weight: 700; }}
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:1080px; height:1920px; overflow:hidden; background:{PAPEL}; }}
#root {{ position:relative; width:1080px; height:1920px; overflow:hidden; background:{PAPEL}; }}
.clip {{ position:absolute; inset:0; overflow:hidden; }}
#shake, #cam {{ position:absolute; left:0; top:0; }}
#cam {{ transform-origin:0 0; }}
#world {{ position:absolute; left:0; top:0; width:{WW}px; height:{WH}px;
  background-image: radial-gradient(rgba(43,39,51,.13) 2.2px, transparent 2.6px), url("assets/img/papel.jpg");
  background-size: 60px 60px, 1882px 600px; }}
.abs {{ position:absolute; }}
.hand {{ font-family:Caveat, cursive; font-weight:700; color:{GRAFITO}; line-height:1.05; }}
.num {{ font-family:Playfair, serif; font-weight:900; font-style:italic; color:{GRAFITO}; line-height:.9; white-space:nowrap; }}
.lines {{ position:absolute; left:0; top:0; width:{WW}px; height:{WH}px; overflow:visible; }}
.wo {{ clip-path: inset(-20% 100% -20% 0%); }}
.tareas {{ width:940px; display:flex; flex-direction:column; gap:34px; }}
.lab {{ font-family:Archivo, sans-serif; font-weight:700; font-size:30px; letter-spacing:.18em; color:rgba(43,39,51,.62); margin-bottom:6px; }}
.vuelta {{ font-size:86px; color:{LILA}; }}
.tl-lab {{ opacity:0; white-space:nowrap; }}

#fig {{ left:70px; top:330px; width:940px; height:1670px; }}
#fig img, .ill img {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
#fig img {{ mix-blend-mode:multiply; }}
.ill {{ overflow:hidden; mix-blend-mode:multiply; }}
.ill-in {{ position:absolute; inset:0; }}
#fig-pencil, .pencil {{ clip-path: inset(0% 0% 100% 0%); }}
.wash {{ clip-path: circle(0% at 50% 60%); }}
#lead {{ position:absolute; left:0; right:0; height:3px; top:0; background:rgba(43,39,51,.55); }}

.card {{ background:#fffdf8; padding:16px; box-shadow:0 22px 50px rgba(43,39,51,.25); }}
.card img {{ width:100%; height:100%; object-fit:cover; object-position:50% 25%; }}
.tape {{ position:absolute; width:220px; height:64px; background:rgba(242,185,104,.62); box-shadow:0 2px 6px rgba(0,0,0,.08); }}
#stamp {{ font-family:Archivo, sans-serif; font-weight:700; font-size:58px; letter-spacing:.08em; color:{ROJO};
  border:7px solid {ROJO}; border-radius:10px; padding:8px 26px; mix-blend-mode:multiply; opacity:0; white-space:nowrap; }}
.fila {{ white-space:nowrap; }}
.grain {{ position:absolute; left:-200px; top:-200px; width:1480px; height:2320px; pointer-events:none; opacity:.09; mix-blend-mode:multiply;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='260' height='260'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"); }}
.vig {{ position:absolute; inset:0; pointer-events:none; background:radial-gradient(ellipse 80% 70% at 50% 50%, transparent 60%, rgba(60,45,30,.22) 100%); }}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{T_END:.2f}" data-width="1080" data-height="1920">
 <div id="stage" class="clip" data-start="0" data-duration="{T_END:.2f}" data-track-index="0">
  <div id="shake"><div id="cam"><div id="world">
    <div id="mapa"><svg class="lines" viewBox="0 0 {WW} {WH}">{svg_de(paths_fondo)}</svg>
    {etiquetas_tl}</div>

    <!-- apertura: figurín -->
    <div id="fig" class="abs">
      <img id="fig-pencil" src="assets/img/figurin-n-lapiz.jpg" alt="" />
      <img class="wash" id="fwa" src="assets/img/figurin-n.jpg" alt="" style="opacity:.45" />
      <img class="wash" id="fwb" src="assets/img/figurin-n.jpg" alt="" style="opacity:.6" />
      <img class="wash" id="fwc" src="assets/img/figurin-n.jpg" alt="" />
      <div id="lead"></div>
    </div>
    <div class="abs hand wo" id="q1" style="left:90px; top:120px; font-size:128px; white-space:nowrap;">¿Cuánto antes</div>
    <div class="abs hand wo" id="q2" style="left:300px; top:240px; font-size:128px; white-space:nowrap;">el <span style="color:{LILA}">vestido</span>?</div>
    {"".join(estaciones_html)}

    <!-- página final -->
    <div class="abs hand wo" id="g-title" style="left:{fx + 90}px; top:{fy + 180}px; font-size:140px; white-space:nowrap;">La guía del 15</div>
    {"".join(filas)}
    <div class="abs hand wo" id="g-cta1" style="left:{fx + 90}px; top:{fy + 1310}px; font-size:84px; color:{LILA}; white-space:nowrap;">Guardala y mandásela a quien</div>
    <div class="abs hand wo" id="g-cta2" style="left:{fx + 90}px; top:{fy + 1405}px; font-size:84px; color:{LILA}; white-space:nowrap;">esté organizando un 15.</div>
    <div class="abs hand wo" id="g-cta3" style="left:{fx + 90}px; top:{fy + 1520}px; font-size:72px; white-space:nowrap;">¿Arrancás? Escribinos.</div>
    <div class="abs" id="g-firma" style="left:{fx + 92}px; top:{fy + 1640}px; font-family:Archivo, sans-serif; font-weight:700; font-size:38px; letter-spacing:.32em; color:{GRAFITO}; opacity:0; white-space:nowrap;">VALLEVERDE EVENTOS</div>

    <svg class="lines" viewBox="0 0 {WW} {WH}">{svg_de(paths)}</svg>
  </div></div></div>
  <div class="vig"></div>
  <div class="grain" id="grain"></div>
 </div>
</div>

<script>
const T = {json.dumps(T)};
const tl = gsap.timeline({{ paused: true }});
const H = (id) => "#" + id;
function cam(t, px, py, z, r, dur, ease) {{
  tl.to("#cam", {{ x: 540, y: 960, scale: z, rotation: r, duration: dur, ease }}, t);
  tl.to("#world", {{ x: -px, y: -py, duration: dur, ease }}, t);
}}
function escribir(id, t, dur) {{
  tl.fromTo(H(id), {{ clipPath: "inset(-20% 100% -20% 0%)" }}, {{ clipPath: "inset(-20% 0% -20% 0%)", duration: dur, ease: "power1.inOut" }}, t);
}}
function trazar(id, t, dur) {{
  tl.fromTo(H(id), {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: dur, ease: "power2.inOut" }}, t);
}}
function barrido(t, px, py, z, r) {{
  cam(t, px, py, z, r, T.WHIP, "power4.inOut");
  tl.fromTo("#world", {{ filter: "blur(0px)" }}, {{ filter: "blur(14px)", duration: T.WHIP / 2, ease: "power2.in" }}, t);
  tl.to("#world", {{ filter: "blur(0px)", duration: T.WHIP / 2, ease: "power2.out" }}, t + T.WHIP / 2);
}}
function dibujarYpintar(pencil, washes, t, origen) {{
  tl.fromTo(pencil, {{ clipPath: "inset(0% 0% 100% 0%)" }}, {{ clipPath: "inset(0% 0% 0% 0%)", duration: 1.0, ease: "power1.inOut" }}, t);
  washes.forEach((id, k) => tl.fromTo(id, {{ clipPath: "circle(0% at " + origen + ")" }},
    {{ clipPath: "circle(85% at " + origen + ")", duration: 0.9 - k * 0.05, ease: "power2.out" }}, t + 0.6 + k * 0.12));
}}

// inicio
tl.set("#cam", {{ x: 540, y: 960, scale: 1, rotation: 0 }}, 0);
tl.set("#world", {{ x: -540, y: -960 }}, 0);
cam(0, 540, 1000, 1.05, 0.6, T.T_PULL, "sine.inOut");

// apertura
dibujarYpintar("#fig-pencil", ["#fwa", "#fwb", "#fwc"], 0.05, "50% 45%");
tl.fromTo("#lead", {{ y: 0, opacity: 1 }}, {{ y: 1670, duration: 1.0, ease: "power1.inOut" }}, 0.05);
tl.to("#lead", {{ opacity: 0, duration: 0.15 }}, 1.05);
escribir("q1", 0.3, 0.6);
escribir("q2", 0.9, 0.55);

// alejamiento: la hoja entera y la línea de tiempo
cam(T.T_PULL, 2100, 1700, 0.36, -4, 1.0, "power3.inOut");
trazar("tl", T.T_PULL + 0.1, 2.0);
tl.to(".tl-lab", {{ opacity: 1, duration: 0.3, stagger: 0.15 }}, T.T_PULL + 0.5);

// la línea de tiempo es solo para la vista general
tl.to("#mapa", {{ opacity: 0, duration: 0.4 }}, T.W0 + 0.2);

// paradas
T.est.forEach((e, i) => {{
  const w = T.W0 + T.STEP * i, a = w + T.WHIP;
  barrido(w, e.cx, e.cy, 1, i % 2 ? -1.5 : 1.5);
  escribir("n-" + i, a - 0.05, 0.3);
  trazar("circ-" + i, a + 0.15, 0.45);
  escribir("u-" + i, a + 0.3, 0.4);
  if (e.ill) {{
    dibujarYpintar("#pen-" + i, ["#w" + i + "a", "#w" + i + "b", "#w" + i + "c"], a + 0.1, "50% 65%");
    tl.fromTo("#ill-" + i, {{ scale: 1.0 }}, {{ scale: 1.05, duration: T.STEP, ease: "none", transformOrigin: "50% 70%" }}, a - 0.3);
  }}
  if (e.es6) {{
    tl.fromTo("#card", {{ y: -500, rotation: -14, opacity: 0 }}, {{ y: 0, rotation: 5, opacity: 1, duration: 0.6, ease: "back.out(1.5)" }}, a + 0.2);
    tl.fromTo("#card-tape", {{ scale: 1.6, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.22, ease: "power3.in" }}, a + 0.7);
    trazar("fl-" + i + "-a", a + 2.5, 0.3); trazar("fl-" + i + "-b", a + 2.78, 0.12);
    tl.fromTo("#stamp", {{ scale: 2.4, rotation: -4, opacity: 0 }}, {{ scale: 1, rotation: -12, opacity: 0.92, duration: 0.16, ease: "power4.in" }}, a + 2.9);
    tl.fromTo("#shake", {{ x: 0, y: 0 }}, {{ x: 9, y: -7, duration: 0.05, yoyo: true, repeat: 5, ease: "none" }}, a + 3.06);
  }}
  [0, 1].forEach((j) => {{
    const tj = a + 0.95 + j * 0.95;
    tl.fromTo("#lab-" + i + "-" + j, {{ opacity: 0, x: -20 }}, {{ opacity: 1, x: 0, duration: 0.3 }}, tj);
    escribir("v-" + i + "-" + j, tj + 0.1, 0.55);
  }});
  if (e.no) trazar("no-" + i, a + 2.75, 0.2);
}});

// página final
barrido(T.T_FINAL_W, T.fcx, T.fcy, 1, -1);
const f = T.T_FINAL_W + T.WHIP;
escribir("g-title", f, 0.6);
trazar("g-sub", f + 0.6, 0.3);
for (let k = 0; k < T.guia; k++) {{
  trazar("box-" + k, f + 0.8 + k * 0.28, 0.2);
  escribir("fila-" + k, f + 0.85 + k * 0.28, 0.35);
}}
for (let k = 0; k < T.guia; k++) trazar("tick-" + k, f + 2.6 + k * 0.13, 0.15);
escribir("g-cta1", f + 3.5, 0.5);
escribir("g-cta2", f + 3.95, 0.4);
escribir("g-cta3", f + 4.4, 0.4);
tl.fromTo("#g-firma", {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.4 }}, f + 4.8);

// cámara en mano y grano
tl.fromTo("#shake", {{ rotation: -0.25 }}, {{ rotation: 0.25, duration: 1.9, yoyo: true, repeat: Math.ceil(T.T_END / 1.9), ease: "sine.inOut" }}, 0);
for (let i = 0; i < Math.ceil(T.T_END * 15); i++) tl.set("#grain", {{ x: ((i * 73) % 200) - 100, y: ((i * 131) % 200) - 100 }}, i / 15);

window.__timelines = window.__timelines || {{}};
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
'''
open("index.html", "w").write(page)
print("duración", round(T_END, 1), "s")
