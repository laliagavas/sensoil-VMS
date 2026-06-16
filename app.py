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

# Configuración Estricta de Sensores (DRF: 7 | ROMERAL: 8)
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "Romeral.csv",  
        "csv_rain": "RomeralRain.csv",
        "imagen": "DRF.jpg", 
        "lat": -28.493772,  
        "lon": -71.254531,
        "max_sensores": 7
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv", 
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg", 
        "lat": -29.726153,  
        "lon": -71.221878,
        "max_sensores": 8
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

# 2. BARRA LATERAL (FILTROS)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")

df_rom_aux, _, _ = cargar_datos_proyecto("ROMERAL")
fechas_sim = sorted(df_rom_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_rom_aux is not None else []
fecha_sel = st.sidebar.selectbox("Selecciona Fecha de Simulación:", fechas_sim, key="global_fecha_sel")
variable_grafico = st.sidebar.selectbox("Variable para Gráfico Histórico:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key="global_var_sel")


# 3. MODAL DE DATOS ANALÍTICOS (Abre los gráficos al pinchar la imagen)
@st.dialog("📊 Ficha de Datos Analíticos", width="large")
def mostrar_modal_datos_sensor(id_proyecto, idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    c_vwc = cols_vwc[idx] if idx < len(cols_vwc) else None
    c_temp = cols_temp[idx] if idx < len(cols_temp) else None
    c_pt = cols_pt[idx] if idx < len(cols_pt) else None
    c_dpt = cols_dpt[idx] if idx < len(cols_dpt) else None

    prof_legible = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    st.markdown(f"### 🔍 Canal Sensor S{idx+1} ({prof_legible}) — {id_proyecto}")
    st.caption(f"📅 Registro: {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Humedad Volumétrica (VWC)", value=f"{ultimo_registro.get(c_vwc, 0.0):.2f} %" if c_vwc else "N/A")
    with m2: st.metric(label="Temperatura Suelo", value=f"{ultimo_registro.get(c_temp, 0.0):.1f} °C" if c_temp else "N/A")
    with m3: st.metric(label="Presión de Poros", value=f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar" if c_pt else "N/A")
    with m4: st.metric(label="Nivel Hidrostático", value=f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm" if c_dpt else "N/A")

    st.markdown("---")
    st.markdown(f"#### 📈 Tendencia de Variación (Últimos 7 días) — {variable_grafico}")

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


# 4. MODAL PRINCIPAL: RADIOGRAFÍA EN TAMAÑO COMERCIAL
@st.dialog("📸 Radiografía Técnica del Pozo", width="large")
def abrir_modal_radiografia(id_proyecto, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    img_b64 = get_base64_image(cfg["imagen"])
    
    st.markdown(f"### Perfil de Infraestructura de Sensores: {id_proyecto}")
    st.caption("Selecciona la profundidad correspondiente en el selector inferior para interactuar con la radiografía.")
    st.markdown("---")
    
    # Maquetación para que la imagen se vea grande y centrada
    c_izq, c_centro, c_der = st.columns([1, 3, 1])
    
    with c_centro:
        if img_b64:
            st.markdown(f"""
                <div style="background-color: #ffffff; border-radius: 12px; padding: 10px; box-shadow: 0px 4px 20px rgba(0,0,0,0.1); text-align: center;">
                    <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; max-width: 550px; border-radius: 8px;">
                </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Archivo {cfg['imagen']} no encontrado.")
            
    st.markdown("---")
    
    # Selector interactivo integrado de manera elegante justo debajo de la imagen grande
    opciones_pines = []
    for idx in range(cfg["max_sensores"]):
        col_name = cols_vwc[idx]
        prof_label = formatear_profundidad(col_name)
        opciones_pines.append(f"📍 Sensor S{idx+1} ({prof_label})")
        
    seleccion = st.selectbox("🎯 Selecciona un punto medido de la imagen para auditar:", opciones_pines)
    
    if st.button("📊 Ver Gráficos e Indicadores en Tiempo Real", use_container_width=True):
        idx_elegido = opciones_pines.index(seleccion)
        mostrar_modal_datos_sensor(id_proyecto, idx_elegido, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)


# 5. PESTAÑAS PRINCIPALES E INTERFAZ DEL MAPA
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, _, error = cargar_datos_proyecto(id_proyecto)
    
    if error or df_data is None:
        st.error(error)
        return

    # Ajuste exacto de los sensores (7 para DRF y 8 para Romeral)
    num_sens = cfg["max_sensores"]
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("No hay registros telemétricos cargados para esta fecha.")
        return
    ultimo_registro = df_dia.iloc[-1]

    st.subheader(f"🗺️ Monitoreo Satelital — Faena {id_proyecto}")
    
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satelital', control=False).add_to(m)
    folium.Marker([cfg["lat"], cfg["lon"]], tooltip=f"Ver Radiografía de {id_proyecto}", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

    mapa_output = st_folium(m, width="100%", height=450, key=f"mapa_final_{id_proyecto}")

    # GATILLO SEGURO: Al pinchar en el mapa, se gatilla la radiografía de forma nativa
    if mapa_output and mapa_output.get("last_object_clicked"):
        abrir_modal_radiografia(id_proyecto, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
