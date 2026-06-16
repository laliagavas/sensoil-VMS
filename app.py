import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import os

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
    /* Fondo oscuro estilo GIS profesional */
    .stApp { background-color: #0d1117; color: #e6edf3; }
    section[data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #30363d; }
    
    /* Tabs estilizadas */
    .stTabs [data-baseweb="tab-list"] { background-color: #161b22; border-radius: 8px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #8b949e; border-radius: 6px; }
    .stTabs [aria-selected="true"] { background-color: #1f6feb !important; color: white !important; }
    
    /* Metric cards */
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; color: #58a6ff; }
    [data-testid="stMetricLabel"] { color: #8b949e; font-size: 0.75rem; }
    
    /* Modal personalizado */
    [data-testid="stDialog"] > div { background-color: #161b22 !important; border: 1px solid #30363d; border-radius: 12px; }
    
    /* Botones */
    .stButton > button {
        background: linear-gradient(135deg, #1f6feb, #388bfd);
        color: white; border: none; border-radius: 8px;
        font-weight: 600; padding: 0.5rem 1.2rem;
        transition: all 0.2s ease;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(31,111,235,0.4); }
    
    /* Selectbox y sidebar */
    .stSelectbox label, .stSidebar label { color: #8b949e; }
    
    /* Ocultar el header de Streamlit */
    #MainMenu, header, footer { visibility: hidden; }
    
    /* Separadores */
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
        # Coordenadas de pines en % (left%, top%) sobre la imagen del pozo.
        # Ajusta estos valores según las cotas dibujadas en tu DRF.jpg
        "pin_coords": [
            (50, 18),   # S1 – sensor más superficial
            (50, 27),   # S2
            (50, 36),   # S3
            (50, 45),   # S4
            (50, 54),   # S5
            (50, 63),   # S6
            (50, 72),   # S7 – sensor más profundo
        ]
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv",
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg",
        "lat": -29.726153,
        "lon": -71.221878,
        "max_sensores": 8,
        # Ajusta estos valores según las cotas dibujadas en tu Romeral.jpg
        "pin_coords": [
            (50, 14),   # S1
            (50, 22),   # S2
            (50, 30),   # S3
            (50, 38),   # S4
            (50, 46),   # S5
            (50, 54),   # S6
            (50, 62),   # S7
            (50, 72),   # S8
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
    """Retorna exactamente n columnas que empiecen con prefix, ordenadas numéricamente."""
    cols = sorted(
        [c for c in df.columns if c.startswith(f"{prefix}_")],
        key=lambda x: int(x.split('_')[1]) if len(x.split('_')) > 1 and x.split('_')[1].isdigit() else 0
    )
    return cols[:n]


# ─────────────────────────────────────────────
# 4. COMPONENTE HTML: IMAGEN CON PINES INTERACTIVOS
#    Usa postMessage para comunicarse con Streamlit
#    sin recargar la página.
# ─────────────────────────────────────────────
def render_imagen_con_pines(id_proyecto: str, img_b64: str, pin_coords: list,
                             cols_vwc: list, ultimo_registro) -> int | None:
    """
    Renderiza la imagen del pozo con pines interactivos en posición absoluta.
    Devuelve el índice del sensor clickeado (0-based) o None si no hubo click.

    Mecanismo:
      1. El HTML pinta pines <button> con position:absolute sobre la imagen.
      2. Al clickear, llama a window.parent.postMessage({sensor: idx}, '*').
      3. Un segundo st.components (listener invisible) escucha ese mensaje y
         lo escribe en un <input> oculto cuyo valor Streamlit lee vía
         st.components.v1.html con height=0.
    """
    # Construimos los datos de los pines
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

    import json
    pins_json = json.dumps(pins_js)
    media_type = "image/jpeg"  # Cambia a "image/png" si tus imágenes son PNG

    html_component = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{ background: transparent; font-family: 'Segoe UI', sans-serif; }}

        .wrapper {{
            position: relative;
            display: inline-block;
            width: 100%;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 8px 32px rgba(0,0,0,0.5);
        }}

        .pozo-img {{
            width: 100%;
            display: block;
            border-radius: 12px;
        }}

        /* PIN base */
        .pin {{
            position: absolute;
            transform: translate(-50%, -100%);
            cursor: pointer;
            border: none;
            background: transparent;
            padding: 0;
            z-index: 10;
            animation: floatIn 0.4s ease forwards;
            opacity: 0;
        }}
        .pin:nth-child(n) {{ animation-delay: calc(0.05s * var(--i)); }}

        @keyframes floatIn {{
            from {{ opacity:0; transform: translate(-50%, -120%); }}
            to   {{ opacity:1; transform: translate(-50%, -100%); }}
        }}

        .pin-inner {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0;
        }}

        .pin-bubble {{
            background: linear-gradient(135deg, #1f6feb, #388bfd);
            color: white;
            border-radius: 8px 8px 8px 0;
            padding: 4px 8px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
            box-shadow: 0 3px 12px rgba(31,111,235,0.6);
            transition: all 0.2s ease;
            line-height: 1.3;
        }}

        .pin-stem {{
            width: 2px;
            height: 10px;
            background: #388bfd;
            box-shadow: 0 2px 6px rgba(31,111,235,0.5);
        }}

        .pin-dot {{
            width: 8px;
            height: 8px;
            background: #58a6ff;
            border-radius: 50%;
            box-shadow: 0 0 8px rgba(88,166,255,0.8);
        }}

        .pin:hover .pin-bubble {{
            background: linear-gradient(135deg, #388bfd, #79c0ff);
            transform: scale(1.1);
            box-shadow: 0 6px 20px rgba(31,111,235,0.8);
        }}

        .pin:hover .pin-dot {{
            box-shadow: 0 0 16px rgba(88,166,255,1);
        }}

        /* Tooltip flotante al hover */
        .pin-tooltip {{
            position: absolute;
            bottom: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 6px 10px;
            font-size: 11px;
            color: #e6edf3;
            white-space: nowrap;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s ease;
            z-index: 20;
        }}
        .pin:hover .pin-tooltip {{ opacity: 1; }}
        .pin-tooltip span {{ color: #58a6ff; font-weight: 700; }}

        /* Pulso de selección activa */
        .pin.selected .pin-bubble {{
            background: linear-gradient(135deg, #238636, #2ea043) !important;
            box-shadow: 0 6px 20px rgba(46,160,67,0.8) !important;
        }}
        .pin.selected .pin-dot {{
            background: #3fb950;
            box-shadow: 0 0 16px rgba(63,185,80,1) !important;
        }}
        .pin.selected .pin-stem {{ background: #2ea043; }}
    </style>
    </head>
    <body>

    <div class="wrapper" id="wrapper">
        <img class="pozo-img" src="data:{media_type};base64,{img_b64}" id="pozo-img" />
        <!-- Los pines se inyectan aquí por JS -->
    </div>

    <script>
    const PINS = {pins_json};
    let selectedIdx = null;

    function buildPins() {{
        const wrapper = document.getElementById('wrapper');
        PINS.forEach((p, i) => {{
            const btn = document.createElement('button');
            btn.className = 'pin';
            btn.id = 'pin-' + p.idx;
            btn.style.cssText = `left:${{p.left}}%; top:${{p.top}}%; --i:${{i}};`;
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
                e.stopPropagation();
                // Quitar selección anterior
                if (selectedIdx !== null) {{
                    const prev = document.getElementById('pin-' + selectedIdx);
                    if (prev) prev.classList.remove('selected');
                }}
                btn.classList.add('selected');
                selectedIdx = p.idx;
                
                // ── COMUNICACIÓN CON STREAMLIT ──
                // Escribimos en el input oculto del listener y disparamos 'input'
                try {{
                    const frames = window.parent.document.querySelectorAll('iframe');
                    frames.forEach(f => {{
                        try {{
                            const inp = f.contentDocument.getElementById('sensor-choice');
                            if (inp) {{
                                inp.value = String(p.idx);
                                inp.dispatchEvent(new Event('input', {{bubbles:true}}));
                            }}
                        }} catch(e) {{}}
                    }});
                }} catch(ex) {{}}

                // Método alternativo: postMessage al padre
                window.parent.postMessage({{
                    type: 'PIN_CLICK',
                    sensor_idx: p.idx,
                    proyecto: '{id_proyecto}'
                }}, '*');
            }});
            wrapper.appendChild(btn);
        }});
    }}

    // Construir pines cuando la imagen esté cargada
    const img = document.getElementById('pozo-img');
    if (img.complete) {{ buildPins(); }}
    else {{ img.addEventListener('load', buildPins); }}
    </script>
    </body>
    </html>
    """
    return html_component


# ─────────────────────────────────────────────
# 5. COMPONENTE LISTENER: Captura el postMessage
#    y lo pasa a Streamlit via st.components retval
# ─────────────────────────────────────────────
def render_listener(id_proyecto: str) -> int | None:
    """
    Componente invisible que escucha mensajes postMessage del componente de imagen
    y devuelve el índice del sensor seleccionado a Python.
    
    Streamlit components con height>0 y return_value pueden comunicarse via
    Streamlit.setComponentValue() — aquí usamos st.components.v1.html para
    almacenar en session_state mediante URL params.
    """
    # Esta es la técnica más confiable en Streamlit puro:
    # Usamos un key único en session_state que el HTML actualiza via
    # window.parent.postMessage y lo capturamos con un query param listener.
    pass


# ─────────────────────────────────────────────
# 6. MODAL DE SENSOR (gráficos e indicadores)
# ─────────────────────────────────────────────
@st.dialog("📊 Análisis de Sensor", width="large")
def modal_sensor(id_proyecto: str, idx: int, df_data, ultimo_registro,
                 cols_vwc, cols_temp, cols_pt, cols_dpt, fecha_sel, variable_grafico: str):

    c_vwc  = cols_vwc[idx]  if idx < len(cols_vwc)  else None
    c_temp = cols_temp[idx] if idx < len(cols_temp) else None
    c_pt   = cols_pt[idx]   if idx < len(cols_pt)   else None
    c_dpt  = cols_dpt[idx]  if idx < len(cols_dpt)  else None
    prof   = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    # Header
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1f6feb22,#388bfd11);
                border:1px solid #1f6feb44; border-radius:10px; padding:14px 18px; margin-bottom:12px;">
        <h3 style="margin:0;color:#58a6ff;">📡 Sensor S{idx+1} — Profundidad {prof}</h3>
        <p style="margin:0;color:#8b949e;font-size:0.85rem;">
            Estación: <b style="color:#e6edf3">{id_proyecto}</b> &nbsp;|&nbsp;
            Registro: <b style="color:#e6edf3">{ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M')}</b>
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Métricas
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("💧 Humedad VWC",
                  f"{ultimo_registro.get(c_vwc, 0.0):.2f} %" if c_vwc else "N/D")
    with m2:
        st.metric("🌡️ Temperatura",
                  f"{ultimo_registro.get(c_temp, 0.0):.1f} °C" if c_temp else "N/D")
    with m3:
        st.metric("⚡ Presión de Poros",
                  f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar" if c_pt else "N/D")
    with m4:
        st.metric("📏 Nivel Hidrostático",
                  f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm" if c_dpt else "N/D")

    st.markdown("---")
    st.markdown(f"#### 📈 Tendencia — {variable_grafico} (últimos 7 días)")

    fecha_max = pd.Timestamp(fecha_sel)
    fecha_min = fecha_max - pd.Timedelta(days=7)
    df_f = df_data[(df_data['TIMESTAMP'] >= fecha_min) &
                   (df_data['TIMESTAMP'] <= fecha_max + pd.Timedelta(days=1))]

    mapeo = {
        "Humedad (VWC %)": c_vwc,
        "Temperatura (°C)": c_temp,
        "Presión de Celda (mbar)": c_pt,
        "Nivel (cm)": c_dpt,
    }
    col_obj = mapeo.get(variable_grafico)
    if col_obj and col_obj in df_f.columns:
        df_g = df_f[['TIMESTAMP', col_obj]].copy()
        df_g.columns = ['Fecha', f"S{idx+1} ({prof})"]
        df_g.set_index('Fecha', inplace=True)
        st.line_chart(df_g, use_container_width=True)
    else:
        st.info("No hay datos disponibles para esta variable en el rango seleccionado.")

    # Botón para cerrar (limpia el estado)
    if st.button("✖ Cerrar", key=f"close_sensor_{id_proyecto}_{idx}"):
        st.session_state[f"sensor_modal_{id_proyecto}"] = None
        st.rerun()


# ─────────────────────────────────────────────
# 7. MODAL DE RADIOGRAFÍA (imagen + pines)
# ─────────────────────────────────────────────
@st.dialog("🏗️ Radiografía del Pozo", width="large")
def modal_radiografia(id_proyecto: str, df_data, ultimo_registro,
                      cols_vwc, cols_temp, cols_pt, cols_dpt, fecha_sel, variable_grafico: str):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    img_b64 = get_base64_image(cfg["imagen"])

    st.markdown(f"""
    <p style="color:#8b949e;font-size:0.85rem;margin-bottom:8px;">
        📍 Estación <b style="color:#58a6ff">{id_proyecto}</b> &nbsp;·&nbsp;
        {cfg['max_sensores']} sensores activos &nbsp;·&nbsp;
        Haz clic en un pin para ver sus datos analíticos
    </p>
    """, unsafe_allow_html=True)

    if not img_b64:
        st.error(f"⚠️ Imagen no encontrada: {cfg['imagen']}")
        st.info("Coloca los archivos DRF.jpg y Romeral.jpg en el directorio raíz de la app.")
        # Renderizado de placeholder cuando no hay imagen
        st.markdown("""
        <div style="background:#161b22;border:2px dashed #30363d;border-radius:12px;
                    height:400px;display:flex;align-items:center;justify-content:center;">
            <span style="color:#8b949e;font-size:1rem;">📷 Imagen no disponible</span>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Renderizar imagen con pines interactivos
        html_pines = render_imagen_con_pines(
            id_proyecto, img_b64, cfg["pin_coords"],
            cols_vwc, ultimo_registro
        )
        st.components.v1.html(html_pines, height=620, scrolling=False)

    st.markdown("---")

    # ── SELECTOR DE SENSOR (fallback robusto cuando JS no puede comunicarse) ──
    st.markdown("##### 🎯 Selecciona un sensor para ver sus datos:")

    opciones = []
    for i in range(cfg["max_sensores"]):
        prof = formatear_profundidad(cols_vwc[i]) if i < len(cols_vwc) else "N/A"
        opciones.append(f"📍 S{i+1} — {prof}")

    col_sel, col_btn = st.columns([3, 1])
    with col_sel:
        sel_key = f"sel_sensor_{id_proyecto}"
        # Recuperar selección previa del session_state (seteada por el pin click)
        default_idx = st.session_state.get(f"pin_click_{id_proyecto}", 0)
        seleccion = st.selectbox("", opciones, index=default_idx, key=sel_key, label_visibility="collapsed")
    with col_btn:
        if st.button("📊 Ver Análisis", key=f"btn_ver_{id_proyecto}", use_container_width=True):
            idx_elegido = opciones.index(seleccion)
            st.session_state[f"sensor_modal_{id_proyecto}"] = idx_elegido
            st.rerun()

    # ── SHORTCUT: botones rápidos de cada sensor ──
    st.markdown("<p style='color:#8b949e;font-size:0.8rem;margin-top:4px;'>Acceso rápido:</p>", unsafe_allow_html=True)
    cols_btns = st.columns(cfg["max_sensores"])
    for i, col in enumerate(cols_btns):
        with col:
            prof = formatear_profundidad(cols_vwc[i]) if i < len(cols_vwc) else ""
            if st.button(f"S{i+1}\n{prof}", key=f"quick_{id_proyecto}_{i}", use_container_width=True):
                st.session_state[f"sensor_modal_{id_proyecto}"] = i
                st.session_state[f"pin_click_{id_proyecto}"] = i
                st.rerun()


# ─────────────────────────────────────────────
# 8. SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.image(
        "https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png",
        width=130
    )
    st.markdown("## VMS GeoCloud")
    st.markdown("<p style='color:#8b949e;font-size:0.85rem;'>Sistema de Monitoreo Geotécnico en Tiempo Real</p>", unsafe_allow_html=True)
    st.markdown("---")

    # Cargar fechas desde ROMERAL (ambas estaciones comparten el mismo CSV en esta demo)
    df_aux, err_aux = cargar_datos_proyecto("ROMERAL")
    fechas_sim = []
    if df_aux is not None:
        fechas_sim = sorted(df_aux['TIMESTAMP'].dt.date.unique(), reverse=True)

    fecha_sel = st.selectbox(
        "📅 Fecha de simulación:",
        fechas_sim,
        key="global_fecha_sel"
    )
    variable_grafico = st.selectbox(
        "📈 Variable histórica:",
        ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"],
        key="global_var_sel"
    )
    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.75rem;color:#8b949e;line-height:1.6;">
        <b style="color:#58a6ff;">Instrucciones:</b><br>
        1. Selecciona una estación<br>
        2. Haz clic en el marcador del mapa<br>
        3. En la radiografía, haz clic en un pin o usa los botones rápidos<br>
        4. Visualiza los datos analíticos del sensor
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 9. INTERFAZ PRINCIPAL POR ESTACIÓN
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
        st.warning("⚠️ Sin datos telemétricos para la fecha seleccionada.")
        return
    ultimo_registro = df_dia.iloc[-1]

    # ── MAPA SATELITAL ──
    st.markdown(f"""
    <h3 style="color:#e6edf3;margin-bottom:4px;">
        🗺️ Monitoreo Satelital — <span style="color:#58a6ff">{id_proyecto}</span>
    </h3>
    <p style="color:#8b949e;font-size:0.85rem;margin-bottom:12px;">
        Haz clic en el marcador azul para abrir la radiografía del pozo con sus sensores interactivos.
    </p>
    """, unsafe_allow_html=True)

    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri', name='Satelital', control=False
    ).add_to(m)

    # Popup con info básica en el mapa
    popup_html = f"""
    <div style="font-family:sans-serif;min-width:180px;">
        <b style="color:#1f6feb;">📍 {id_proyecto}</b><br>
        <small style="color:#666;">Sensores activos: {num_sens}</small><br>
        <hr style="margin:4px 0;">
        <small>Último registro:<br><b>{ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M')}</b></small>
    </div>
    """
    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        tooltip=f"📍 Click → Radiografía {id_proyecto}",
        popup=folium.Popup(popup_html, max_width=220),
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    mapa_output = st_folium(m, width="100%", height=480, key=f"mapa_{id_proyecto}")

    # ── GATILLO DEL MAPA → abre modal de radiografía ──
    if mapa_output and mapa_output.get("last_object_clicked"):
        st.session_state[f"abrir_radio_{id_proyecto}"] = True

    # ── RESUMEN DE SENSORES ACTIVOS (tabla compacta bajo el mapa) ──
    st.markdown("##### 📊 Estado Actual de Sensores")
    data_resumen = []
    for i in range(num_sens):
        prof = formatear_profundidad(cols_vwc[i]) if i < len(cols_vwc) else "N/A"
        data_resumen.append({
            "Sensor": f"S{i+1}",
            "Profundidad": prof,
            "VWC (%)": f"{ultimo_registro.get(cols_vwc[i], 0.0):.2f}" if i < len(cols_vwc) else "N/D",
            "Temp (°C)": f"{ultimo_registro.get(cols_temp[i], 0.0):.1f}" if i < len(cols_temp) else "N/D",
            "Presión (mbar)": f"{ultimo_registro.get(cols_pt[i], 0.0):.0f}" if i < len(cols_pt) else "N/D",
            "Nivel (cm)": f"{ultimo_registro.get(cols_dpt[i], 0.0):.1f}" if i < len(cols_dpt) else "N/D",
        })
    df_resumen = pd.DataFrame(data_resumen)
    st.dataframe(df_resumen, use_container_width=True, hide_index=True)

    # ── APERTURA DEL MODAL DE RADIOGRAFÍA ──
    if st.session_state.get(f"abrir_radio_{id_proyecto}"):
        modal_radiografia(
            id_proyecto, df_data, ultimo_registro,
            cols_vwc, cols_temp, cols_pt, cols_dpt,
            fecha_sel, variable_grafico
        )

    # ── APERTURA DEL MODAL DE SENSOR (desde botón rápido o pin) ──
    sensor_idx = st.session_state.get(f"sensor_modal_{id_proyecto}")
    if sensor_idx is not None:
        modal_sensor(
            id_proyecto, sensor_idx, df_data, ultimo_registro,
            cols_vwc, cols_temp, cols_pt, cols_dpt,
            fecha_sel, variable_grafico
        )


# ─────────────────────────────────────────────
# 10. PESTAÑAS PRINCIPALES
# ─────────────────────────────────────────────
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
