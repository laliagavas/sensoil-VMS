import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import os
import json

# ─────────────────────────────────────────────
# 1. CONFIGURACIÓN GLOBAL
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="VMS GeoCloud - SENSOIL Demo Comercial",
    page_icon="🌍",
    layout="wide"
)

# Inyección de CSS global para la UI premium
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
# 2. CONFIGURACIÓN DE PROYECTOS Y SENSORES
# ─────────────────────────────────────────────
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "Romeral.csv",
        "csv_rain": "RomeralRain.csv",
        "imagen": "DRF.jpg",
        "lat": -28.493772,
        "lon": -71.254531,
        "max_sensores": 7,
        "pin_coords": [
            (60.2, 42.7),  # S1
            (55.5, 51.9),
            (51.2, 59.3),
            (46.8, 68.3),
            (42.3, 76.2),
            (38.0, 83.8),
            (33.2, 93.4)   # S7
        ]
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv",
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg",
        "lat": -29.726153,
        "lon": -71.221878,
        "max_sensores": 8,
        "pin_coords": [
             (64.3, 38.5),  # S1
             (60.5, 46.1),
             (56.6, 53.9),
             (52.5, 62.1),
             (48.5, 70.2),
             (44.4, 77.8),
             (41.2, 84.9),
             (37.0, 93.3)   # S8
        ]
    }
}

# ─────────────────────────────────────────────
# 3. UTILIDADES
# ─────────────────────────────────────────────
def get_base64_image(image_path: str) -> str:
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    return ""

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

def formatear_profundidad(col_name: str) -> str:
    try:
        parts = col_name.split('_')
        if len(parts) > 2:
            cm_str = parts[2].replace('cm', '')
            return f"{float(cm_str) / 100:.1f}m"
    except Exception:
        pass
    return "N/A"

def get_cols(df, prefix, n):
    cols = sorted(
        [c for c in df.columns if c.startswith(f"{prefix}_")],
        key=lambda x: int(x.split('_')[1]) if len(x.split('_')) > 1 and x.split('_')[1].isdigit() else 0
    )
    return cols[:n]

