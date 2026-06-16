import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import os

# 1. CONFIGURACIÓN DE LA PLATAFORMA DE VENTAS DEMO
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
        # Lee saltando los metadatos de Campbell (filas 1, 3 y 4 de metadatos)
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

# 4. BARRA LATERAL (BRANDING CORPORATIVO)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Uso para Clientes:** Navegue entre las pestañas de las faenas mineras, explore el mapa satelital interactivo y haga clic en el marcador azul para desplegar la radiografía de perforación en tiempo real.")

# 5. ESTRUCTURA DE PESTAÑAS PRINCIPALES
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        return

    # --- DETECCIÓN DINÁMICA DE COLUMNAS (BULLETPROOF CODES) ---
    # Busca y ordena los canales basándose en el número de sensor real que viene en la columna
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)
    
    num_sensores = len(cols_vwc)
    
    if num_sensores == 0:
        st.warning(f"No se detectaron columnas con formato de sensor (VWC_) en el archivo de {id_proyecto}.")
        return

    # Generación dinámica de la distribución vertical de nodos sobre la imagen
    coordenadas_nodos = {}
    for idx in range(num_sensores):
        sensor_num = idx + 1
        # Distribuye uniformemente los sensores entre el 22% y el 82% del alto de la imagen
        top_val = 22 + (idx * (82 - 22) / (num_sensores - 1)) if num_sensores > 1 else 50
        coordenadas_nodos[sensor_num] = {"top": f"{top_val:.1f}%", "left": "51%"}

    # --- CARGA Y PROCESAMIENTO DE FECHAS ---
    fechas_disponibles = df_data['TIMESTAMP'].dt.date.unique()
    
    col_mapa, col_controles = st.columns([5, 3])
    
    with col_controles:
        st.markdown("### ⚙️ Panel de Control")
        fecha_sel = st.selectbox(f"Selecciona fecha de simulación ({id_proyecto}):", sorted(fechas_disponibles, reverse=True), key=f"sel_fecha_{id_proyecto}")
        variable_grafico = st.selectbox("Variable para Tendencia Histórica:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key=f"sel_var_{id_proyecto}")
        st.info("🎯 **Presentación Comercial:** Al hacer clic en el marcador azul del mapa satelital, emergerá la radiografía interactiva en profundidad con las lecturas calculadas para este día.")

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    ultimo_registro = df_dia.iloc[-1]
    ultima_fecha = ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')

    # --- GENERACIÓN DE LA RADIOGRAFÍA COMPLETA EN POPUP ---
    img_b64 = get_base64_image(cfg["imagen"])
    
    popup_html = f"""
    <div style="font-family: 'Arial', sans-serif; width: 420px; max-height: 520px; overflow-y: auto; padding: 5px;">
        <h4 style="color: #0F172A; margin-top: 0; margin-bottom: 8px; border-bottom: 2px solid #3B82F6; padding-bottom: 4px;">
            🌍 Radiografía VMS - Perfil {id_proyecto}
        </h4>
        <p style="font-size: 11px; color: #64748B; margin: 0 0 10px 0;"><b>Registro:</b> {ultima_fecha} ({num_sensores} Sensores)</p>
    """
    
    if img_b64:
        popup_html += f"""
        <div style="position: relative; width: 100%; max-width: 380px; margin: auto;">
            <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; border-radius: 6px; display: block;">
        """
        # Renderizado dinámico basado en las columnas encontradas
        for idx in range(num_sensores):
            sensor_num = idx + 1
            col_name = cols_vwc[idx]
            vwc = ultimo_registro.get(col_name, 0.0)
            
            # Extrae la profundidad física del nombre de la columna (ej: 158cm)
            parts = col_name.split('_')
            prof = parts[2] if len(parts) > 2 else ""
            
            coord = coordenadas_nodos[sensor_num]
            color_borde = "#28A745" if pd.notna(vwc) and vwc >= 0 else "#DC3545"
            texto_vwc = f"{vwc:.1f}%" if pd.notna(vwc) and vwc >= 0 else "ERROR"
            
            popup_html += f"""
            <div style="position: absolute; top: {coord['top']}; left: {coord['left']}; 
                        background-color: rgba(15, 23, 42, 0.95); color: #FFFFFF; 
                        padding: 2px 6px; border-radius: 4px; font-size: 9px; 
                        font-weight: bold; border: 1.5px solid {color_borde}; 
                        transform: translate(-50%, -50%); white-space: nowrap; 
                        box-shadow: 2px 2px 5px rgba(0,0,0,0.4);">
                S{sensor_num} ({prof}): {texto_vwc}
            </div>
            """
        popup_html += "</div>"
    else:
        popup_html += f'<p style="color:red; font-size:12px;">⚠️ Falta el archivo visual {cfg["imagen"]} en GitHub para renderizar el perfil de sensores.</p>'
        
    popup_html += "</div>"

    # --- MAPA SATELITAL ---
    with col_mapa:
        st.subheader("🗺️ Ubicación Satelital en Faena")
        m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
        folium.TileLayer(
            tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
            attr='Esri World Imagery',
            name='Vista Satelital',
            overlay=False,
            control=False
        ).add_to(m)

        iframe = folium.IFrame(popup_html, width=440, height=540)
        folium.Marker(
            [cfg["lat"], cfg["lon"]],
            popup=folium.Popup(iframe, max_width=460),
            tooltip=f"Haga clic para abrir la Radiografía de {id_proyecto}",
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

        st_folium(m, width="100%", height=350, key=f"mapa_{id_proyecto}")

    st.markdown("---")
    
    # --- MÉTRICAS GENERALES DE INGENIERÍA ---
    st.subheader(f"📊 Estado Analítico del Perfil | Registro Seleccionado: {ultima_fecha}")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Voltaje del Sistema", value=f"{ultimo_registro.get('Batt_volt_Min', 0.0):.2f} V" if pd.notna(ultimo_registro.get('Batt_volt_Min')) else "N/A")
    with m2: st.metric(label="Estado de Carga (SOC)", value=f"{ultimo_registro.get('BatterySOC', 0.0):.1f} %" if pd.notna(ultimo_registro.get('BatterySOC')) else "N/A")
    with m3: st.metric(label="Temperatura Datalogger", value=f"{ultimo_registro.get('PTemp', 0.0):.1f} °C" if pd.notna(ultimo_registro.get('PTemp')) else "N/A")
    with m4:
        rain_val = 0.0
        if df_rain is not None:
            df_rain_dia = df_rain[df_rain['TIMESTAMP'].dt.date == fecha_sel]
            if not df_rain_dia.empty: rain_val = df_rain_dia.iloc[-1].get('Rain_day', 0.0)
        st.metric(label="Precipitación del Día", value=f"{rain_val:.2f} mm" if pd.notna(rain_val) else "N/A")

    # --- TABLA MATRIZ DE SENSORES Y GRÁFICO TENDENCIA ---
    col_detalles, col_grafico = st.columns([4, 5])
    
    with col_detalles:
        st.markdown("**📋 Matriz Completa de Sensores (Lecturas Físicas)**")
        tabla_datos = []
        for idx in range(num_sensores):
            sensor_label = f"S{idx+1}"
            
            val_vwc = ultimo_registro.get(cols_vwc[idx], 0.0) if idx < len(cols_vwc) else 0.0
            val_temp = ultimo_registro.get(cols_temp[idx], 0.0) if idx < len(cols_temp) else 0.0
            val_pt = ultimo_registro.get(cols_pt[idx], 0.0) if idx < len(cols_pt) else 0.0
            val_dpt = ultimo_registro.get(cols_dpt[idx], 0.0) if idx < len(cols_dpt) else 0.0
            
            profundidad = cols_vwc[idx].split('_')[2] if len(cols_vwc[idx].split('_')) > 2 else "N/A"
            
            tabla_datos.append({
                "Sensor": sensor_label,
                "Profundidad": profundidad,
                "Humedad (VWC)": f"{val_vwc:.2f} %" if pd.notna(val_vwc) else "N/A",
                "Temperatura": f"{val_temp:.1f} °C" if pd.notna(val_temp) else "N/A",
                "Presión Celda": f"{val_pt:.0f} mbar" if pd.notna(val_pt) else "N/A",
                "Nivel Fijo": f"{val_dpt:.1f} cm" if pd.notna(val_dpt) else "N/A"
            })
        st.dataframe(pd.DataFrame(tabla_datos), hide_index=True, use_container_width=True)

    with col_grafico:
        st.markdown(f"**📈 Curvas de Variación Temporal (Últimos 7 días)**")
        fecha_max_grafico = pd.Timestamp(fecha_sel)
        fecha_min_grafico = fecha_max_grafico - pd.Timedelta(days=7)
        df_filtrado = df_data[(df_data['TIMESTAMP'] >= fecha_min_grafico) & (df_data['TIMESTAMP'] <= fecha_max_grafico + pd.Timedelta(days=1))]

        mapeo_variables = {
            "Humedad (VWC %)": cols_vwc,
            "Temperatura (°C)": cols_temp,
            "Presión de Celda (mbar)": cols_pt,
            "Nivel (cm)": cols_dpt
        }

        columnas_grafico = mapeo_variables[variable_grafico]
        df_grafico = df_filtrado[['TIMESTAMP'] + columnas_grafico].copy()
        df_grafico.columns = ['Fecha'] + [f"Sensor S{i+1}" for i in range(num_sensores)]
        df_grafico.set_index('Fecha', inplace=True)
        st.line_chart(df_grafico, use_container_width=True)

# 6. ASIGNACIÓN DE CONTENIDO A LAS PESTAÑAS
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
