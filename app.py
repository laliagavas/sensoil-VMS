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
        "csv_data": "Romeral.csv",  # Cambiado temporalmente al archivo existente para evitar caídas en la demo
        "csv_rain": "RomeralRain.csv",
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

# 3. BARRA LATERAL (PANEL DE CONTROL FIJO A LA IZQUIERDA ABAJO DEL TÍTULO)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Panel de Control")

# Captura de fechas referenciales reales desde la data cargada
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
st.sidebar.info("🎯 **Flujo de la Demo:**\n1. Haga clic en el marcador azul del mapa.\n2. Se abrirá la Radiografía en tamaño grande.\n3. Haga clic en cualquier pin de profundidad (`📍 0.4m`) sobre la foto.\n4. Se abrirá una ventana independiente con los gráficos e indicadores específicos.")


# 4. VENTANA FLOTANTE INDEPENDIENTE (MODAL PARA DETALLE DEL SENSOR)
@st.dialog("📊 Desglose de Datos del Sensor", width="large")
def mostrar_modal_sensor_detallado(id_proyecto, idx_seleccionado):
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    if error or df_data is None:
        st.error("Error al cargar la base de datos de auditoría.")
        return
        
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("No hay registros disponibles para la fecha seleccionada.")
        return
    ultimo_registro = df_dia.iloc[-1]

    c_vwc = cols_vwc[idx_seleccionado] if idx_seleccionado < len(cols_vwc) else None
    c_temp = cols_temp[idx_seleccionado] if idx_seleccionado < len(cols_temp) else None
    c_pt = cols_pt[idx_seleccionado] if idx_seleccionado < len(cols_pt) else None
    c_dpt = cols_dpt[idx_seleccionado] if idx_seleccionado < len(cols_dpt) else None

    prof_legible = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    st.markdown(f"### 🔍 Sensor S{idx_seleccionado+1} ({prof_legible}) | Estación {id_proyecto}")
    st.caption(f"📅 Registro Auditado: {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    # Fila de Tarjetas de Métricas Clave
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Humedad Volumétrica (VWC)", value=f"{ultimo_registro.get(c_vwc, 0.0):.2f} %" if c_vwc else "N/A")
    with m2: st.metric(label="Temperatura del Suelo", value=f"{ultimo_registro.get(c_temp, 0.0):.1f} °C" if c_temp else "N/A")
    with m3: st.metric(label="Presión de Poros (Celda)", value=f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar" if c_pt else "N/A")
    with m4: st.metric(label="Nivel Hidrostático Fijo", value=f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm" if c_dpt else "N/A")

    st.markdown("---")
    st.markdown(f"#### 📈 Análisis de Variación Temporal (Últimos 7 días) — {variable_grafico}")

    # Renderizado de gráfico lineal histórico
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

    if st.button("❌ Cerrar y Volver", use_container_width=True):
        st.query_params.clear()
        st.rerun()


# --- VENTANA FLOTANTE INDEPENDIENTE (MODAL PARA RADIOGRAFÍA TÉCNICA GRANDE) ---
@st.dialog("📸 Radiografía de Infraestructura Técnica", width="large")
def abrir_modal_radiografia(id_proyecto, cols_vwc):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    num_sensores = len(cols_vwc)
    
    st.markdown(f"### Perfil Estratigráfico Vertical — Faena {id_proyecto}")
    st.caption("Haga clic sobre cualquiera de los marcadores azules tipo pin (`📍`) dispuestos en el pozo para auditar sus curvas.")
    
    img_b64 = get_base64_image(cfg["imagen"])
    
    if img_b64:
        html_nodos = ""
        for idx in range(num_sensores):
            col_name = cols_vwc[idx]
            prof_label = formatear_profundidad(col_name)
            
            # Distribución proporcional de los pines en vertical sobre la imagen
            top_val = 18 + (idx * (82 - 18) / (num_sensores - 1)) if num_sensores > 1 else 50
            
            # Marcador interactivo limpio estilo pin de mapa
            html_nodos += f"""
            <div style="position: absolute; top: {top_val}%; left: 52%; transform: translate(-50%, -50%); z-index: 10;">
                <a href="?sensor={id_proyecto}_{idx}" target="_top" style="text-decoration: none;">
                    <div style="display: flex; align-items: center; cursor: pointer;">
                        <div style="width: 14px; height: 14px; background-color: #007BFF; border: 2px solid #FFFFFF; border-radius: 50%; box-shadow: 0 0 8px rgba(0,123,255,0.8); display: flex; align-items: center; justify-content: center;">
                            <div style="width: 4px; height: 4px; background-color: white; border-radius: 50%;"></div>
                        </div>
                        <div style="background-color: #0F172A; color: #FFFFFF; font-family: 'Arial', sans-serif; font-size: 11px; font-weight: bold; padding: 2px 7px; border-radius: 12px; margin-left: 6px; border: 1px solid rgba(255,255,255,0.3); white-space: nowrap; box-shadow: 1px 2px 5px rgba(0,0,0,0.3);">
                            📍 {prof_label}
                        </div>
                    </div>
                </a>
            </div>
            """
            
        # CORREGIDO AQUÍ: Se cambió unsafe_html=True por unsafe_allow_html=True para evitar el error fatal
        st.markdown(f"""
        <div style="position: relative; width: 100%; max-width: 480px; margin: auto; background-color: #f8f9fa; border-radius: 8px; padding: 10px; box-shadow: 0px 4px 12px rgba(0,0,0,0.15);">
            <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; display: block; border-radius: 4px;">
            {html_nodos}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.error(f"⚠️ El archivo visual {cfg['imagen']} no se encuentra en el directorio raíz.")


# Escucha global de parámetros en la URL para activar el segundo modal (Datos del Sensor)
if "sensor" in query_params:
    sensor_val = query_params["sensor"]
    parts = sensor_val.split("_")
    if len(parts) == 2:
        st.session_state["modal_sensor_active"] = (parts[0], int(parts[1]))

if "modal_sensor_active" in st.session_state and st.session_state["modal_sensor_active"]:
    proj_id, s_idx = st.session_state["modal_sensor_active"]
    del st.session_state["modal_sensor_active"]
    mostrar_modal_sensor_detallado(proj_id, s_idx)


# 5. ASIGNACIÓN DE PESTAÑAS PRINCIPALES DE NAVEGACIÓN
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        return

    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    
    st.subheader(f"🗺️ Ubicación Satelital — Monitoreo Faena {id_proyecto}")
    
    # Renderizado del mapa principal a pantalla completa
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Vista Satelital',
        control=False
    ).add_to(m)

    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        tooltip=f"Haga clic para expandir la radiografía técnica de {id_proyecto}",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    mapa_output = st_folium(m, width="100%", height=500, key=f"mapa_full_{id_proyecto}")

    # Captura del clic en el marcador del mapa para abrir la radiografía grande
    if mapa_output and mapa_output.get("last_object_clicked"):
        abrir_modal_radiografia(id_proyecto, cols_vwc)

# 6. INYECCIÓN DE DATOS
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
