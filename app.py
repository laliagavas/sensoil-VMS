Python
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
import base64
import os

# 1. CONFIGURACIÓN DE LA PLATAFORMA DE VENTAS
st.set_page_config(
    page_title="VMS GeoCloud - SENSOIL Demo Comercial", 
    page_icon="🌍", 
    layout="wide"
)

# 2. RUTAS DE LOS ARCHIVOS EN SUPABASE STORAGE (Reemplaza 'TU_PROYECTO')
URL_BASE = "https://TU_PROYECTO.supabase.co/storage/v1/object/public/sensoil-data"

CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": f"{URL_BASE}/drf/DRF.csv",
        "csv_rain": f"{URL_BASE}/drf/DRFRain.csv",
        "imagen": "perforacion_drf.jpg",
        "lat": -27.3667,  # REEMPLAZA por la latitud real de DRF
        "lon": -70.3333,  # REEMPLAZA por la longitud real de DRF
        "coordenadas_nodos": {
            1: {"top": "41%", "left": "56%"}, 2: {"top": "48%", "left": "48%"}, 3: {"top": "56%", "left": "41%"},
            4: {"top": "64%", "left": "34%"}, 5: {"top": "72%", "left": "27%"}, 6: {"top": "79%", "left": "20%"},
            7: {"top": "87%", "left": "13%"}
        },
        "sufijos_vwc": {1: "1_40cm", 2: "2_82cm", 3: "3_184cm", 4: "4_287cm", 5: "5_389cm", 6: "6_491cm", 7: "7_594cm"},
        "sufijos_pt": {1: "1_40cm", 2: "2_123cm", 3: "3_225cm", 4: "4_328cm", 5: "5_430cm", 6: "6_532cm", 7: "7_635cm"},
        "sufijos_dpt": {1: "1_50cm", 2: "2_152cm", 3: "3_254cm", 4: "4_356cm", 5: "5_459cm", 6: "6_561cm", 7: "7_664cm"}
    },
    "ROMERAL": {
        "csv_data": f"{URL_BASE}/romeral/DRF.csv",
        "csv_rain": f"{URL_BASE}/romeral/DRFRain.csv",
        "imagen": "perforacion_romeral.jpg",
        "lat": -29.8833,  # REEMPLAZA por la latitud real de Romeral
        "lon": -71.2333,  # REEMPLAZA por la longitud real de Romeral
        # Coordenadas tentativas para Romeral (Vertical - línea recta hacia abajo)
        "coordenadas_nodos": {
            1: {"top": "25%", "left": "50%"}, 2: {"top": "35%", "left": "50%"}, 3: {"top": "45%", "left": "50%"},
            4: {"top": "55%", "left": "50%"}, 5: {"top": "65%", "left": "50%"}, 6: {"top": "75%", "left": "50%"},
            7: {"top": "85%", "left": "50%"}
        },
        "sufijos_vwc": {1: "1_40cm", 2: "2_82cm", 3: "3_184cm", 4: "4_287cm", 5: "5_389cm", 6: "6_491cm", 7: "7_594cm"},
        "sufijos_pt": {1: "1_40cm", 2: "2_123cm", 3: "3_225cm", 4: "4_328cm", 5: "5_430cm", 6: "6_532cm", 7: "7_635cm"},
        "sufijos_dpt": {1: "1_50cm", 2: "2_152cm", 3: "3_254cm", 4: "4_356cm", 5: "5_459cm", 6: "6_561cm", 7: "7_664cm"}
    }
}

# 3. FUNCIONES AUXILIARES
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode()
    return ""

@st.cache_data
def cargar_datos_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    try:
        df_data = pd.read_csv(cfg["csv_data"], skiprows=[0, 2, 3])
        df_data['TIMESTAMP'] = pd.to_datetime(df_data['TIMESTAMP'])
        try:
            df_rain = pd.read_csv(cfg["csv_rain"], skiprows=[0, 2, 3])
            df_rain['TIMESTAMP'] = pd.to_datetime(df_rain['TIMESTAMP'])
        except:
            df_rain = None
        return df_data, df_rain, None
    except Exception as e:
        return None, None, f"Error al cargar {id_proyecto}: {e}"

# 4. DISEÑO DE LA BARRA LATERAL (BRANDING)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Guía de uso:** Seleccione la pestaña de la faena minera, haga clic en el marcador del mapa satelital y presione el botón flotante para desplegar la radiografía en tiempo real de la perforación.")

# 5. MARCO PRINCIPAL - CREACIÓN DE PESTAÑAS (TABS)
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

