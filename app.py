import math
import json
import streamlit as st
import pandas as pd
import plotly.express as px

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VMS SENSOIL",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="collapsed"  # Oculta la barra lateral vacía por defecto
)

st.markdown("""
<style>
    .stApp { background-color: #0d1117; color: #e6edf3; }
    section[data-testid="stSidebar"] { display: none; } /* Fuerza la desaparición visual del sidebar */
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

    /* ── Panel tipo "tarjeta" usado en sensores / leyenda / detalles del pozo ── */
    .vms-card {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 14px;
    }
    .vms-card h4 {
        color: #e6edf3; font-size: 0.85rem; font-weight: 700;
        margin: 0 0 10px 0; letter-spacing: 0.03em;
        border-bottom: 1px solid #30363d; padding-bottom: 8px;
    }
    .vms-sensor-row {
        display:flex; align-items:center; justify-content:space-between;
        padding: 6px 0; border-bottom: 1px dashed #21262d;
    }
    .vms-sensor-row:last-child { border-bottom: none; }
    .vms-badge {
        display:inline-flex; align-items:center; justify-content:center;
        width:26px; height:26px; border-radius:50%;
        background:#1f6feb; color:white; font-weight:700; font-size:0.75rem;
        margin-right:8px; flex-shrink:0;
    }
    .vms-badge-selected { background:#3dd68c !important; color:#0d1117 !important; }
    .vms-sensor-meta { font-size:0.72rem; color:#8b949e; line-height:1.3; }
    .vms-sensor-meta b { color:#e6edf3; }
    .vms-detail-row {
        display:flex; justify-content:space-between;
        font-size:0.8rem; padding:5px 0; border-bottom: 1px dashed #21262d;
    }
    .vms-detail-row:last-child { border-bottom:none; }
    .vms-detail-row span:first-child { color:#8b949e; }
    .vms-detail-row span:last-child { color:#e6edf3; font-weight:600; text-align:right; }
    .vms-status-pill {
        display:inline-block; padding:3px 10px; border-radius:20px;
        font-size:0.72rem; font-weight:700;
    }
    .vms-status-normal { background:#1a3a2a; color:#3dd68c; border:1px solid #235c3d; }
    .vms-status-alerta { background:#3a1a1a; color:#f87171; border:1px solid #5c2323; }
    .vms-legend-row { display:flex; align-items:center; gap:8px; font-size:0.75rem; color:#c9d1d9; padding:4px 0; }
    .vms-legend-icon { width:20px; text-align:center; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 2. CONFIGURACIÓN DE PROYECTOS
# ─────────────────────────────────────────────
CONFIG_PROYECTOS = {
    "DRF": {
        "nombre_estacion": "VMS - DRF - HUASCO",
        "csv_data":    "DRF.csv",        
        "csv_rain":    "DRFRain.csv",    
        "max_sensores": 7,
        "angle_deg":   55.0,
        "diametro_perforacion": "HQ (96 mm)",
        "tipo_instalacion": "Tubo PVC Ø 2\" Ranurado",
        "fecha_instalacion": "—",
        "soil_layers": [
            ("#A0875A", "Layer 1"),
            ("#8C7050", "Layer 2"),
            ("#7A5C40", "Layer 3"),
            ("#6B4E34", "Layer 4"),
            ("#5C4128", "Layer 5"),
            ("#4A3220", "Layer 6"),
        ],
    },
    "ROMERAL": {
        "nombre_estacion": "VMS - EL ROMERAL",
        "csv_data":    "Romeral.csv",
        "csv_rain":    "RomeralRain.csv",
        "max_sensores": 8,
        "angle_deg":   55.0,
        "diametro_perforacion": "HQ (96 mm)",
        "tipo_instalacion": "Tubo PVC Ø 2\" Ranurado",
        "fecha_instalacion": "—",
        "soil_layers": [
            ("#9E8B6A", "Layer 1"),
            ("#8A7255", "Layer 2"),
            ("#785E42", "Layer 3"),
            ("#664A30", "Layer 4"),
            ("#563D22", "Layer 5"),
            ("#422E18", "Layer 6"),
            ("#321F0E", "Layer 7"),
            ("#241408", "Layer 8"),
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


def estado_sensor(vwc_str: str) -> str:
    try:
        v = float(vwc_str)
        if v > 45 or v < 2:
            return "ALERTA"
    except Exception:
        pass
    return "NORMAL"


# =============================================================================
# 4. GENERADOR SVG DINÁMICO DEL PERFIL DE SUELO (VERSION OPTIMIZADA)
# =============================================================================
SVG_W       = 680
SVG_H       = 660
SURFACE_Y   = 100
MAX_DEPTH_Y = 608
CABLE_X0    = 340
REF_LINE_X  = 70

def sensor_xy(depth_cm_val: float, angle_deg: float, max_depth_cm: float):
    depth_m = depth_cm_val / 100.0
    max_depth_m = max(1.0, max_depth_cm / 100.0) 
    
    px_per_meter = (MAX_DEPTH_Y - SURFACE_Y) / max_depth_m
    
    dy = depth_m * px_per_meter
    dx = dy * math.tan(math.radians(angle_deg))
    return (round(CABLE_X0 + dx, 1), round(SURFACE_Y + dy, 1))

def render_soil_profile(id_proyecto, cfg, cols_vwc, cols_temp, cols_pt, cols_dpt,
                        ultimo_reg, selected_idx=0):
    angle_visual = 22.0  
    layers = cfg.get("soil_layers", [])
    n_sens = cfg["max_sensores"]
    
    real_max_depth_cm = 600.0
    for cv in cols_vwc:
        dc = depth_cm(cv)
        if dc > real_max_depth_cm:
            real_max_depth_cm = dc
    real_max_depth_cm += 200.0 
    real_max_depth_m = real_max_depth_cm / 100.0

    layer_h = max(30, (MAX_DEPTH_Y - SURFACE_Y - 2) // max(len(layers), 1))

    sensors = []
    px_per_meter = (MAX_DEPTH_Y - SURFACE_Y) / (real_max_depth_cm / 100.0)
    
    for i in range(n_sens):
        cv = cols_vwc[i]  if i < len(cols_vwc)  else None
        ct = cols_temp[i] if i < len(cols_temp) else None
        cp = cols_pt[i]   if i < len(cols_pt)   else None
        cd = cols_dpt[i]  if i < len(cols_dpt)  else None
        dc = depth_cm(cv) if cv else (i + 1) * 80.0
        
        depth_m = dc / 100.0
        dy = depth_m * px_per_meter
        dx = dy * math.tan(math.radians(angle_visual))
        sx, sy = round(CABLE_X0 + dx, 1), round(SURFACE_Y + dy, 1)
        
        sensors.append({
            "idx":   i,
            "label": f"S{i+1}",
            "depth": fmt_depth(cv) if cv else f"{dc/100:.2f} m",
            "x": sx, "y": sy,
            "vwc":   safe_val(ultimo_reg, cv, 2)  if cv else "N/D",
            "temp": safe_val(ultimo_reg, ct, 1)  if ct else "N/D",
            "pt":   safe_val(ultimo_reg, cp, 0)  if cp else "N/D",
            "dpt":  safe_val(ultimo_reg, cd, 1)  if cd else "N/D",
        })

    layer_svg = []
    for idx, (color, _) in enumerate(layers):
        y_top = SURFACE_Y + 2 + idx * layer_h
        h     = min(layer_h, SVG_H - y_top - 4)
        if h <= 0:
            break
        layer_svg.append(
            f'<rect x="0" y="{y_top}" width="{SVG_W}" height="{h}" fill="{color}"/>'
            f'<rect x="0" y="{y_top+h-1}" width="{SVG_W}" height="1.5" fill="#2a1a08" opacity="0.25"/>'
        )

    last      = sensors[-1]
    cable_ex  = last["x"] + 15 * math.tan(math.radians(angle_visual))
    cable_ey  = min(last["y"] + 15, SVG_H - 8)

    pins_svg = []
    for s in sensors:
        px, py     = s["x"], s["y"]
        tip_x      = px + 14
        tip_w      = 160
        if tip_x + tip_w > SVG_W - 6:
            tip_x = px - tip_w - 10
        is_sel     = (s["idx"] == selected_idx)
        ring_color = "#ffe066" if is_sel else "#7dc3ff"
        delay      = f"{s['idx'] * 0.25:.2f}s"

        pins_svg.append(f"""
  <g class="vms-sensor{' vms-selected' if is_sel else ''}" data-idx="{s['idx']}" style="cursor:pointer">
    <circle class="vms-halo" cx="{px}" cy="{py}" r="13" fill="#1f7fe8" opacity="0.15" style="animation-delay:{delay}"/>
    <circle cx="{px}" cy="{py}" r="8" fill="#1255b0" stroke="{ring_color}" stroke-width="2.2"/>
    <circle cx="{px}" cy="{py}" r="3.5" fill="{ring_color}"/>
    <rect x="{px+11}" y="{py-11}" width="28" height="15" rx="4" fill="#0a1f3c" stroke="#1f7fe8" stroke-width="0.8"/>
    <text x="{px+25}" y="{py-3}" text-anchor="middle" dominant-baseline="central" font-family="'Segoe UI',sans-serif" font-size="10" font-weight="700" fill="{ring_color}">{s['label']}</text>
    <g class="vms-tip" opacity="0" pointer-events="none">
      <rect x="{tip_x-4}" y="{py-14}" width="{tip_w}" height="80" rx="7" fill="#0d1a2e" stroke="#1f7fe8" stroke-width="0.9"/>
      <text x="{tip_x+3}" y="{py+4}" font-family="'Segoe UI',sans-serif" font-size="11" font-weight="700" fill="#7dc3ff">{s['label']} · {s['depth']}</text>
      <text x="{tip_x+3}" y="{py+20}" font-family="'Segoe UI',sans-serif" font-size="10" fill="#a8cce8">
        VWC: <tspan font-weight="700" fill="#3dd68c">{s['vwc']} %</tspan>
        &#160;&#160;T: <tspan font-weight="700" fill="#f6a03a">{s['temp']} °C</tspan>
      </text>
      <text x="{tip_x+3}" y="{py+36}" font-family="'Segoe UI',sans-serif" font-size="10" fill="#a8cce8">
        Presión: <tspan font-weight="700" fill="#c084fc">{s['pt']} mbar</tspan>
        &#160; Nivel: <tspan font-weight="700" fill="#38bdf8">{s['dpt']} cm</tspan>
      </text>
      <text x="{tip_x+3}" y="{py+54}" font-family="'Segoe UI',sans-serif" font-size="10" fill="#4a9aaa">Clic para fijar selección →</text>
    </g>
  </g>""")

    ref_svg = f"""
  <line x1="{REF_LINE_X}" y1="{SURFACE_Y}" x2="{REF_LINE_X}" y2="{MAX_DEPTH_Y}" stroke="#38bdf8" stroke-width="1.3" stroke-dasharray="5,5" opacity="0.6"/>
  <path d="M{REF_LINE_X-4} {MAX_DEPTH_Y-8} L{REF_LINE_X} {MAX_DEPTH_Y} L{REF_LINE_X+4} {MAX_DEPTH_Y-8}" fill="none" stroke="#38bdf8" stroke-width="1.3" opacity="0.6"/>
  <text x="{REF_LINE_X-46}" y="{SURFACE_Y-8}" font-family="'Segoe UI',sans-serif" font-size="10" fill="#38bdf8" opacity="0.8">NIVEL DE</text>
  <text x="{REF_LINE_X-46}" y="{SURFACE_Y+4}" font-family="'Segoe UI',sans-serif" font-size="10" fill="#38bdf8" opacity="0.8">TERRENO</text>
"""

    ruler_marks = 7
    ruler_svg   = [f'<line x1="634" y1="{SURFACE_Y}" x2="634" y2="{MAX_DEPTH_Y}" stroke="#ffffff" stroke-width="0.5" opacity="0.25"/>']
    for i in range(ruler_marks):
        ry = SURFACE_Y + i * (MAX_DEPTH_Y - SURFACE_Y) // (ruler_marks - 1)
        current_m = (i * real_max_depth_m) / (ruler_marks - 1)
        ruler_svg.append(
            f'<line x1="628" y1="{ry}" x2="640" y2="{ry}" stroke="#ffffff" stroke-width="0.8" opacity="0.4"/>'
            f'<text x="646" y="{ry+4}" font-family="\'Segoe UI\',sans-serif" font-size="10" fill="#c8dae8" opacity="0.7">{current_m:.1f} m</text>'
        )

    sensors_json = json.dumps(sensors)

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
</style>
</head><body>
<svg viewBox="0 0 {SVG_W} {SVG_H}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="#c2dff0"/>
    <stop offset="100%" stop-color="#9ec8e4"/>
  </linearGradient>
</defs>

<rect x="0" y="0" width="{SVG_W}" height="{SURFACE_Y}" fill="url(#sky)"/>

<rect x="292" y="38" width="96" height="58" rx="8" fill="#ddeeff" stroke="#80aacc" stroke-width="1"/>
<rect x="300" y="26" width="80" height="14" rx="3" fill="#4a90d9" stroke="#2a70b9" stroke-width="0.8"/>
<text x="340" y="60" text-anchor="middle" dominant-baseline="central" font-family="'Segoe UI',sans-serif" font-size="12" font-weight="700" fill="#1a3a5c">VMS</text>
<text x="340" y="78" text-anchor="middle" font-family="'Segoe UI',sans-serif" font-size="9" fill="#3a6080">Estación</text>
<line x1="376" y1="26" x2="384" y2="12" stroke="#4a7a9a" stroke-width="1.5"/>
<circle cx="386" cy="10" r="3" fill="none" stroke="#4a9ad9" stroke-width="1.2"/>

<rect x="0" y="{SURFACE_Y}" width="{SVG_W}" height="10" fill="#9a7c48"/>

{"".join(layer_svg)}
{ref_svg}

<line x1="{CABLE_X0}" y1="{SURFACE_Y+8}" x2="{cable_ex:.1f}" y2="{cable_ey:.1f}" stroke="#2e7a2e" stroke-width="5" stroke-linecap="round" opacity="0.85"/>
<line x1="{CABLE_X0+4}" y1="{SURFACE_Y+8}" x2="{cable_ex+4:.1f}" y2="{cable_ey:.1f}" stroke="#c8a820" stroke-width="3" stroke-linecap="round" opacity="0.8"/>

{"".join(pins_svg)}
{"".join(ruler_svg)}

</svg>

<script>
const SENSORS = {sensors_json};
document.querySelectorAll('.vms-sensor').forEach(el => {{
  el.addEventListener('click', () => {{
    const idx = parseInt(el.dataset.idx);
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

# ────────────────────────────────────────────────────────────────────────
# 5. MODAL OPTIMIZADO — HISTÓRICO CON SELECTORES INTEGRADOS Y PLOTLY
# ────────────────────────────────────────────────────────────────────────
@st.dialog("📊 Histórico e Instrumentación del Sensor", width="large")
def modal_historico(id_proyecto, idx, df_data, cols_vwc, cols_temp, cols_pt, cols_dpt):
    # 1. Recuperar nombres de columnas de instrumentación correspondientes al índice
    cv = cols_vwc[idx]  if idx < len(cols_vwc)  else None
    ct = cols_temp[idx] if idx < len(cols_temp) else None
    cp = cols_pt[idx]   if idx < len(cols_pt)   else None
    cd = cols_dpt[idx]  if idx < len(cols_dpt)  else None
    prof = fmt_depth(cv) if cv else "N/A"

    # 2. CONTROLES DINÁMICOS DENTRO DEL MODAL (Evita usar la barra lateral)
    st.markdown("##### ⚙️ Configuración de Consulta")
    c_fecha, c_var = st.columns(2)
    
    with c_fecha:
        fecha_max_global = df_data['TIMESTAMP'].max().date() if 'TIMESTAMP' in df_data.columns else pd.Timestamp.now().date()
        fecha_sel = st.date_input(
            "📅 Selecciona fecha de simulación:",
            value=fecha_max_global,
            key=f"modal_date_{id_proyecto}_{idx}"
        )
        
    with c_var:
        opciones_variables = ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"]
        variable_grafico = st.selectbox(
            "📈 Variable para Tendencia Histórica:",
            options=opciones_variables,
            index=0,
            key=f"modal_var_{id_proyecto}_{idx}"
        )

    st.markdown("---")

    # 3. FILTRADO TEMPORAL DEL DATO ACTUAL (Métricas del encabezado)
    fecha_limite_kpi = pd.to_datetime(fecha_sel) + pd.Timedelta(days=1)
    df_actual = df_data[df_data['TIMESTAMP'] < fecha_limite_kpi]
    
    if not df_actual.empty:
        ultimo_registro = df_actual.iloc[-1]
        fecha_lectura_str = ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M')
    else:
        ultimo_registro = df_data.iloc[-1] if not df_data.empty else None
        fecha_lectura_str = "Sin datos para esta fecha"

    # 4. DISEÑO DEL ENCABEZADO Y TARJETAS MÉTRICAS
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1f6feb22,#388bfd11);
         border:1px solid #1f6feb44; border-radius:10px;
         padding:14px 18px; margin-bottom:12px;">
      <h3 style="margin:0;color:#58a6ff;">📡 Sensor S{idx+1} — Profundidad {prof}</h3>
      <p style="margin:0;color:#8b949e;font-size:0.85rem;">
        Estación: <b style="color:#e6edf3">{id_proyecto}</b> &nbsp;|&nbsp;
        Lectura al corte de simulación: <b style="color:#e6edf3">{fecha_lectura_str}</b>
      </p>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    if ultimo_registro is not None:
        with m1: st.metric("💧 Humedad VWC",       f"{safe_val(ultimo_registro, cv)} %"    if cv else "N/D")
        with m2: st.metric("🌡️ Temperatura",        f"{safe_val(ultimo_registro, ct, 1)} °C" if ct else "N/D")
        with m3: st.metric("⚡ Presión de Poros",   f"{safe_val(ultimo_registro, cp, 0)} mbar" if cp else "N/D")
        with m4: st.metric("📏 Nivel Hidrostático", f"{safe_val(ultimo_registro, cd, 1)} cm"  if cd else "N/D")
    else:
        st.warning("No se encontraron registros de telemetría.")

    st.markdown("---")
    st.markdown(f"#### 📊 Gráfica de Tendencia — {variable_grafico} (Ventana de 7 días hacia atrás)")

    # 5. FILTRADO PARA LA SERIE TEMPORAL (Plotly)
    fecha_max = pd.to_datetime(fecha_sel) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
    fecha_min = pd.to_datetime(fecha_sel) - pd.Timedelta(days=7)

    df_f = df_data[
        (df_data['TIMESTAMP'] >= fecha_min) &
        (df_data['TIMESTAMP'] <= fecha_max)
    ].copy()
    
    mapeo = {
        "Humedad (VWC %)":        cv,
        "Temperatura (°C)":        ct,
        "Presión de Celda (mbar)": cp,
        "Nivel (cm)":              cd,
    }
    col_obj = mapeo.get(variable_grafico)
    
    # 6. RENDERIZADO DEL GRÁFICO INTERACTIVO
    if col_obj and col_obj in df_f.columns:
        df_g = df_f[['TIMESTAMP', col_obj]].dropna().copy()
        df_g.columns = ['Fecha', variable_grafico]
        df_g['Fecha'] = pd.to_datetime(df_g['Fecha'])
        
        if not df_g.empty:
            fig = px.line(df_g, x='Fecha', y=variable_grafico, template="plotly_dark")
            fig.update_traces(line=dict(color='#388bfd', width=2.5))
            fig.update_layout(
                margin=dict(l=50, r=20, t=20, b=40),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                xaxis=dict(showgrid=True, gridcolor='#21262d', title=None, tickformat='%d %b\n%H:%M'),
                yaxis=dict(
                    showgrid=True, 
                    gridcolor='#21262d', 
                    title=None,
                    rangemode='nonnegative' if "Humedad" in variable_grafico else 'normal'
                ),
                hovermode="x unified"
            )
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
            st.dataframe(df_g, use_container_width=True, hide_index=True)

            df_export = df_g.set_index('Fecha')
            csv_bytes = df_export.to_csv().encode("utf-8")
            st.download_button(
                "⬇️ Exportar serie completa (CSV)",
                data=csv_bytes,
                file_name=f"{id_proyecto}_S{idx+1}_{col_obj}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            st.warning("⚠️ No se encontraron puntos de datos válidos en el rango de 7 días seleccionado.")
    else:
        st.error("⚠️ La variable seleccionada no está instrumentada en este sensor.")

    if st.button("Cerrar", key=f"close_hist_{id_proyecto}_{idx}", use_container_width=True):
        st.rerun()


# ─────────────────────────────────────────────
# 6. PANEL POR PROYECTO
# ─────────────────────────────────────────────
def construir_interfaz_proyecto(id_proyecto: str):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, error = cargar_datos_proyecto(id_proyecto)
    if error or df_data is None:
        st.error(error)
        return

    n         = cfg["max_sensores"]
    cols_vwc  = get_cols(df_data, "VWC",  n)
    cols_temp = get_cols(df_data, "TEMP", n)
    cols_pt   = get_cols(df_data, "PT",   n)
    cols_dpt  = get_cols(df_data, "DPT",  n)

    # El control de fecha superior ahora busca la fecha máxima del set de datos directamente
    if f"fecha_sim_{id_proyecto}" not in st.session_state:
        st.session_state[f"fecha_sim_{id_proyecto}"] = df_data['TIMESTAMP'].max().date() if not df_data.empty else pd.Timestamp.now().date()
    
    # Selector de fecha integrado de forma elegante arriba en lugar del sidebar
    fechas_disponibles = sorted(df_data['TIMESTAMP'].dt.date.unique(), reverse=True) if not df_data.empty else []
    
    col_header, col_date_pick = st.columns([2.5, 1.5])
    with col_date_pick:
        fecha_sel = st.selectbox(
            "📅 Fecha activa de simulación:",
            options=fechas_disponibles,
            key=f"sb_date_{id_proyecto}"
        )

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("⚠️ Sin registros para el día seleccionado.")
        return
    ultimo = df_dia.iloc[-1]

    key_idx = f"sensor_sel_{id_proyecto}"
    if key_idx not in st.session_state:
        st.session_state[key_idx] = 0
    sel_idx = st.session_state[key_idx]

    cv_sel = cols_vwc[sel_idx] if sel_idx < len(cols_vwc) else None
    vwc_sel_val = safe_val(ultimo, cv_sel) if cv_sel else "N/D"
    estado_general = estado_sensor(vwc_sel_val)
    pill_class = "vms-status-normal" if estado_general == "NORMAL" else "vms-status-alerta"
    ts_str = ultimo['TIMESTAMP'].strftime('%d-%m-%Y %H:%M')

    h_left, h_right = st.columns([3, 1])
    with h_left:
        st.markdown(f"""<div style="display:flex; flex-direction:column; gap:2px;"><span style="font-size:0.75rem; letter-spacing:0.08em; color:#8b949e;">{cfg['nombre_estacion']}</span><span style="font-size:1.6rem; font-weight:800; color:#e6edf3;">ESTACIÓN VMS {cfg['angle_deg']:.0f}°</span><span style="font-size:0.85rem; color:#58a6ff; letter-spacing:0.05em;">PERFIL DE MONITOREO — {id_proyecto}</span></div>""", unsafe_allow_html=True)
    with h_right:
        st.markdown(f"""<div class="vms-card" style="text-align:center; margin-bottom:0;"><div style="font-size:0.7rem; color:#8b949e; letter-spacing:0.05em;">ESTADO GENERAL</div><span class="vms-status-pill {pill_class}">{estado_general}</span><div style="font-size:0.68rem; color:#8b949e; margin-top:6px;">Última actualización:<br>{ts_str}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_izq, col_centro, col_der = st.columns([1.1, 1.7, 1.1])

    with col_izq:
        filas_html = []
        for i in range(n):
            cv = cols_vwc[i] if i < len(cols_vwc) else None
            prof = fmt_depth(cv) if cv else "N/A"
            vwc  = safe_val(ultimo, cv) if cv else "N/D"
            badge_cls = "vms-badge vms-badge-selected" if i == sel_idx else "vms-badge"
            filas_html.append(f'<div class="vms-sensor-row"><div style="display:flex; align-items:center;"><span class="{badge_cls}">S{i+1}</span><span class="vms-sensor-meta">Profundidad: <b>{prof}</b><br>VWC: <b>{vwc} %</b></span></div></div>')
        
        html_card_sensores = f'<div class="vms-card"><h4>📡 SENSORES INSTALADOS</h4>{"".join(filas_html)}</div>'
        st.markdown(html_card_sensores, unsafe_allow_html=True)

        botones_cols = st.columns(min(4, n))
        for i in range(n):
            with botones_cols[i % len(botones_cols)]:
                if st.button(f"S{i+1}", key=f"sel_{id_proyecto}_{i}", use_container_width=True):
                    st.session_state[key_idx] = i
                    st.rerun()

        st.markdown("""<div class="vms-card"><h4>🔎 SIMBOLOGÍA</h4><div class="vms-legend-row"><span class="vms-legend-icon">💧</span> Humedad volumétrica (VWC)</div><div class="vms-legend-row"><span class="vms-legend-icon">🌡️</span> Temperatura del suelo</div><div class="vms-legend-row"><span class="vms-legend-icon">⚡</span> Presión de poros / celda</div><div class="vms-legend-row"><span class="vms-legend-icon">📏</span> Nivel hidrostático</div><div class="vms-legend-row"><span class="vms-legend-icon">┄</span> Profundidad vertical de referencia</div></div>""", unsafe_allow_html=True)

    with col_centro:
        st.caption("Pasa el cursor sobre un sensor para ver sus datos rápidos · Usa los botones S1-S8 para fijar la telemetría")
        html_code = render_soil_profile(
            id_proyecto, cfg, cols_vwc, cols_temp, cols_pt, cols_dpt,
            ultimo, selected_idx=sel_idx,
        )
        st.components.v1.html(html_code, height=660, scrolling=False)
        st.markdown("""<div style="font-size:0.72rem; color:#6e7681; text-align:center; margin-top:6px;">ℹ️ Las profundidades indicadas corresponden a la distancia medida a lo largo del eje del pozo (inclinación indicada).</div>""", unsafe_allow_html=True)

    with col_der:
        cv = cols_vwc[sel_idx]  if sel_idx < len(cols_vwc)  else None
        ct = cols_temp[sel_idx] if sel_idx < len(cols_temp) else None
        cp = cols_pt[sel_idx]   if sel_idx < len(cols_pt)   else None
        cd = cols_dpt[sel_idx]  if sel_idx < len(cols_dpt)  else None
        prof = fmt_depth(cv) if cv else "N/A"

        st.markdown(f"""<div class="vms-card"><h4>ℹ️ INFORMACIÓN DEL SENSOR</h4><div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;"><span class="vms-badge vms-badge-selected">S{sel_idx+1}</span><span style="font-weight:700; color:#e6edf3;">Sensor S{sel_idx+1}</span></div><div class="vms-detail-row"><span>Profundidad</span><span>{prof}</span></div><div class="vms-detail-row"><span>Humedad (VWC)</span><span>{safe_val(ultimo, cv) if cv else 'N/D'} %</span></div><div class="vms-detail-row"><span>Temperatura</span><span>{safe_val(ultimo, ct, 1) if ct else 'N/D'} °C</span></div><div class="vms-detail-row"><span>Presión de poros</span><span>{safe_val(ultimo, cp, 0) if cp else 'N/D'} mbar</span></div><div class="vms-detail-row"><span>Nivel hidrostático</span><span>{safe_val(ultimo, cd, 1) if cd else 'N/D'} cm</span></div><div class="vms-detail-row"><span>Última lectura</span><span>{ts_str}</span></div><div class="vms-detail-row"><span>Estado</span><span class="vms-status-pill {pill_class}" style="padding:1px 8px;">{estado_general}</span></div></div>""", unsafe_allow_html=True)

        b1, b2 = st.columns(2)
        with b1:
            if st.button("📈 Ver Histórico", key=f"hist_{id_proyecto}", use_container_width=True):
                modal_historico(
                    id_proyecto=id_proyecto,
                    idx=sel_idx,
                    df_data=df_data,
                    cols_vwc=cols_vwc,
                    cols_temp=cols_temp,
                    cols_pt=cols_pt,
                    cols_dpt=cols_dpt
                )
        with b2:
            fila_export = ultimo[[c for c in [cv, ct, cp, cd, 'TIMESTAMP'] if c]]
            st.download_button(
                "⬇️ Exportar día",
                data=pd.DataFrame([fila_export]).to_csv(index=False).encode("utf-8"),
                file_name=f"{id_proyecto}_S{sel_idx+1}_{fecha_sel}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        st.markdown(f"""<div class="vms-card"><h4>🏗️ DETALLES DEL POZO</h4><div class="vms-detail-row"><span>Inclinación</span><span>{cfg['angle_deg']:.0f}°</span></div><div class="vms-detail-row"><span>N° de sensores</span><span>{n}</span></div><div class="vms-detail-row"><span>Diámetro perforación</span><span>{cfg['diametro_perforacion']}</span></div><div class="vms-detail-row"><span>Tipo de instalación</span><span>{cfg['tipo_instalacion']}</span></div><div class="vms-detail-row"><span>Fecha instalación</span><span>{cfg['fecha_instalacion']}</span></div></div>""", unsafe_allow_html=True)

    with st.expander("📊 Ver tabla completa de sensores"):
        resumen = []
        for i in range(n):
            resumen.append({
                "Sensor":         f"S{i+1}",
                "Profundidad":    fmt_depth(cols_vwc[i]) if i < len(cols_vwc) else "N/A",
                "VWC (%)":        safe_val(ultimo, cols_vwc[i])  if i < len(cols_vwc)  else "N/D",
                "Temp (°C)":      safe_val(ultimo, cols_temp[i], 1) if i < len(cols_temp) else "N/D",
                "Presión (mbar)": safe_val(ultimo, cols_pt[i], 0)  if i < len(cols_pt)   else "N/D",
                "Nivel (cm)":      safe_val(ultimo, cols_dpt[i], 1)  if i < len(cols_dpt)  else "N/D",
            })
        st.dataframe(pd.DataFrame(resumen), use_container_width=True, hide_index=True)

# ─────────────────────────────────────────────
# 7. PESTAÑAS PRINCIPALES
# ─────────────────────────────────────────────
tab_drf, tab_romeral = st.tabs([
    "📍 Estación DRF",
    "📍 Estación El Romeral",
])

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
