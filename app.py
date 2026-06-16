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
        "csv_data": "Romeral.csv",  # Vinculado temporalmente al archivo existente para evitar caídas
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

# 3. BARRA LATERAL (PANEL DE CONTROL FIJO A LA IZQUIERDA)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ Panel de Control")

# Captura de fechas referenciales desde los datos
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
st.sidebar.info("🎯 **Flujo Comercial de la Demo:**\n1. Haga clic en el marcador azul del mapa.\n2. Se activará la visualización del Pozo en tamaño real abajo.\n3. Seleccione cualquier pin o botón de profundidad al costado de la foto.\n4. Se desplegará una ventana emergente del sistema con las métricas y gráficos históricos.")


# 4. VENTANA EMERGENTE MODAL (ST.DIALOG) PARA DETALLE ANALÍTICO DE SENSORES
@st.dialog("📊 Desglose de Datos del Sensor", width="large")
def mostrar_modal_sensor_fijo(id_proyecto, idx_seleccionado, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    c_vwc = cols_vwc[idx_seleccionado] if idx_seleccionado < len(cols_vwc) else None
    c_temp = cols_temp[idx_seleccionado] if idx_seleccionado < len(cols_temp) else None
    c_pt = cols_pt[idx_seleccionado] if idx_seleccionado < len(cols_pt) else None
    c_dpt = cols_dpt[idx_seleccionado] if idx_seleccionado < len(cols_dpt) else None

    prof_legible = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    st.markdown(f"### 🔍 Canal Sensor S{idx_seleccionado+1} ({prof_legible}) — Estación {id_proyecto}")
    st.caption(f"📅 Ventana Analítica: {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    # Corregido y asegurado completamente el formateo de strings para evitar SyntaxError
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
    st.markdown(f"#### 📈 Análisis de Variación Temporal (Últimos 7 días) — {variable_grafico}")

    # Filtrado dinámico para la tendencia histórica
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
        st.info("No hay datos históricos suficientes para graficar esta variable.")


# 5. ESTRUCTURA DE PESTAÑAS EN LA PANTALLA PRINCIPAL
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        return

    # Extracción e indexación ordenada de canales
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    
    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning(f"Sin registros para la fecha elegida.")
        return
    ultimo_registro = df_dia.iloc[-1]

    st.subheader(f"🗺️ Ubicación Satelital — Monitoreo Faena {id_proyecto}")
    
    # Mapa satelital limpio
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Vista Satelital',
        control=False
    ).add_to(m)

    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        tooltip=f"Haga clic aquí para desplegar la radiografía técnica del pozo {id_proyecto}",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    mapa_output = st_folium(m, width="100%", height=450, key=f"mapa_full_{id_proyecto}")

    # Persistencia del estado al clickear el marcador del mapa
    if f"ver_perfil_{id_proyecto}" not in st.session_state:
        st.session_state[f"ver_perfil_{id_proyecto}"] = False

    if mapa_output and mapa_output.get("last_object_clicked"):
        st.session_state[f"ver_perfil_{id_proyecto}"] = True

    # SECCIÓN DE DESPLIEGUE: IMAGEN EN GRANDE + PINS SELECCIONABLES AL COSTADO
    if st.session_state[f"ver_perfil_{id_proyecto}"]:
        st.markdown("---")
        st.markdown(f"### 📸 Perfil Técnico Estratigráfico e Infraestructura de Sensores: {id_proyecto}")
        
        col_foto, col_pines = st.columns([1.8, 1.2])
        
        with col_foto:
            img_b64 = get_base64_image(cfg["imagen"])
            if img_b64:
                # La imagen se despliega en tamaño grande y nítido, libre de compresiones
                st.markdown(f"""
                <div style="background-color: #f8f9fa; border-radius: 8px; padding: 10px; box-shadow: 0px 4px 12px rgba(0,0,0,0.1); text-align: center;">
                    <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; max-width: 480px; border-radius: 4px; display: inline-block;">
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"⚠️ Falta el archivo visual {cfg['imagen']} en el servidor.")
                
        with col_pines:
            st.markdown("#### 🎯 Auditoría por Profundidad")
            st.caption("Seleccione un pin marcado a continuación para abrir la ventana con la información en tiempo real:")
            
            # Generador interactivo de botones estilizados como puntos/pines de monitoreo
            for idx, col_name in enumerate(cols_vwc):
                prof_label = formatear_profundidad(col_name)
                
                # Botón interactivo nativo que simula un punto o pin de mapa marcado
                if st.button(f"📍 Sensor S{idx+1} (Profundidad: {prof_label})", key=f"btn_sensor_{id_proyecto}_{idx}", use_container_width=True):
                    # Llama directo a la ventana emergente modal con los datos exactos
                    mostrar_modal_sensor_fijo(id_proyecto, idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)

# 6. INYECCIÓN AUTOMÁTICA EN LAS PESTAÑAS
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
