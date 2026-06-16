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

# Estilos CSS personalizados para mejorar el diseño comercial y los botones tipo "Pin"
st.markdown("""
    <style>
    div.stButton > button {
        background-color: #0F172A !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.2) !important;
        border-radius: 20px !important;
        padding: 6px 16px !important;
        font-weight: bold !important;
        transition: all 0.3s ease;
    }
    div.stButton > button:hover {
        background-color: #007BFF !important;
        border-color: #FFFFFF !important;
        transform: scale(1.02);
    }
    </style>
""", unsafe_allow_html=True)

# 2. CONFIGURACIÓN GEOGRÁFICA Y DE SENSORES POR ESTACIÓN
# Aquí se corrige la cantidad exacta de sensores para cada proyecto (7 vs 8)
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "Romeral.csv",  # Vinculado para asegurar datos en la demo
        "csv_rain": "RomeralRain.csv",
        "imagen": "DRF.jpg", 
        "lat": -28.493772,  
        "lon": -71.254531,
        "max_senores": 7  # Configuración estricta para DRF
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv", 
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg", 
        "lat": -29.726153,  
        "lon": -71.221878,
        "max_senores": 8  # Configuración estricta para Romeral
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
        
        try:
            df_rain = pd.read_csv(cfg["csv_rain"], skiprows=[0, 2, 3])
            df_rain.columns = df_rain.columns.str.replace('"', '').str.replace("'", "").str.strip()
            df_rain['TIMESTAMP'] = pd.to_datetime(df_rain['TIMESTAMP'].astype(str).str.replace('"', ''))
        except:
            df_rain = None
            
        return df_data, df_rain, None
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

# 3. BARRA LATERAL (PANEL DE CONTROL UNIFICADO)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Panel de Control")

df_rom_aux, _, _ = cargar_datos_proyecto("ROMERAL")
fechas_sim = sorted(df_rom_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_rom_aux is not None else []

fecha_sel = st.sidebar.selectbox(
    "Selecciona Fecha de Simulación:", 
    fechas_sim, 
    key="global_fecha_sel"
)

variable_grafico = st.sidebar.selectbox(
    "Variable para Tendencia Histórica:", 
    ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], 
    key="global_var_sel"
)

st.sidebar.markdown("---")
st.sidebar.info("🎯 **Nueva Experiencia Interactiva:**\n1. Haga clic en el marcador del mapa.\n2. Aparecerá la radiografía técnica del pozo justo abajo.\n3. Seleccione el Pin de profundidad deseado al lado o sobre el perfil.\n4. Se abrirá la ventana flotante con las métricas y gráficos en alta resolución.")