# --- FUNCIÓN MAESTRA PARA RENDERIZAR CADA PROYECTO ---
def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        return

    # --- MAPA SATELITAL INTERACTIVO ---
    st.subheader("🗺️ Ubicación Geográfica en Terreno")
    
    # Crear mapa folium centrado en la faena con capa Satelital de Esri
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=15, tiles="cartodbpositron")
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri',
        name='Satelital',
        overlay=False,
        control=True
    ).add_to(m)

    # Marcador interactivo
    popup_text = f"""
    <div style='font-family: Arial, sans-serif; width: 180px;'>
        <h4>Sistema VMS {id_proyecto}</h4>
        <p><b>Estado:</b> Operacional</p>
        <p><i>Haga clic abajo para inspeccionar sensores</i></p>
    </div>
    """
    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        popup=popup_text,
        tooltip=f"Ver Perforación {id_proyecto}",
        icon=folium.Icon(color="green", icon="cloud")
    ).add_to(m)

    # Renderizar mapa en Streamlit
    st_folium(m, width="100%", height=350, key=f"mapa_{id_proyecto}")

    st.markdown("---")
    
    # Control de tiempo comercial (Viaje en el tiempo para la Demo)
    fechas_disponibles = df_data['TIMESTAMP'].dt.date.unique()
    
    col_control1, col_control2 = st.columns([4, 4])
    with col_control1:
        fecha_sel = st.selectbox(f"Selecciona fecha para simulación ({id_proyecto}):", sorted(fechas_disponibles, reverse=True), key=f"sel_fecha_{id_proyecto}")
    with col_control2:
        variable_grafico = st.selectbox("Variable para Gráfico Histórico:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key=f"sel_var_{id_proyecto}")

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    ultimo_registro = df_dia.iloc[-1]
    ultima_fecha = ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')

    st.subheader(f"📊 Análisis de Perforación - Registro Técnico: {ultima_fecha}")
    
    # Métricas clave superiores
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Voltaje Batería", value=f"{ultimo_registro.get('Batt_volt_Min', 0.0):.2f} V")
    with m2: st.metric(label="Carga Batería (SOC)", value=f"{ultimo_registro.get('BatterySOC', 0.0):.1f} %")
    with m3: st.metric(label="Temperatura Panel", value=f"{ultimo_registro.get('PTemp', 0.0):.1f} °C")
    with m4:
        rain_val = 0.0
        if df_rain is not None:
            df_rain_dia = df_rain[df_rain['TIMESTAMP'].dt.date == fecha_sel]
            if not df_rain_dia.empty: rain_val = df_rain_dia.iloc[-1].get('Rain_day', 0.0)
        st.metric(label="Lluvia el Día", value=f"{rain_val:.2f} mm")

    # --- VENTANA INSPECCIÓN DE IMAGEN CON PUNTOS (FOTO DE LA PERFORACIÓN) ---
    col_img, col_detalles = st.columns([5, 3])
    
    with col_img:
        st.markdown("**🔍 Radiografía de Perforación (Sensores en Profundidad)**")
        img_b64 = get_base64_image(cfg["imagen"])
        if img_b64:
            html_content = f'<div style="position: relative; width: 100%; max-width: 900px; margin: auto;"><img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; border-radius: 8px; box-shadow: 0px 4px 10px rgba(0,0,0,0.2);">'
            for i in range(1, 8):
                vwc = ultimo_registro.get(f"VWC_{cfg['sufijos_vwc'][i]}", 0.0)
                coord = cfg["coordenadas_nodos"][i]
                color_borde = "#00FF00" if vwc >= 0 else "#FF0000"
                texto_vwc = f"{vwc:.1f}%" if vwc >= 0 else "ERROR"
                html_content += f'<div style="position: absolute; top: {coord["top"]}; left: {coord["left"]}; background-color: rgba(20, 25, 35, 0.9); color: #FFFFFF; padding: 4px 8px; border-radius: 6px; font-size: 11px; font-weight: bold; border: 2px solid {color_borde}; transform: translate(-50%, -50%); white-space: nowrap; box-shadow: 2px 2px 5px rgba(0,0,0,0.4);">S{i}: {texto_vwc}</div>'
            html_content += "</div>"
            st.components.v1.html(html_content, height=580)
        else:
            st.warning(f"⚠️ Falta subir la imagen '{cfg['imagen']}' en el repositorio de GitHub para renderizar los puntos.")

    with col_detalles:
        st.markdown("**📋 Datos Detallados del Perfil**")
        tabla_datos = []
        for i in range(1, 8):
            tabla_datos.append({
                "Sensor": f"S{i}",
                "Humedad": f"{ultimo_registro.get(f'VWC_{cfg["sufijos_vwc"][i]}', 0.0):.2f} %",
                "Temperatura": f"{ultimo_registro.get(f'TEMP_{cfg["sufijos_vwc"][i]}', 0.0):.1f} °C",
                "Presión Celda": f"{ultimo_registro.get(f'PT_{cfg["sufijos_pt"][i]}', 0.0):.0f} mbar",
                "Nivel": f"{ultimo_registro.get(f'DPT_{cfg["sufijos_dpt"][i]}', 0.0):.1f} cm"
            })
        st.dataframe(pd.DataFrame(tabla_datos), hide_index=True, use_container_width=True)

    # --- HISTORIAL DESDE LA FECHA SELECCIONADA ---
    st.markdown("---")
    st.markdown(f"**📈 Curvas de Tendencia Histórica (Filtro Dinámico)**")
    fecha_max_grafico = pd.Timestamp(fecha_sel)
    fecha_min_grafico = fecha_max_grafico - pd.Timedelta(days=7)
    df_filtrado = df_data[(df_data['TIMESTAMP'] >= fecha_min_grafico) & (df_data['TIMESTAMP'] <= fecha_max_grafico + pd.Timedelta(days=1))]

    mapeo_variables = {
        "Humedad (VWC %)": [f"VWC_{cfg['sufijos_vwc'][i]}" for i in range(1, 8)],
        "Temperatura (°C)": [f"TEMP_{cfg['sufijos_vwc'][i]}" for i in range(1, 8)],
        "Presión de Celda (mbar)": [f"PT_{cfg['sufijos_pt'][i]}" for i in range(1, 8)],
        "Nivel (cm)": [f"DPT_{cfg['sufijos_dpt'][i]}" for i in range(1, 8)]
    }

    columnas_grafico = mapeo_variables[variable_grafico]
    df_grafico = df_filtrado[['TIMESTAMP'] + columnas_grafico].copy()
    df_grafico.columns = ['Fecha'] + [f"Sensor S{i}" for i in range(1, 8)]
    df_grafico.set_index('Fecha', inplace=True)
    st.line_chart(df_grafico, use_container_width=True)

# 6. EJECUCIÓN POR PESTAÑA
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
