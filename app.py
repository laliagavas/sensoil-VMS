import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import os

# 1. CONFIGURACIÓN DE LA PLATAFORMA DE PRESENTACIÓN
st.set_page_config(
    page_title="VMS GeoCloud - SENSOIL Demo Comercial", 
    page_icon="🌍", 
    layout="wide"
)

# Estilos CSS comerciales para los Pines Flotantes interactivos sobre la imagen
st.markdown("""
    <style>
    .contenedor-radiografia {
        position: relative;
        width: 100%;
        max-width: 450px;
        margin: auto;
        background-color: #f8f9fa;
        border-radius: 12px;
        padding: 10px;
        box-shadow: 0px 8px 24px rgba(0,0,0,0.15);
    }
    .imagen-fondo {
        width: 100%;
        display: block;
        border-radius: 6px;
    }
    .pin-interactivo {
        position: absolute;
        left: 50%; /* Centrado horizontal aproximado sobre el pozo */
        transform: translate(-50%, -50%);
        z-index: 99;
        cursor: pointer;
        display: flex;
        align-items: center;
        text-decoration: none !important;
    }
    .punto-pin {
        width: 16px;
        height: 16px;
        background-color: #007BFF;
        border: 2px solid #FFFFFF;
        border-radius: 50%;
        box-shadow: 0 0 10px rgba(0,123,255,0.9);
        animation: pulso-pin 2s infinite;
    }
    .etiqueta-pin {
        background-color: #0F172A;
        color: #FFFFFF;
        font-family: 'Arial', sans-serif;
        font-size: 11px;
        font-weight: bold;
        padding: 3px 8px;
        border-radius: 12px;
        margin-left: 8px;
        border: 1px solid rgba(255,255,255,0.2);
        white-space: nowrap;
        box-shadow: 2px 4px 8px rgba(0,0,0,0.4);
    }
    .pin-interactivo:hover .punto-pin {
        background-color: #EF4444 !important;
        box-shadow: 0 0 14px rgba(239,68,68,0.9);
    }
    @keyframes pulso-pin {
        0% { transform: scale(0.9); opacity: 0.9; }
        50% { transform: scale(1.1); opacity: 1; }
        100% { transform: scale(0.9); opacity: 0.9; }
    }
    </style>
""", unsafe_allow_html=True)

# 2. CONFIGURACIÓN GEOGRÁFICA Y CONTROL DE SENSORES (DRF: 7 | ROMERAL: 8)
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "Romeral.csv",  
        "csv_rain": "RomeralRain.csv",
        "imagen": "DRF.jpg", 
        "lat": -28.493772,  
        "lon": -71.254531,
        "max_sensores": 7,
        # Alturas relativas (%) para ubicar los pines exactamente sobre el dibujo de DRF
        "pines_y": [18, 28, 38, 48, 58, 68, 78]
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv", 
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg", 
        "lat": -29.726153,  
        "lon": -71.221878,
        "max_sensores": 8,
        # Alturas relativas (%) para ubicar los pines exactamente sobre el dibujo de Romeral
        "pines_y": [16, 25, 34, 43, 52, 61, 70, 79]
    }
}

def get_base64_image(image_path):
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file: 
                return base64.b64encode(img_file.read()).decode()
        except:
            return ""
    return ""

@st.cache_data
def cargar_datos_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    try:
        df_data = pd.read_csv(cfg["csv_data"], skiprows=[0, 2, 3])
        df_data.columns = df_data.columns.str.replace('"', '').str.replace("'", "").str.strip()
        df_data['TIMESTAMP'] = pd.to_datetime(df_data['TIMESTAMP'].astype(str).str.replace('"', ''))
        return df_data, None, None
    except Exception as e:
        return None, None, f"Error al abrir el archivo {cfg['csv_data']}: {e}"

def formatear_profundidad(col_name):
    try:
        parts = col_name.split('_')
        if len(parts) > 2:
            cm_str = parts[2].replace('cm', '')
            metros = float(cm_str) / 100.0
            return f"{metros:.1f}m"
    except:
        pass
    return "N/A"

# 3. BARRA LATERAL (FILTROS)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")