# 4. MODAL FLOTANTE (ST.DIALOG) PARA DETALLE ANALÍTICO DEL SENSOR SELECTO
@st.dialog("📊 Ficha Técnica del Sensor", width="large")
def mostrar_modal_sensor_fijo(id_proyecto, idx_seleccionado, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    c_vwc = cols_vwc[idx_seleccionado] if idx_seleccionado < len(cols_vwc) else None
    c_temp = cols_temp[idx_seleccionado] if idx_seleccionado < len(cols_temp) else None
    c_pt = cols_pt[idx_seleccionado] if idx_seleccionado < len(cols_pt) else None
    c_dpt = cols_dpt[idx_seleccionado] if idx_seleccionado < len(cols_dpt) else None

    prof_legible = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    st.markdown(f"### 🔍 Sensor Canal S{idx_seleccionado+1} ({prof_legible}) — Estación {id_proyecto}")
    st.caption(f"📅 Ventana Horaria del Registro: {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    # Cuadrícula de KPI Comerciales
    m1, m2, m3, m4 = st.columns(4)
    with m1: 
        val_vwc = ultimo_registro.get(c_vwc, 0.0) if c_vwc else 0.0
        st.metric(label="Humedad Volumétrica (VWC)", value=f"{val_vwc:.2f} %")
    with m2: 
        val_temp = ultimo_registro.get(c_temp, 0.0) if c_temp else 0.0
        st.metric(label="Temperatura del Suelo", value=f"{val_temp:.1f} °C")
    with m3: 
        val_pt = ultimo_registro.get(c_pt, 0.0) if c_pt else 0.0
        st.metric(label="Presión de Poros (Celda)", value=f"{val_pt:.0f} mbar")
    with m4: 
        val_dpt = ultimo_registro.get(c_dpt, 0.0) if c_dpt else 0.0
        st.metric(label="Nivel Hidrostático Fijo", value=f"{val_dpt:.1f} cm")

    st.markdown("---")
    st.markdown(f"#### 📈 Tendencia Histórica e Histograma (Últimos 7 días) — {variable_grafico}")

    # Filtrado y construcción de la gráfica temporal
    fecha_max_grafico = pd.Timestamp(fecha_sel)
    fecha_min_grafico = fecha_max_grafico - pd.Timedelta(days=7)
    df_filtrado = df_data[(df_data['TIMESTAMP'] >= fecha_min_grafico) & (df_data['TIMESTAMP'] <= fecha_max_grafico + pd.Timedelta(days=1))]

    mapeo_variables = {
        "Humedad (VWC %)": c_vwc,
        "Temperatura (°C)": c_temp,
        "Presión de Celda (mbar)": c_pt,
        "Nivel (cm)": c_dpt
    }
    columna_objetivo = mapeo_variables.get(variable_grafico)
    
    if columna_objetivo and columna_objetivo in df_filtrado.columns:
        df_grafico = df_filtrado[['TIMESTAMP', columna_objetivo]].copy()
        df_grafico.columns = ['Fecha', f"Sensor S{idx_seleccionado+1} ({prof_legible})"]
        df_grafico.set_index('Fecha', inplace=True)
        st.line_chart(df_grafico, use_container_width=True)
    else:
        st.info("No hay suficientes registros históricos para desplegar la tendencia lineal.")


# 5. ESTRUCTURA VISUAL EN PESTAÑAS
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        return

    # Extracción y filtrado acotado por la cantidad de sensores definidos para la estación
    num_sensores = cfg["max_senores"]
    
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sensores]
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sensores]
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sensores]
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sensores]
    
    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning(f"No se registran datos telemétricos para la fecha seleccionada.")
        return
    ultimo_registro = df_dia.iloc[-1]

    st.subheader(f"🗺️ Geolocalización Satelital Continua — Faena {id_proyecto}")
    
    # Mapa base
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Vista Satelital',
        control=False
    ).add_to(m)

    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        tooltip=f"Ver perfil de sensores e infraestructura de {id_proyecto}",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    mapa_output = st_folium(m, width="100%", height=400, key=f"mapa_full_{id_proyecto}")

    # Control de estado de la visualización del pozo
    if f"ver_perfil_{id_proyecto}" not in st.session_state:
        st.session_state[f"ver_perfil_{id_proyecto}"] = False

    if mapa_output and mapa_output.get("last_object_clicked"):
        st.session_state[f"ver_perfil_{id_proyecto}"] = True

    # SECCIÓN PREMIUM INTERACTIVA: RADIOGRAFÍA DE INFRAESTRUCTURA Y BOTONES TIPO PIN
    if st.session_state[f"ver_perfil_{id_proyecto}"]:
        st.markdown("---")
        st.markdown(f"### 📸 Radiografía de Perfil Técnico e Infraestructura Multi-Sensor: {id_proyecto}")
        st.caption("Presione sobre los pines de monitoreo dispuestos al costado derecho del pozo para abrir la ficha analítica de datos en tiempo real.")
        
        col_foto, col_pines = st.columns([1.6, 1.4])
        
        with col_foto:
            img_b64 = get_base64_image(cfg["imagen"])
            if img_b64:
                st.markdown(f"""
                <div style="background-color: #f8f9fa; border-radius: 12px; padding: 15px; box-shadow: 0px 6px 16px rgba(0,0,0,0.1); text-align: center;">
                    <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; max-width: 420px; border-radius: 8px; display: inline-block;">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"⚠️ El archivo visual {cfg['imagen']} no está en la raíz.")
                
        with col_pines:
            st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
            
            # Generador dinámico y ordenado de accesos interactivos respetando la cantidad real de sensores (7 u 8)
            for idx, col_name in enumerate(cols_vwc):
                prof_label = formatear_profundidad(col_name)
                
                # Diseño premium de botón que simula el marcador estratigráfico del pozo
                if st.button(f"📍 Sensor S{idx+1} — Nivel de Profundidad: {prof_label}", key=f"btn_s_{id_proyecto}_{idx}", use_container_width=True):
                    mostrar_modal_sensor_fijo(id_proyecto, idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)

# 6. INYECCIÓN AUTOMÁTICA EN LAS PESTAÑAS DE NAVEGACIÓN
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
