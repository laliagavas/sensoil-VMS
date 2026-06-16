import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import os

# 1. CONFIGURACIÓN DE LA PLATAFORMA
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
    """Transforma sufijos como 158cm a formato legible en metros (1.6m)"""
    try:
        parts = col_name.split('_')
        if len(parts) > 2:
            cm_str = parts[2].replace('cm', '')
            metros = float(cm_str) / 100.0
            return f"{metros:.1f}m"
    except:
        pass
    return "N/A"

# 3. BARRA LATERAL (BRANDING Y CONTROLES GLOBALES)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")

st.sidebar.markdown("### ⚙️ Panel de Control")

# Manejo de estados de selección de fecha compartidos
df_drf_aux, _, _ = cargar_datos_proyecto("DRF")
fechas_drf = sorted(df_drf_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_drf_aux is not None else []

fecha_sel = st.sidebar.selectbox(
    "Selecciona Fecha de Simulación:", 
    fechas_drf, 
    key="global_fecha_sel"
)

variable_grafico = st.sidebar.selectbox(
    "Variable para Tendencia:", 
    ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], 
    key="global_var_sel"
)

st.sidebar.markdown("---")
st.sidebar.info("🎯 **Instrucciones de la Demo:**\n1. Haga clic en el marcador azul del mapa.\n2. Dentro de la foto emergente, haga clic en cualquier etiqueta de profundidad (ej: 1.6m).\n3. La información analítica detallada de ese sensor específico se desplegará mágicamente abajo del mapa.")

