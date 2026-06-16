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

# 2. CONFIGURACIÓN GEOGRÁFICA DE LAS ESTACIONES
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "DRF.csv",
        "csv_rain": "DRFRain.csv",
        "imagen": "DRF.jpg", 
        "lat": -28.493772,  
        "lon": -71.254531
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv", 
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg", 
        "lat": -29.726153,  
        "lon": -71.221878
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

# 3. BARRA LATERAL (PANEL DE CONTROL FIJO A LA IZQUIERDA)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Panel de Control")

# Obtener fechas referenciales
df_drf_aux, _, _ = cargar_datos_proyecto("DRF")
fechas_drf = sorted(df_drf_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_drf_aux is not None else []

fecha_sel = st.sidebar.selectbox(
    "Selecciona Fecha de Simulación:", 
    fechas_drf, 
    key="global_fecha_sel"
)

variable_grafico = st.sidebar.selectbox(
    "Variable para Tendencia Histórica:", 
    ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], 
    key="global_var_sel"
)

st.sidebar.markdown("---")
st.sidebar.info("🎯 **Flujo de la Demo:**\n1. Haga clic en el marcador azul del mapa.\n2. Se abrirá la Radiografía en tamaño grande.\n3. Haga clic en cualquier punto de profundidad sobre la foto para abrir la ventana con el desglose analítico y gráfico temporal.")

# 4. DIALOGOS EMERGENTES (MODALES DE ALTA RESOLUCIÓN)

