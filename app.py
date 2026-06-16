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
    with m4: st.metric(label="Nivel Hidrostático Fijo", value=f"{ultimo_registro.get(c_dpt, 0.0):.1
