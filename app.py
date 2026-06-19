import math
import json
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VMS GeoCloud - SENSOIL Demo Comercial",
    page_icon="🌍",
    layout="wide"
)

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    .stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background-color: #1f6feb !important; color: white !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; color: #58a6ff; }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.75rem; }
    [data-testid="stDialog"] > div { background-color: #161b22 !important; border: 1px solid #30363d; border-radius: 12px; }
    .stButton > button {
        background: linear-gradient(135deg, #1f6feb, #388bfd);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(31,111,235,0.4); }
    .stSelectbox label, .stSidebar label { color: #8b949e; }
    #MainMenu, header, footer { visibility: hidden; }
    hr { border-color: #30363d; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. CONFIGURACIÓN DE PROYECTOS
# ─────────────────────────────────────────────
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data":    "Romeral.csv",
        "csv_rain":    "RomeralRain.csv",
        "lat":         -28.493772,
        "lon":         -71.254531,
        "max_sensores": 7,
        "angle_deg":   55.0,
        "soil_layers": [
            ("#A0875A", "Relleno superficial"),
            ("#8C7050", "Suelo arcilloso"),
            ("#7A5C40", "Arcilla densa"),
            ("#6B4E34", "Arcilla compacta"),
            ("#5C4128", "Roca base"),
            ("#4A3220", "Roca profunda"),
        ],
    },
    "ROMERAL": {
        "csv_data":    "Romeral.csv",
        "csv_rain":    "RomeralRain.csv",
        "lat":         -29.726153,
        "lon":         -71.221878,
        "max_sensores": 8,
        "angle_deg":   55.0,
        "soil_layers": [
            ("#9E8B6A", "Relleno superficial"),
            ("#8A7255", "Limo arenoso"),
            ("#785E42", "Arcilla limosa"),
            ("#664A30", "Arcilla compacta"),
            ("#563D22", "Grava fina"),
            ("#422E18", "Roca base"),
            ("#321F0E", "Roca profunda"),
            ("#241408", "Roca dura"),
        ],
    },
}

# ─────────────────────────────────────────────
# 3. UTILIDADES
# ─────────────────────────────────────────────
@st.cache_data
def cargar_datos_proyecto(id_proyecto: str):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    try:
        df = pd.read_csv(cfg["csv_data"], skiprows=[0, 2, 3])
        df.columns = df.columns.str.replace('"', '').str.replace("'", "").str.strip()
        df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'].astype(str).str.replace('"', ''))
        return df, None
    except Exception as e:
        return None, f"Error al abrir {cfg['csv_data']}: {e}"


def get_cols(df, prefix, n):
    cols = sorted(
        [c for c in df.columns if c.startswith(f"{prefix}_")],
        key=lambda x: int(x.split('_')[1]) if len(x.split('_')) > 1 and x.split('_')[1].isdigit() else 0
    )
    return cols[:n]


def fmt_depth(col_name: str) -> str:
    """'VWC_1_40cm' → '0.40 m'"""
    try:
        parts = col_name.split('_')
        if len(parts) >= 3:
            cm = float(parts[2].replace('cm', '').replace('CM', ''))
            return f"{cm / 100:.2f} m"
    except Exception:
        pass
    return "N/A"


def depth_cm(col_name: str) -> float:
    try:
        parts = col_name.split('_')
        if len(parts) >= 3:
            return float(parts[2].replace('cm', '').replace('CM', ''))
    except Exception:
        pass
    return 0.0


def safe_val(serie, col, decimals=2):
    try:
        return f"{float(serie[col]):.{decimals}f}"
    except Exception:
        return "N/D"


# ─────────────────────────────────────────────
# 4. GENERADOR SVG DINÁMICO DEL PERFIL DE SUELO
# ─────────────────────────────────────────────
SVG_W       = 680
SVG_H       = 660
SURFACE_Y   = 118
MAX_DEPTH_Y = 608
CABLE_X0    = 310


def sensor_xy(depth_cm_val: float, angle_deg: float):
    depth_m      = depth_cm_val / 100.0
    px_per_meter = (MAX_DEPTH_Y - SURFACE_Y) / 6.0
    dy           = depth_m * px_per_meter
    dx           = dy * math.tan(math.radians(angle_deg))
    return (round(CABLE_X0 + dx, 1), round(SURFACE_Y + dy, 1))


def render_soil_profile(id_proyecto, cfg, cols_vwc, cols_temp, cols_pt, cols_dpt, ultimo_reg):
    angle      = cfg.get("angle_deg", 55.0)
    layers     = cfg.get("soil_layers", [])
    n_sens     = cfg["max_sensores"]
    lat, lon   = cfg["lat"], cfg["lon"]
    layer_h    = max(60, (MAX_DEPTH_Y - SURFACE_Y - 2) // max(len(layers), 1))

    # ── Datos de cada sensor ──
    sensors = []
    for i in range(n_sens):
        cv = cols_vwc[i]  if i < len(cols_vwc)  else None
        ct = cols_temp[i] if i < len(cols_temp) else None
        cp = cols_pt[i]   if i < len(cols_pt)   else None
        cd = cols_dpt[i]  if i < len(cols_dpt)  else None
        dc = depth_cm(cv) if cv else (i + 1) * 80.0
        sx, sy = sensor_xy(dc, angle)
        sensors.append({
            "idx":   i,
            "label": f"S{i+1}",
            "depth": fmt_depth(cv) if cv else f"{dc/100:.2f} m",
            "x": sx, "y": sy,
            "vwc":  safe_val(ultimo_reg, cv, 2)  if cv else "N/D",
            "temp": safe_val(ultimo_reg, ct, 1)  if ct else "N/D",
            "pt":   safe_val(ultimo_reg, cp, 0)  if cp else "N/D",
            "dpt":  safe_val(ultimo_reg, cd, 1)  if cd else "N/D",
        })

    # ── Capas de suelo ──
    layer_svg = []
    for idx, (color, label) in enumerate(layers):
        y_top = SURFACE_Y + 2 + idx * layer_h
        h     = min(layer_h, SVG_H - y_top - 4)
        if h <= 0:
            break
        layer_svg.append(
            f'<rect x="0" y="{y_top}" width="{SVG_W}" height="{h}" fill="{color}"/>'
            f'<rect x="0" y="{y_top+h-1}" width="{SVG_W}" height="1.5" fill="#2a1a08" opacity="0.35"/>'
            f'<text x="14" y="{y_top+16}" font-family="\'Segoe UI\',sans-serif" '
            f'font-size="11" fill="#f0ddb8" opacity="0.6">{label}</text>'
        )

    # ── Cable ──
    last      = sensors[-1]
    cable_ex  = last["x"] + 18 * math.tan(math.radians(angle))
    cable_ey  = min(last["y"] + 18, SVG_H - 8)

    # ── Pines / sensores ──
    pins_svg = []
    for s in sensors:
        px, py  = s["x"], s["y"]
        tip_x   = px + 14
        tip_w   = 158
        if tip_x + tip_w > SVG_W - 6:
            tip_x = px - tip_w - 10

        # stagger de animación
        delay = f"{s['idx'] * 0.35:.2f}s"

        pins_svg.append(f"""
  <g class="vms-sensor" data-idx="{s['idx']}" style="cursor:pointer">
    <circle class="vms-halo" cx="{px}" cy="{py}" r="13"
            fill="#1f7fe8" opacity="0.15"
            style="animation-delay:{delay}"/>
    <circle cx="{px}" cy="{py}" r="8"
            fill="#1255b0" stroke="#7dc3ff" stroke-width="2"/>
    <circle cx="{px}" cy="{py}" r="3.5" fill="#7dc3ff"/>
    <rect x="{px+11}" y="{py-11}" width="28" height="15"
          rx="4" fill="#0a1f3c" stroke="#1f7fe8" stroke-width="0.8"/>
    <text x="{px+25}" y="{py-3}"
          text-anchor="middle" dominant-baseline="central"
          font-family="'Segoe UI',sans-serif" font-size="10"
          font-weight="700" fill="#7dc3ff">{s['label']}</text>
    <g class="vms-tip" opacity="0" pointer-events="none">
      <rect x="{tip_x-4}" y="{py-14}" width="{tip_w}" height="80"
            rx="7" fill="#0d1a2e" stroke="#1f7fe8" stroke-width="0.9"/>
      <text x="{tip_x+3}" y="{py+4}"
            font-family="'Segoe UI',sans-serif" font-size="11"
            font-weight="700" fill="#7dc3ff">{s['label']} · {s['depth']}</text>
      <text x="{tip_x+3}" y="{py+20}"
            font-family="'Segoe UI',sans-serif" font-size="10" fill="#a8cce8">
        VWC: <tspan font-weight="700" fill="#3dd68c">{s['vwc']} %</tspan>
        &#160;&#160;T: <tspan font-weight="700" fill="#f6a03a">{s['temp']} °C</tspan>
      </text>
      <text x="{tip_x+3}" y="{py+36}"
            font-family="'Segoe UI',sans-serif" font-size="10" fill="#a8cce8">
        Presión: <tspan font-weight="700" fill="#c084fc">{s['pt']} mbar</tspan>
        &#160; Nivel: <tspan font-weight="700" fill="#38bdf8">{s['dpt']} cm</tspan>
      </text>
      <text x="{tip_x+3}" y="{py+54}"
            font-family="'Segoe UI',sans-serif" font-size="10" fill="#4a9aaa">
        Clic para análisis completo →
      </text>
    </g>
  </g>""")

    # ── Regla de profundidad ──
    ruler_marks = 7
    ruler_svg   = [
        f'<line x1="634" y1="{SURFACE_Y}" x2="634" y2="{MAX_DEPTH_Y}" '
        f'stroke="#ffffff" stroke-width="0.5" opacity="0.25"/>'
    ]
    for i in range(ruler_marks):
        ry = SURFACE_Y + i * (MAX_DEPTH_Y - SURFACE_Y) // (ruler_marks - 1)
        ruler_svg.append(
            f'<line x1="628" y1="{ry}" x2="640" y2="{ry}" '
            f'stroke="#ffffff" stroke-width="0.8" opacity="0.4"/>'
            f'<text x="646" y="{ry+4}" font-family="\'Segoe UI\',sans-serif" '
            f'font-size="10" fill="#c8dae8" opacity="0.7">{i} m</text>'
        )

    # ── Ángulo ──
    ar     = math.radians(angle)
    ax     = CABLE_X0 + 24 * math.sin(ar)
    ay     = SURFACE_Y + 24 - 24 * (1 - math.cos(ar))

    try:
        ts = ultimo_reg["TIMESTAMP"].strftime("%Y-%m-%d %H:%M")
    except Exception:
        ts = ""

    sensors_json = json.dumps(sensors)

    # ── HTML + SVG final ──
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  html,body{{background:transparent;overflow:hidden}}
  svg{{display:block;width:100%}}
  @keyframes vms-pulse{{0%,100%{{r:13;opacity:0.15}}50%{{r:19;opacity:0.07}}}}
  .vms-halo{{animation:vms-pulse 2.6s ease-in-out infinite}}
  .vms-sensor:hover .vms-tip{{opacity:1!important}}
  .vms-sensor:hover circle:nth-child(2){{filter:brightness(1.3)}}
  .vms-selected circle:nth-child(2){{stroke:#ffe066;stroke-width:2.5}}
</style>
</head><body>
<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#c2dff0"/>
    <stop offset="100%" stop-color="#9ec8e4"/>
  </linearGradient>
</defs>

<!-- Cielo -->
<rect x="0" y="0" width="{SVG_W}" height="{SURFACE_Y}" fill="url(#sky)"/>

<!-- Título -->
<text x="14" y="22" font-family="'Segoe UI',sans-serif" font-size="13"
      font-weight="700" fill="#1a3a5c">{id_proyecto} — VMS GeoCloud · Sensoil</text>
<text x="14" y="40" font-family="'Segoe UI',sans-serif" font-size="10"
      fill="#4a7090">Última lectura: {ts} · {lat:.4f} / {lon:.4f}</text>
<text x="14" y="56" font-family="'Segoe UI',sans-serif" font-size="10"
      fill="#3a8a6a">Pasa el cursor sobre un sensor · Clic para análisis completo</text>

<!-- Estación VMIS -->
<rect x="262" y="50" width="96" height="58" rx="8"
      fill="#ddeeff" stroke="#80aacc" stroke-width="1"/>
<rect x="270" y="38" width="80" height="14" rx="3"
      fill="#4a90d9" stroke="#2a70b9" stroke-width="0.8"/>
<text x="310" y="72" text-anchor="middle" dominant-baseline="central"
      font-family="'Segoe UI',sans-serif" font-size="12" font-weight="700"
      fill="#1a3a5c">VMIS</text>
<text x="310" y="90" text-anchor="middle"
      font-family="'Segoe UI',sans-serif" font-size="9" fill="#3a6080">Estación</text>
<line x1="346" y1="38" x2="354" y2="24" stroke="#4a7a9a" stroke-width="1.5"/>
<circle cx="356" cy="22" r="3" fill="none" stroke="#4a9ad9" stroke-width="1.2"/>

<!-- Superficie -->
<rect x="0" y="{SURFACE_Y}" width="{SVG_W}" height="10" fill="#9a7c48"/>

<!-- Capas de suelo -->
{"".join(layer_svg)}

<!-- Cable: manguera multipar -->
<line x1="{CABLE_X0}" y1="{SURFACE_Y+8}" x2="{cable_ex:.1f}" y2="{cable_ey:.1f}"
      stroke="#2e7a2e" stroke-width="5" stroke-linecap="round" opacity="0.85"/>
<line x1="{CABLE_X0+4}" y1="{SURFACE_Y+8}" x2="{cable_ex+4:.1f}" y2="{cable_ey:.1f}"
      stroke="#c8a820" stroke-width="3" stroke-linecap="round" opacity="0.8"/>

<!-- Ángulo -->
<path d="M{CABLE_X0} {SURFACE_Y+24} A24 24 0 0 1 {ax:.1f} {ay:.1f}"
      fill="none" stroke="#ffffff" stroke-width="1" opacity="0.55"/>
<text x="{CABLE_X0+30}" y="{SURFACE_Y+32}"
      font-family="'Segoe UI',sans-serif" font-size="11"
      fill="#ffffff" opacity="0.75">{angle:.0f}°</text>

<!-- Sensores -->
{"".join(pins_svg)}

<!-- Regla -->
{"".join(ruler_svg)}

</svg>

<script>
const SENSORS = {sensors_json};
document.querySelectorAll('.vms-sensor').forEach(el => {{
  el.addEventListener('click', () => {{
    const idx = parseInt(el.dataset.idx);
    document.querySelectorAll('.vms-sensor').forEach(e => e.classList.remove('vms-selected'));
    el.classList.add('vms-selected');
    window.parent.postMessage({{
      isstreamlitMessage: true,
      type: "streamlit:setComponentValue",
      value: idx
    }}, "*");
  }});
}});
(function resize() {{
  const h = document.querySelector('svg').getBoundingClientRect().height;
  if (h > 80) window.parent.postMessage({{
    isstreamlitMessage: true,
    type: "streamlit:setFrameHeight",
    height: Math.ceil(h) + 10
  }}, "*");
  setTimeout(resize, 500);
}})();
</script>
</body></html>"""


# ─────────────────────────────────────────────
# 5. MODAL DE SENSOR
# ─────────────────────────────────────────────
@st.dialog("📊 Análisis de Sensor Completo", width="large")
def modal_sensor(id_proyecto, idx, df_data, ultimo_registro,
                 cols_vwc, cols_temp, cols_pt, cols_dpt,
                 fecha_sel, variable_grafico):
    cv = cols_vwc[idx]  if idx < len(cols_vwc)  else None
    ct = cols_temp[idx] if idx < len(cols_temp) else None
    cp = cols_pt[idx]   if idx < len(cols_pt)   else None
    cd = cols_dpt[idx]  if idx < len(cols_dpt)  else None
    prof = fmt_depth(cv) if cv else "N/A"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1f6feb22,#388bfd11);
         border:1px solid #1f6feb44; border-radius:10px;
         padding:14px 18px; margin-bottom:12px;">
      <h3 style="margin:0;color:#58a6ff;">📡 Sensor S{idx+1} — Profundidad {prof}</h3>
      <p style="margin:0;color:#8b949e;font-size:0.85rem;">
        Estación: <b style="color:#e6edf3">{id_proyecto}</b> &nbsp;|&nbsp;
        Última Lectura: <b style="color:#e6edf3">
          {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M')}
        </b>
      </p>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("💧 Humedad VWC",       f"{safe_val(ultimo_registro, cv)} %"    if cv else "N/D")
    with m2: st.metric("🌡️ Temperatura",        f"{safe_val(ultimo_registro, ct, 1)} °C" if ct else "N/D")
    with m3: st.metric("⚡ Presión de Poros",   f"{safe_val(ultimo_registro, cp, 0)} mbar" if cp else "N/D")
    with m4: st.metric("📏 Nivel Hidrostático", f"{safe_val(ultimo_registro, cd, 1)} cm"  if cd else "N/D")

    st.markdown("---")
    st.markdown(f"#### 📈 Historial — {variable_grafico} (Últimos 7 días)")

    fecha_max = pd.Timestamp(fecha_sel)
    fecha_min = fecha_max - pd.Timedelta(days=7)
    df_f = df_data[
        (df_data['TIMESTAMP'] >= fecha_min) &
        (df_data['TIMESTAMP'] <= fecha_max + pd.Timedelta(days=1))
    ]
    mapeo = {
        "Humedad (VWC %)":         cv,
        "Temperatura (°C)":        ct,
        "Presión de Celda (mbar)": cp,
        "Nivel (cm)":              cd,
    }
    col_obj = mapeo.get(variable_grafico)
    if col_obj and col_obj in df_f.columns:
        df_g = df_f[['TIMESTAMP', col_obj]].copy()
        df_g.columns = ['Fecha', f"S{idx+1} ({prof})"]
        df_g.set_index('Fecha', inplace=True)
        st.line_chart(df_g, use_container_width=True)

    if st.button("← Volver a la Radiografía",
                 key=f"close_sens_{id_proyecto}_{idx}",
                 use_container_width=True):
        st.session_state[f"sensor_modal_{id_proyecto}"] = None
        st.session_state[f"abrir_radio_{id_proyecto}"]  = True
        st.rerun()


# ─────────────────────────────────────────────
# 6. MODAL DE RADIOGRAFÍA
# ─────────────────────────────────────────────
@st.dialog("🏗️ Radiografía Estructural del Pozo", width="large")
def modal_radiografia(id_proyecto, df_data, ultimo_registro,
                      cols_vwc, cols_temp, cols_pt, cols_dpt,
                      fecha_sel, variable_grafico):
    cfg = CONFIG_PROYECTOS[id_proyecto]

    st.markdown(f"""
    <p style="color:#8b949e;font-size:0.85rem;margin-bottom:10px;">
      📍 <b style="color:#58a6ff">{id_proyecto}</b> &nbsp;·&nbsp;
      {cfg['max_sensores']} sensores activos &nbsp;·&nbsp;
      Pasa el cursor sobre cada sensor para ver los datos.
      Haz <b>clic</b> para el análisis completo.
    </p>
    """, unsafe_allow_html=True)

    html_code = render_soil_profile(
        id_proyecto, cfg,
        cols_vwc, cols_temp, cols_pt, cols_dpt,
        ultimo_registro,
    )

    click_index = st.components.v1.html(html_code, height=680, scrolling=False)

    if click_index is not None and click_index != "":
        st.session_state[f"sensor_modal_{id_proyecto}"] = int(click_index)
        st.session_state[f"abrir_radio_{id_proyecto}"]  = False
        st.rerun()

    st.markdown("---")
    st.markdown("##### Acceso directo por sensor:")
    cols_btns = st.columns(cfg["max_sensores"])
    for i, col in enumerate(cols_btns):
        with col:
            prof = fmt_depth(cols_vwc[i]) if i < len(cols_vwc) else ""
            if st.button(f"S{i+1}\n{prof}",
                         key=f"quick_{id_proyecto}_{i}",
                         use_container_width=True):
                st.session_state[f"sensor_modal_{id_proyecto}"] = i
                st.session_state[f"abrir_radio_{id_proyecto}"]  = False
                st.rerun()


# ─────────────────────────────────────────────
# 7. SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png",
        width=130,
    )
    st.markdown("## VMS GeoCloud")
    st.markdown("---")

    df_aux, _ = cargar_datos_proyecto("ROMERAL")
    fechas_sim = (
        sorted(df_aux['TIMESTAMP'].dt.date.unique(), reverse=True)
        if df_aux is not None else []
    )

    fecha_sel = st.selectbox(
        "📅 Fecha de simulación:", fechas_sim, key="global_fecha_sel"
    )
    variable_grafico = st.selectbox(
        "📈 Variable histórica:",
        ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"],
        key="global_var_sel",
    )


# ─────────────────────────────────────────────
# 8. PANEL POR PROYECTO
# ─────────────────────────────────────────────
def construir_interfaz_proyecto(id_proyecto: str):
    cfg      = CONFIG_PROYECTOS[id_proyecto]
    df_data, error = cargar_datos_proyecto(id_proyecto)
    if error or df_data is None:
        st.error(error)
        return

    n        = cfg["max_sensores"]
    cols_vwc  = get_cols(df_data, "VWC",  n)
    cols_temp = get_cols(df_data, "TEMP", n)
    cols_pt   = get_cols(df_data, "PT",   n)
    cols_dpt  = get_cols(df_data, "DPT",  n)

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("⚠️ Sin registros para el día seleccionado.")
        return
    ultimo = df_dia.iloc[-1]

    st.markdown(
        f"### 🗺️ Monitoreo Satelital — <span style='color:#58a6ff'>{id_proyecto}</span>",
        unsafe_allow_html=True,
    )
    st.caption("Haz clic en el marcador del mapa para abrir la radiografía interactiva del pozo.")

    # Mapa
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satelital', control=False,
    ).add_to(m)
    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        tooltip=f"Ver Radiografía {id_proyecto}",
        icon=folium.Icon(color="blue", icon="info-sign"),
    ).add_to(m)

    mapa_out = st_folium(m, width="100%", height=380, key=f"mapa_{id_proyecto}")
    if mapa_out and mapa_out.get("last_object_clicked"):
        st.session_state[f"abrir_radio_{id_proyecto}"] = True
        st.rerun()

    # Modal radiografía
    if st.session_state.get(f"abrir_radio_{id_proyecto}"):
        modal_radiografia(
            id_proyecto, df_data, ultimo,
            cols_vwc, cols_temp, cols_pt, cols_dpt,
            fecha_sel, variable_grafico,
        )

    # Modal sensor
    sensor_idx = st.session_state.get(f"sensor_modal_{id_proyecto}")
    if sensor_idx is not None:
        modal_sensor(
            id_proyecto, sensor_idx, df_data, ultimo,
            cols_vwc, cols_temp, cols_pt, cols_dpt,
            fecha_sel, variable_grafico,
        )

    # Tabla resumen
    st.markdown("##### 📊 Estado de Sensores")
    resumen = []
    for i in range(n):
        resumen.append({
            "Sensor":        f"S{i+1}",
            "Profundidad":   fmt_depth(cols_vwc[i]) if i < len(cols_vwc) else "N/A",
            "VWC (%)":       safe_val(ultimo, cols_vwc[i])  if i < len(cols_vwc)  else "N/D",
            "Temp (°C)":     safe_val(ultimo, cols_temp[i], 1) if i < len(cols_temp) else "N/D",
            "Presión (mbar)": safe_val(ultimo, cols_pt[i], 0)  if i < len(cols_pt)   else "N/D",
            "Nivel (cm)":    safe_val(ultimo, cols_dpt[i], 1)  if i < len(cols_dpt)  else "N/D",
        })
    st.dataframe(pd.DataFrame(resumen), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# 9. PESTAÑAS PRINCIPALES
# ─────────────────────────────────────────────
tab_drf, tab_romeral = st.tabs([
    "📍 Estación DRF Chile",
    "📍 Estación El Romeral",
])

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