# ─────────────────────────────────────────────
# 4. COMPONENTE HTML BIDIRECCIONAL REFINADO
# ─────────────────────────────────────────────
def render_imagen_con_pines(id_proyecto: str, img_b64: str, pin_coords: list, cols_vwc: list, ultimo_registro):
    pins_js = []
    for i, (left_pct, top_pct) in enumerate(pin_coords):
        prof = formatear_profundidad(cols_vwc[i]) if i < len(cols_vwc) else "N/A"
        vwc_val = f"{ultimo_registro.get(cols_vwc[i], 0.0):.1f}%" if i < len(cols_vwc) else "N/A"
        pins_js.append({
            "idx": i,
            "left": left_pct,
            "top": top_pct,
            "label": f"S{i+1}",
            "prof": prof,
            "vwc": vwc_val,
        })

    pins_json = json.dumps(pins_js)
    
    # Inyección directa del script de comunicación nativa de Streamlit
    html_component = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background: transparent; font-family: 'Segoe UI', sans-serif; overflow: hidden; }}
        .wrapper {{ position: relative; display: inline-block; width: 100%; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 32px rgba(0,0,0,0.5); }}
        .pozo-img {{ width: 100%; display: block; border-radius: 12px; }}
        .pin {{ position: absolute; transform: translate(-50%, -100%); cursor: pointer; border: none; background: transparent; padding: 0; z-index: 10; opacity: 1; }}
        .pin-inner {{ display: flex; flex-direction: column; align-items: center; gap: 0; }}
        .pin-bubble {{ background: linear-gradient(135deg, #1f6feb, #388bfd); color: white; border-radius: 8px 8px 8px 0; padding: 4px 8px; font-size: 11px; font-weight: 700; white-space: nowrap; box-shadow: 0 3px 12px rgba(31,111,235,0.6); transition: all 0.2s ease; line-height: 1.3; text-align: center; }}
        .pin-stem {{ width: 2px; height: 10px; background: #388bfd; }}
        .pin-dot {{ width: 8px; height: 8px; background: #58a6ff; border-radius: 50%; box-shadow: 0 0 8px rgba(88,166,255,0.8); }}
        .pin:hover .pin-bubble {{ background: linear-gradient(135deg, #388bfd, #79c0ff); transform: scale(1.05); }}
        
        .pin-tooltip {{ position: absolute; bottom: calc(100% + 8px); left: 50%; transform: translateX(-50%); background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 6px 10px; font-size: 11px; color: #e6edf3; white-space: nowrap; pointer-events: none; opacity: 0; transition: opacity 0.2s ease; z-index: 20; }}
        .pin:hover .pin-tooltip {{ opacity: 1; }}
        .pin-tooltip span {{ color: #58a6ff; font-weight: 700; }}
    </style>
    </head>
    <body>

    <div class="wrapper" id="wrapper">
        <img class="pozo-img" src="data:image/jpeg;base64,{img_b64}" id="pozo-img" />
    </div>

    <script src="https://cdn.jsdelivr.net/npm/streamlit-component-lib@1.4.0/dist/streamlit-component-lib.js"></script>
    <script>
    const PINS = {pins_json};

    function sendMessageToStreamlit(sensorIdx) {{
        // Envía de forma segura el índice del sensor a Python usando la API oficial
        Streamlit.setComponentValue(sensorIdx);
    }}

    function buildPins() {{
        const wrapper = document.getElementById('wrapper');
        PINS.forEach((p) => {{
            const btn = document.createElement('button');
            btn.className = 'pin';
            btn.id = 'pin-' + p.idx;
            btn.style.cssText = `left:${{p.left}}%; top:${{p.top}}%;`;
            btn.innerHTML = `
                <div class="pin-inner">
                    <div class="pin-tooltip">
                        <span>${{p.label}}</span> · ${{p.prof}} · VWC: <span>${{p.vwc}}</span>
                    </div>
                    <div class="pin-bubble">${{p.label}}<br/><small style="font-weight:400;font-size:9px">${{p.prof}}</small></div>
                    <div class="pin-stem"></div>
                    <div class="pin-dot"></div>
                </div>
            `;
            btn.addEventListener('click', (e) => {{
                e.preventDefault();
                sendMessageToStreamlit(p.idx);
            }});
            wrapper.appendChild(btn);
        }});
        
        // Ajusta la altura del iframe en Streamlit de forma dinámica
        setTimeout(() => {{
            Streamlit.setFrameHeight(document.getElementById('wrapper').offsetHeight);
        }}, 150);
    }}

    const img = document.getElementById('pozo-img');
    if (img.complete) {{ buildPins(); }}
    else {{ img.addEventListener('load', buildPins); }}
    </script>
    </body>
    </html>
    """
    return html_component


# ─────────────────────────────────────────────
# 5. MODAL DE SENSOR (Métricas e Histórico)
# ─────────────────────────────────────────────
@st.dialog("📊 Análisis de Sensor", width="large")
def modal_sensor(id_proyecto: str, idx: int, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt, fecha_sel, variable_grafico: str):
    c_vwc  = cols_vwc[idx]  if idx < len(cols_vwc)  else None
    c_temp = cols_temp[idx] if idx < len(cols_temp) else None
    c_pt   = cols_pt[idx]   if idx < len(cols_pt)   else None
    c_dpt  = cols_dpt[idx]  if idx < len(cols_dpt)  else None
    prof   = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1f6feb22,#388bfd11); border:1px solid #1f6feb44; border-radius:10px; padding:14px 18px; margin-bottom:12px;">
        <h3 style="margin:0;color:#58a6ff;">📡 Sensor S{idx+1} — Profundidad {prof}</h3>
        <p style="margin:0;color:#8b949e;font-size:0.85rem;">
            Estación: <b style="color:#e6edf3">{id_proyecto}</b> &nbsp;|&nbsp;
            Registro: <b style="color:#e6edf3">{ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M')}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("💧 Humedad VWC", f"{ultimo_registro.get(c_vwc, 0.0):.2f} %" if c_vwc else "N/D")
    with m2: st.metric("🌡️ Temperatura", f"{ultimo_registro.get(c_temp, 0.0):.1f} °C" if c_temp else "N/D")
    with m3: st.metric("⚡ Presión de Poros", f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar" if c_pt else "N/D")
    with m4: st.metric("📏 Nivel Hidrostático", f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm" if c_dpt else "N/D")

    st.markdown("---")
    st.markdown(f"#### 📈 Tendencia — {variable_grafico} (últimos 7 días)")

    fecha_max = pd.Timestamp(fecha_sel)
    fecha_min = fecha_max - pd.Timedelta(days=7)
    df_f = df_data[(df_data['TIMESTAMP'] >= fecha_min) & (df_data['TIMESTAMP'] <= fecha_max + pd.Timedelta(days=1))]

    mapeo = {"Humedad (VWC %)": c_vwc, "Temperatura (°C)": c_temp, "Presión de Celda (mbar)": c_pt, "Nivel (cm)": c_dpt}
    col_obj = mapeo.get(variable_grafico)
    
    if col_obj and col_obj in df_f.columns:
        df_g = df_f[['TIMESTAMP', col_obj]].copy()
        df_g.columns = ['Fecha', f"S{idx+1} ({prof})"]
        df_g.set_index('Fecha', inplace=True)
        st.line_chart(df_g, use_container_width=True)

    if st.button("✖ Volver a Radiografía", key=f"close_sens_{id_proyecto}_{idx}"):
        st.session_state[f"sensor_modal_{id_proyecto}"] = None
        st.rerun()


# ─────────────────────────────────────────────
# 6. MODAL DE RADIOGRAFÍA (Conexión Bidireccional Segura)
# ─────────────────────────────────────────────
@st.dialog("🏗️ Radiografía del Pozo", width="large")
def modal_radiografia(id_proyecto: str, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt, fecha_sel, variable_grafico: str):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    img_b64 = get_base64_image(cfg["imagen"])

    st.markdown(f"""
    <p style="color:#8b949e;font-size:0.85rem;margin-bottom:8px;">
        📍 Estación <b style="color:#58a6ff">{id_proyecto}</b> &nbsp;·&nbsp; {cfg['max_sensores']} sensores activos &nbsp;·&nbsp; Haz clic sobre los pines de la imagen.
    </p>
    """, unsafe_allow_html=True)

    if not img_b64:
        st.error(f"⚠️ Imagen no encontrada: {cfg['imagen']}")
    else:
        html_code = render_imagen_con_pines(id_proyecto, img_b64, cfg["pin_coords"], cols_vwc, ultimo_registro)
        
        # Almacenamos el índice que retorna el iframe al ser clickeado de forma nativa
        click_index = st.components.v1.html(html_code, height=580, scrolling=False)
        
        # CAPTURA DINÁMICA: Si el usuario presionó un pin, mutamos el estado e invocamos rerun
        if click_index is not None:
            st.session_state[f"sensor_modal_{id_proyecto}"] = int(click_index)
            st.rerun()

    st.markdown("---")
    st.markdown("##### 🎯 Acceso Rápido por Botones:")
    cols_btns = st.columns(cfg["max_sensores"])
    for i, col in enumerate(cols_btns):
        with col:
            prof = formatear_profundidad(cols_vwc[i]) if i < len(cols_vwc) else ""
            if st.button(f"S{i+1}\n{prof}", key=f"quick_{id_proyecto}_{i}", use_container_width=True):
                st.session_state[f"sensor_modal_{id_proyecto}"] = i
                st.rerun()


# ─────────────────────────────────────────────
# 7. SIDEBAR (Filtros de control)
# ─────────────────────────────────────────────
with st.sidebar:
    st.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=130)
    st.markdown("## VMS GeoCloud")
    st.markdown("---")

    df_aux, err_aux = cargar_datos_proyecto("ROMERAL")
    fechas_sim = sorted(df_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_aux is not None else []

    fecha_sel = st.selectbox("📅 Fecha de simulación:", fechas_sim, key="global_fecha_sel")
    variable_grafico = st.selectbox("📈 Variable histórica:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key="global_var_sel")


# ─────────────────────────────────────────────
# 8. INTERFAZ PRINCIPAL Y MAPAS
# ─────────────────────────────────────────────
def construir_interfaz_proyecto(id_proyecto: str):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, error = cargar_datos_proyecto(id_proyecto)

    if error or df_data is None:
        st.error(error)
        return

    num_sens = cfg["max_sensores"]
    cols_vwc  = get_cols(df_data, "VWC",  num_sens)
    cols_temp = get_cols(df_data, "TEMP", num_sens)
    cols_pt   = get_cols(df_data, "PT",   num_sens)
    cols_dpt  = get_cols(df_data, "DPT",  num_sens)

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("⚠️ Sin datos para la fecha seleccionada.")
        return
    ultimo_registro = df_dia.iloc[-1]

    st.markdown(f"### 🗺️ Monitoreo Satelital — <span style='color:#58a6ff'>{id_proyecto}</span>", unsafe_allow_html=True)
    st.caption("Haz clic en el marcador azul del mapa para desplegar la radiografía estructural interactiva.")

    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satelital', control=False).add_to(m)
    folium.Marker([cfg["lat"], cfg["lon"]], tooltip=f"Ver Radiografía {id_proyecto}", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

    mapa_output = st_folium(m, width="100%", height=400, key=f"mapa_{id_proyecto}")

    if mapa_output and mapa_output.get("last_object_clicked"):
        st.session_state[f"abrir_radio_{id_proyecto}"] = True

    # Despliegue seguro de modales controlados por estado de sesión
    if st.session_state.get(f"abrir_radio_{id_proyecto}"):
        # Apagamos el flag inmediatamente para evitar bucles de renderizado al interactuar
        st.session_state[f"abrir_radio_{id_proyecto}"] = False
        modal_radiografia(id_proyecto, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt, fecha_sel, variable_grafico)

    sensor_idx = st.session_state.get(f"sensor_modal_{id_proyecto}")
    if sensor_idx is not None:
        modal_sensor(id_proyecto, sensor_idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt, fecha_sel, variable_grafico)

    # Tabla compacta inferior de estado actual
    st.markdown("##### 📊 Estado Actual de Sensores")
    data_resumen = []
    for i in range(num_sens):
        prof = formatear_profundidad(cols_vwc[i]) if i < len(cols_vwc) else "N/A"
        data_resumen.append({
            "Sensor": f"S{i+1}", "Profundidad": prof,
            "VWC (%)": f"{ultimo_registro.get(cols_vwc[i], 0.0):.2f}" if i < len(cols_vwc) else "N/D",
            "Temp (°C)": f"{ultimo_registro.get(cols_temp[i], 0.0):.1f}" if i < len(cols_temp) else "N/D",
            "Presión (mbar)": f"{ultimo_registro.get(cols_pt[i], 0.0):.0f}" if i < len(cols_pt) else "N/D",
            "Nivel (cm)": f"{ultimo_registro.get(cols_dpt[i], 0.0):.1f}" if i < len(cols_dpt) else "N/D"
        })
    st.dataframe(pd.DataFrame(data_resumen), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────
# 9. CONTROL DE PESTAÑAS
# ─────────────────────────────────────────────
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