# 4. ESTRUCTURA DE PESTAÑAS PRINCIPALES
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        return

    # --- DETECCIÓN DINÁMICA DE CANALES ---
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    
    num_sensores = len(cols_vwc)
    if num_sensores == 0:
        st.warning("No se detectaron sensores en el archivo.")
        return

    # Distribución de coordenadas sobre la imagen técnica
    coordenadas_nodos = {}
    for idx in range(num_sensores):
        sensor_num = idx + 1
        top_val = 22 + (idx * (82 - 22) / (num_sensores - 1)) if num_sensores > 1 else 50
        coordenadas_nodos[sensor_num] = {"top": f"{top_val:.1f}%", "left": "51%"}

    # Filtrado por fecha seleccionada en el Panel de Control lateral
    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning(f"No hay registros para la fecha {fecha_sel} en la estación {id_proyecto}.")
        return
        
    ultimo_registro = df_dia.iloc[-1]
    ultima_fecha = ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')

    # --- MAPA SATELITAL (ANCHO COMPLETO PARA LIMPIEZA VISUAL) ---
    st.subheader(f"🗺️ Ubicación Satelital e Infraestructura de Monitoreo")
    
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Vista Satelital',
        control=False
    ).add_to(m)

    # --- CONSTRUCCIÓN DEL HTML DE LA RADIOGRAFÍA INTERACTIVA (CON LINKS DE CAPTURA) ---
    img_b64 = get_base64_image(cfg["imagen"])
    popup_html = f"""
    <div style="font-family: 'Arial', sans-serif; width: 320px; text-align: center;">
        <h4 style="color: #0F172A; margin: 0 0 4px 0; border-bottom: 2px solid #3B82F6; padding-bottom: 4px; font-size: 13px;">
            📸 Perfil Técnico: {id_proyecto}
        </h4>
        <p style="font-size: 10px; color: #64748B; margin: 0 0 8px 0;">Pinche una profundidad para auditar datos:</p>
    """
    
    if img_b64:
        popup_html += f"""
        <div style="position: relative; width: 100%; max-width: 260px; margin: auto;">
            <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; border-radius: 4px; display: block;">
        """
        for idx in range(num_sensores):
            sensor_num = idx + 1
            col_name = cols_vwc[idx]
            prof_label = formatear_profundidad(col_name)
            coord = coordenadas_nodos[sensor_num]
            
            # Link especial que recarga la app inyectando el sensor seleccionado en la URL
            link_target = f"?sensor={id_proyecto}_{sensor_num}"
            
            popup_html += f"""
            <a href="{link_target}" target="_top" style="text-decoration: none;">
                <div style="position: absolute; top: {coord['top']}; left: {coord['left']}; 
                            background-color: #3B82F6; color: #FFFFFF; 
                            padding: 2px 5px; border-radius: 3px; font-size: 10px; 
                            font-weight: bold; border: 1px solid #FFFFFF; 
                            transform: translate(-50%, -50%); white-space: nowrap; 
                            box-shadow: 1px 1px 4px rgba(0,0,0,0.4); cursor: pointer;">
                    📍 {prof_label}
                </div>
            </a>
            """
        popup_html += "</div>"
    else:
        popup_html += f'<p style="color:red; font-size:11px;">⚠️ Archivo {cfg["imagen"]} ausente.</p>'
    popup_html += "</div>"

    iframe = folium.IFrame(popup_html, width=340, height=440)
    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        popup=folium.Popup(iframe, max_width=360),
        tooltip=f"Haga clic para ver la Radiografía del Pozo {id_proyecto}",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    st_folium(m, width="100%", height=380, key=f"mapa_{id_proyecto}")

    # --- LÓGICA DE CAPTURA DEL SENSOR SELECCIONADO POR CLIC ---
    parametros = st.query_params
    sensor_seleccionado = parametros.get("sensor", None)
    
    st.markdown("---")
    
    # Verificamos si el clic pertenece a la pestaña de la faena que estamos renderizando
    if sensor_seleccionado and sensor_seleccionado.startswith(f"{id_proyecto}_"):
        try:
            idx_seleccionado = int(sensor_seleccionado.split("_")[1]) - 1
        except:
            idx_seleccionado = 0
            
        if idx_seleccionado >= num_sensores:
            idx_seleccionado = 0
            
        # Extraemos los datos del sensor elegido
        c_vwc = cols_vwc[idx_seleccionado]
        c_temp = cols_temp[idx_seleccionado]
        c_pt = cols_pt[idx_seleccionado]
        c_dpt = cols_dpt[idx_seleccionado]
        
        prof_legible = formatear_profundidad(c_vwc)
        
        # --- DESPLIEGUE EXCLUSIVO DEL SENSOR AUDITADO ---
        st.subheader(f"🔍 Auditoría en Profundidad: Sensor S{idx_seleccionado+1} ({prof_legible}) | {id_proyecto}")
        
        # Fila 1: Métricas específicas del punto seleccionado
        m1, m2, m3, m4 = st.columns(4)
        with m1: st.metric(label=f"Humedad Volumétrica (VWC)", value=f"{ultimo_registro.get(c_vwc, 0.0):.2f} %")
        with m2: st.metric(label="Temperatura del Suelo", value=f"{ultimo_registro.get(c_temp, 0.0):.1f} °C")
        with m3: st.metric(label="Presión de Poros (Celda)", value=f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar")
        with m4: st.metric(label="Nivel Hidrostático Fijo", value=f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm")
        
        # Fila 2: Gráfico de Tendencia Histórica del Sensor
        st.markdown(f"**📈 Análisis de Comportamiento Temporal Histórico (Ventana de 7 días)**")
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
        df_grafico.columns = ['Fecha', f"Sensor S{idx_seleccionado+1} ({prof_legible}) - {variable_grafico}"]
        df_grafico.set_index('Fecha', inplace=True)
        st.line_chart(df_grafico, use_container_width=True)
        
    else:
        # Estado inicial o de reposo instructivo
        st.info(f"💡 **Modo de Espera Activo:** Por favor, expanda el mapa de arriba, haga clic en el marcador azul y seleccione una de las profundidades físicas disponibles (ej: {formatear_profundidad(cols_vwc[0])}) para auditar el comportamiento hidrológico detallado de ese nivel.")

# 5. ASIGNACIÓN DE CONTENIDO A LAS PESTAÑAS
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