@st.dialog("📊 Desglose de Datos del Sensor", width="large")
def mostrar_modal_sensor(id_proyecto, sensor_idx, prof_label, registro, df_data, cols_sensor):
    c_vwc, c_temp, c_pt, c_dpt = cols_sensor
    
    st.markdown(f"### 🔍 Sensor S{sensor_idx+1} ({prof_label}) — Faena {id_proyecto}")
    st.write(f"**Fecha del Registro:** {registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Métricas en cajas analíticas limpias
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Humedad Volumétrica (VWC)", value=f"{registro.get(c_vwc, 0.0):.2f} %")
    with m2: st.metric(label="Temperatura Suelo", value=f"{registro.get(c_temp, 0.0):.1f} °C")
    with m3: st.metric(label="Presión de Poros (Celda)", value=f"{registro.get(c_pt, 0.0):.0f} mbar")
    with m4: st.metric(label="Nivel Hidrostático", value=f"{registro.get(c_dpt, 0.0):.1f} cm")
    
    st.markdown("---")
    st.markdown(f"#### 📈 Histórico de Variación Temporal (Ventana de 7 días) — {variable_grafico}")
    
    # Gráfico histórico personalizado dentro de la ventana emergente
    fecha_max_grafico = pd.Timestamp(fecha_sel)
    fecha_min_grafico = fecha_max_grafico - pd.Timedelta(days=7)
    df_filtrado = df_data[(df_data['TIMESTAMP'] >= fecha_min_grafico) & (df_data['TIMESTAMP'] <= fecha_max_grafico + pd.Timedelta(days=1))]
    
    mapeo_variables = {
        "Humedad (VWC %)": c_vwc,
        "Temperatura (°C)": c_temp,
        "Presión de Celda (mbar)": c_pt,
        "Nivel (cm)": c_dpt
    }
    
    columna_objetivo = mapeo_variables[variable_grafico]
    df_grafico = df_filtrado[['TIMESTAMP', columna_objetivo]].copy()
    df_grafico.columns = ['Fecha', f"Sensor S{sensor_idx+1} ({prof_label})"]
    df_grafico.set_index('Fecha', inplace=True)
    st.line_chart(df_grafico, use_container_width=True)

@st.dialog("📸 Radiografía de Infraestructura Técnica", width="large")
def abrir_modal_radiografia(id_proyecto, cols_vwc, cols_temp, cols_pt, cols_dpt, ultimo_registro, df_data):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    num_sensores = len(cols_vwc)
    
    st.markdown(f"### Perfil Estratigráfico Vertical — {id_proyecto}")
    st.caption("Haga clic directamente sobre los puntos de profundidad azules para abrir la ventana de auditoría analítica.")
    
    img_b64 = get_base64_image(cfg["imagen"])
    
    if img_b64:
        # Construcción HTML interactiva con botones nativos de Streamlit simulados estéticamente
        html_nodos = ""
        for idx in range(num_sensores):
            col_name = cols_vwc[idx]
            prof_label = formatear_profundidad(col_name)
            
            # Distribución proporcional de los marcadores en vertical
            top_val = 20 + (idx * (82 - 20) / (num_sensores - 1)) if num_sensores > 1 else 50
            
            # Código HTML para generar un punto marcado e interactivo
            html_nodos += f"""
            <div style="position: absolute; top: {top_val}%; left: 50%; transform: translate(-50%, -50%); z-index: 10;">
                <a href="?action=audit_{id_proyecto}_{idx}" target="_top" style="text-decoration: none;">
                    <div style="background-color: #007BFF; color: white; padding: 4px 9px; 
                                border-radius: 20px; font-size: 11px; font-weight: bold; 
                                border: 2px solid white; box-shadow: 0px 2px 6px rgba(0,0,0,0.4);
                                cursor: pointer; white-space: nowrap; transition: 0.2s;">
                        📍 {prof_label}
                    </div>
                </a>
            </div>
            """
            
        st.markdown(f"""
        <div style="position: relative; width: 100%; max-width: 480px; margin: auto; background-color: #f8f9fa; border-radius: 8px; padding: 10px; box-shadow: inset 0 0 10px rgba(0,0,0,0.05);">
            <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; display: block; border-radius: 4px;">
            {html_nodos}
        </div>
        """, unsafe_html=True)
    else:
        st.error(f"Falta el archivo visual {cfg['imagen']} en el directorio.")

# 5. ESTRUCTURA DE PESTAÑAS EN PANTALLA PRINCIPAL
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        return

    # Extracción de canales dinámicos
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    
    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning(f"Sin registros para la fecha elegida.")
        return
    ultimo_registro = df_dia.iloc[-1]

    # MAPA SATELITAL LIMPIO A PANTALLA COMPLETA
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Vista Satelital',
        control=False
    ).add_to(m)

    # Marcador interactivo limpio
    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        tooltip=f"Ver Radiografía Completa del Pozo {id_proyecto}",
        icon=folium.Icon(color="blue", icon="fullscreen")
    ).add_to(m)

    # Renderizado y escucha de clics en el mapa
    mapa_output = st_folium(m, width="100%", height=550, key=f"mapa_full_{id_proyecto}")

    # Lógica de Apertura de Ventana de Imagen al pinchar el Marcador del Mapa
    if mapa_output and mapa_output.get("last_object_clicked"):
        # Reseteamos el estado de clic del mapa para permitir re-aperturas
        st.session_state[f"modal_radiografia_{id_proyecto}"] = True
        abrir_modal_radiografia(id_proyecto, cols_vwc, cols_temp, cols_pt, cols_dpt, ultimo_registro, df_data)

    # LÓGICA DE CAPTURA DE SELECCIÓN DE SENSOR POR PUNTO PINCHADO
    query_params = st.query_params
    action = query_params.get("action", None)
    
    if action and action.startswith(f"audit_{id_proyecto}_"):
        try:
            sensor_idx = int(action.split("_")[2])
            # Limpiamos el parámetro de la URL inmediatamente para evitar bucles de renderizado
            st.query_params.clear()
            
            # Ejecutamos el modal de auditoría específico del sensor pinchado
            c_vwc = cols_vwc[sensor_idx]
            prof_label = formatear_profundidad(c_vwc)
            cols_sensor = (cols_vwc[sensor_idx], cols_temp[sensor_idx], cols_pt[sensor_idx], cols_dpt[sensor_idx])
            
            mostrar_modal_sensor(id_proyecto, sensor_idx, prof_label, ultimo_registro, df_data, cols_sensor)
        except:
            pass

# 6. ASIGNACIÓN A CADA PESTAÑA
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