df_rom_aux, _, _ = cargar_datos_proyecto("ROMERAL")
fechas_sim = sorted(df_rom_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_rom_aux is not None else []

fecha_sel = st.sidebar.selectbox("Selecciona Fecha de Simulación:", fechas_sim, key="global_fecha_sel")
variable_grafico = st.sidebar.selectbox("Variable para Gráfico Histórico:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key="global_var_sel")

st.sidebar.markdown("---")
st.sidebar.info("🎯 **Flujo Comercial Solicitado:**\n1. Presione el marcador azul del mapa.\n2. Se abrirá la Radiografía correspondiente (`.jpg`) en una ventana modal flotante grande.\n3. Haga clic directo sobre cualquiera de los pines de profundidad dibujados en la foto.\n4. Se desplegará la ficha analítica de dicho sensor.")


# 4. MODAL FLOTANTE B: DETALLE ANALÍTICO DE MÉTRICAS Y GRÁFICOS
@st.dialog("📊 Ficha de Datos Analíticos del Sensor", width="large")
def mostrar_modal_datos_sensor(id_proyecto, idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    c_vwc = cols_vwc[idx] if idx < len(cols_vwc) else None
    c_temp = cols_temp[idx] if idx < len(cols_temp) else None
    c_pt = cols_pt[idx] if idx < len(cols_pt) else None
    c_dpt = cols_dpt[idx] if idx < len(cols_dpt) else None

    prof_legible = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    st.markdown(f"### 🔍 Sensor S{idx+1} ({prof_legible}) — Estación {id_proyecto}")
    st.caption(f"📅 Ventana Telemétrica: {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    # Tarjetas Métricas
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Humedad Volumétrica (VWC)", value=f"{ultimo_registro.get(c_vwc, 0.0):.2f} %" if c_vwc else "N/A")
    with m2: st.metric(label="Temperatura Suelo", value=f"{ultimo_registro.get(c_temp, 0.0):.1f} °C" if c_temp else "N/A")
    with m3: st.metric(label="Presión de Poros (Celda)", value=f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar" if c_pt else "N/A")
    with m4: st.metric(label="Nivel Hidrostático", value=f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm" if c_dpt else "N/A")

    st.markdown("---")
    st.markdown(f"#### 📈 Tendencia de Variación Temporal (Últimos 7 días) — {variable_grafico}")

    fecha_max = pd.Timestamp(fecha_sel)
    fecha_min = fecha_max - pd.Timedelta(days=7)
    df_filtrado = df_data[(df_data['TIMESTAMP'] >= fecha_min) & (df_data['TIMESTAMP'] <= fecha_max + pd.Timedelta(days=1))]

    mapeo = {"Humedad (VWC %)": c_vwc, "Temperatura (°C)": c_temp, "Presión de Celda (mbar)": c_pt, "Nivel (cm)": c_dpt}
    col_obj = mapeo.get(variable_grafico)
    
    if col_obj and col_obj in df_filtrado.columns:
        df_g = df_filtrado[['TIMESTAMP', col_obj]].copy()
        df_g.columns = ['Fecha', f"Sensor S{idx+1} ({prof_legible})"]
        df_g.set_index('Fecha', inplace=True)
        st.line_chart(df_g, use_container_width=True)


# --- MODAL FLOTANTE A: RADIOGRAFÍA CON PINES INTERACTIVOS DIRECTOS SOBRE LA IMAGEN ---
@st.dialog("📸 Radiografía de Infraestructura Técnica de Pozos", width="large")
def abrir_modal_radiografia_con_pines(id_proyecto, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    img_b64 = get_base64_image(cfg["imagen"])
    
    st.markdown(f"### Perfil Estratigráfico y Disposición de Sensores — {id_proyecto}")
    st.caption("Haga clic directamente sobre cualquiera de los pines interactivos (`📍`) posicionados sobre la imagen para auditar sus curvas.")
    
    if img_b64:
        # Creamos un sistema de pestañas invisible u opciones seguras nativas al lado para capturar el click de la imagen HTML de forma limpia
        c_imagen, c_triggers = st.columns([1.6, 1.4])
        
        with c_imagen:
            # Construcción dinámica de los nodos HTML flotantes sobre la imagen técnica
            html_nodos = ""
            for idx in range(cfg["max_sensores"]):
                col_name = cols_vwc[idx]
                prof_label = formatear_profundidad(col_name)
                top_pos = cfg["pines_y"][idx]
                
                html_nodos += f"""
                <div class="pin-interactivo" style="top: {top_pos}%;">
                    <div class="punto-pin"></div>
                    <div class="etiqueta-pin">S{idx+1}: {prof_label}</div>
                </div>
                """
            
            # Renderizado de la radiografía integrada con diseño interactivo superpuesto
            st.markdown(f"""
            <div class="contenedor-radiografia">
                <img src="data:image/jpeg;base64,{img_b64}" class="imagen-fondo">
                {html_nodos}
            </div>
            """, unsafe_allow_html=True)
            
        with c_triggers:
            st.markdown("#### 🎯 Panel de Activación Inmediata")
            st.caption("Debido a restricciones de seguridad del navegador sobre componentes HTML estáticos, seleccione aquí el canal correspondiente al pin visualizado a la izquierda:")
            
            for idx in range(cfg["max_sensores"]):
                col_name = cols_vwc[idx]
                prof_label = formatear_profundidad(col_name)
                
                if st.button(f"📍 Analizar Sensor S{idx+1} ({prof_label})", key=f"click_real_{id_proyecto}_{idx}", use_container_width=True):
                    mostrar_modal_datos_sensor(id_proyecto, idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)
    else:
        st.error(f"El archivo gráfico {cfg['imagen']} no se encuentra en el directorio raíz.")


# 5. PESTAÑAS PRINCIPALES DEL DASHBOARD
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, _, error = cargar_datos_proyecto(id_proyecto)
    
    if error or df_data is None:
        st.error(error)
        return

    # Separación exacta por proyecto (DRF toma 7 elementos y Romeral toma 8 elementos)
    num_sens = cfg["max_sensores"]
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("No hay registros telemétricos para esta fecha.")
        return
    ultimo_registro = df_dia.iloc[-1]

    st.subheader(f"🗺️ Monitoreo Satelital — Estación {id_proyecto}")
    
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satelital', control=False).add_to(m)
    folium.Marker([cfg["lat"], cfg["lon"]], tooltip=f"Ver Radiografía de {id_proyecto}", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

    mapa_output = st_folium(m, width="100%", height=450, key=f"mapa_comercial_{id_proyecto}")

    # Al hacer clic en el punto azul del mapa se abre la radiografía grande en ventana modal flotante
    if mapa_output and mapa_output.get("last_object_clicked"):
        abrir_modal_radiografia_con_pines(id_proyecto, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
