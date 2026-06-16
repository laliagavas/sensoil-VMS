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

# 2. CONFIGURACIÓN DE RUTAS DE TUS BUCKETS REALES EN SUPABASE
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "https://jmnmzfybubcasaihmhqb.supabase.co/storage/v1/object/public/DRF/DRF.csv",
        "csv_rain": "https://jmnmzfybubcasaihmhqb.supabase.co/storage/v1/object/public/DRF/DRFRain.csv",
        "imagen": "DRR.jpg", 
        "lat": -28.493772,  
        "lon": -71.254531,  
        "coordenadas_nodos": {
            1: {"top": "24%", "left": "51%"},
            2: {"top": "33%", "left": "51%"},
            3: {"top": "42%", "left": "51%"},
            4: {"top": "51%", "left": "51%"},
            5: {"top": "60%", "left": "51%"},
            6: {"top": "69%", "left": "51%"},
            7: {"top": "78%", "left": "51%"}
        },
        "sufijos_vwc": {1: "1_40cm", 2: "2_82cm", 3: "3_184cm", 4: "4_287cm", 5: "5_389cm", 6: "6_491cm", 7: "7_594cm"},
        "sufijos_pt": {1: "1_40cm", 2: "2_123cm", 3: "3_225cm", 4: "4_328cm", 5: "5_430cm", 6: "6_532cm", 7: "7_635cm"},
        "sufijos_dpt": {1: "1_50cm", 2: "2_152cm", 3: "3_254cm", 4: "4_356cm", 5: "5_459cm", 6: "6_561cm", 7: "7_664cm"}
    },
    "ROMERAL": {
        "csv_data": "https://jmnmzfybubcasaihmhqb.supabase.co/storage/v1/object/public/Romeral/DRF.csv", 
        "csv_rain": "https://jmnmzfybubcasaihmhqb.supabase.co/storage/v1/object/public/Romeral/DRFRain.csv",
        "imagen": "Romeral.jpg", 
        "lat": -29.726153,  
        "lon": -71.221878,  
        "coordenadas_nodos": {
            1: {"top": "24%", "left": "51%"},
            2: {"top": "33%", "left": "51%"},
            3: {"top": "42%", "left": "51%"},
            4: {"top": "51%", "left": "51%"},
            5: {"top": "60%", "left": "51%"},
            6: {"top": "69%", "left": "51%"},
            7: {"top": "78%", "left": "51%"}
        },
        "sufijos_vwc": {1: "1_40cm", 2: "2_82cm", 3: "3_184cm", 4: "4_287cm", 5: "5_389cm", 6: "6_491cm", 7: "7_594cm"},
        "sufijos_pt": {1: "1_40cm", 2: "2_123cm", 3: "3_225cm", 4: "4_328cm", 5: "5_430cm", 6: "6_532cm", 7: "7_635cm"},
        "sufijos_dpt": {1: "1_50cm", 2: "2_152cm", 3: "3_254cm", 4: "4_356cm", 5: "5_459cm", 6: "6_561cm", 7: "7_664cm"}
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
        return None, None, f"Error al descargar o procesar los datos desde la nube: {e}"

# 4. BARRA LATERAL (BRANDING CORPORATIVO)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")
st.sidebar.info("💡 **Uso para Clientes:** Navegue entre las pestañas de las faenas mineras, explore el mapa satelital interactivo y seleccione un día de operación en el menú para simular el comportamiento histórico.")

# 5. ESTRUCTURA DE PESTAÑAS PRINCIPALES
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, df_rain, error = cargar_datos_proyecto(id_proyecto)
    
    if error:
        st.error(error)
        st.info("💡 **Ajuste de Supabase requerido:** Asegúrate de que los buckets **'DRF'** y **'Romeral'** estén configurados como **PUBLIC** en las opciones de Supabase Storage.")
        return

    # --- MAPA SATELITAL REAL ---
    st.subheader("🗺️ Ubicación Satelital en Faena")
    
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer(
        tiles='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
        attr='Esri World Imagery',
        name='Vista Satelital',
        overlay=False,
        control=False
    ).add_to(m)

    popup_text = f"""
    <div style='font-family: Arial, sans-serif; width: 200px;'>
        <h4 style='color:#007BFF; margin-bottom:5px;'>Sistema VMS Sensoil</h4>
        <p style='margin:0;'><b>Faena:</b> {id_proyecto}</p>
        <p style='margin:0;'><b>Estado:</b> Conectado Cloud</p>
    </div>
    """
    folium.Marker(
        [cfg["lat"], cfg["lon"]],
        popup=popup_text,
        tooltip=f"Ver Estación {id_proyecto}",
        icon=folium.Icon(color="blue", icon="info-sign")
    ).add_to(m)

    st_folium(m, width="100%", height=320, key=f"mapa_{id_proyecto}")
    st.markdown("---")
    
    fechas_disponibles = df_data['TIMESTAMP'].dt.date.unique()
    
    col_ctrl1, col_ctrl2 = st.columns([4, 4])
    with col_ctrl1:
        fecha_sel = st.selectbox(f"Selecciona un día histórico para la Demostración ({id_proyecto}):", sorted(fechas_disponibles, reverse=True), key=f"sel_fecha_{id_proyecto}")
    with col_ctrl2:
        variable_grafico = st.selectbox("Variable para Tendencia Histórica:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key=f"sel_var_{id_proyecto}")

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    ultimo_registro = df_dia.iloc[-1]
    ultima_fecha = ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')

    st.subheader(f"📊 Estado Analítico del Perfil | Registro Seleccionado: {ultima_fecha}")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Voltaje del Sistema", value=f"{ultimo_registro.get('Batt_volt_Min', 0.0):.2f} V")
    with m2: st.metric(label="Estado de Carga (SOC)", value=f"{ultimo_registro.get('BatterySOC', 0.0):.1f} %")
    with m3: st.metric(label="Temperatura Datalogger", value=f"{ultimo_registro.get('PTemp', 0.0):.1f} °C")
    with m4:
        rain_val = 0.0
        if df_rain is not None:
            df_rain_dia = df_rain[df_rain['TIMESTAMP'].dt.date == fecha_sel]
            if not df_rain_dia.empty: rain_val = df_rain_dia.iloc[-1].get('Rain_day', 0.0)
        st.metric(label="Precipitación del Día", value=f"{rain_val:.2f} mm")

    # --- RADIOGRAFÍA INTERACTIVA ---
    col_img, col_detalles = st.columns([5, 3])
    
    with col_img:
        st.markdown("**🔍 Radiografía de Perforación (Monitoreo en Profundidad VMS)**")
        img_b64 = get_base64_image(cfg["imagen"])
        if img_b64:
            html_content = f'<div style="position: relative; width: 100%; max-width: 500px; margin: auto;"><img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; border-radius: 8px; box-shadow: 0px 4px 12px rgba(0,0,0,0.15);">'
            for i in range(1, 8):
                sufijo = cfg["sufijos_vwc"][i]
                vwc = ultimo_registro.get(f"VWC_{sufijo}", 0.0)
                coord = cfg["coordenadas_nodos"][i]
                color_borde = "#28A745" if vwc >= 0 else "#DC3545"
                texto_vwc = f"{vwc:.1f}%" if vwc >= 0 else "ERROR"
                html_content += f'<div style="position: absolute; top: {coord["top"]}; left: {coord["left"]}; background-color: rgba(15, 23, 42, 0.95); color: #FFFFFF; padding: 3px 8px; border-radius: 4px; font-size: 11px; font-weight: bold; border: 2px solid {color_borde}; transform: translate(-50%, -50%); white-space: nowrap; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">S{i}: {texto_vwc}</div>'
            html_content += "</div>"
            st.components.v1.html(html_content, height=620)
        else:
            st.error(f"❌ Error: No se encontró el archivo visual '{cfg['imagen']}' en tu GitHub.")

    with col_detalles:
        st.markdown("**📋 Matriz Completa de Sensores**")
        tabla_datos = []
        for i in range(1, 8):
            suf_vwc = cfg["sufijos_vwc"][i]
            suf_pt = cfg["sufijos_pt"][i]
            suf_dpt = cfg["sufijos_dpt"][i]
            
            val_vwc = ultimo_registro.get(f"VWC_{suf_vwc}", 0.0)
            val_temp = ultimo_registro.get(f"TEMP_{suf_vwc}", 0.0)
            val_pt = ultimo_registro.get(f"PT_{suf_pt}", 0.0)
            val_dpt = ultimo_registro.get(f"DPT_{suf_dpt}", 0.0)
            
            tabla_datos.append({
                "Sensor": f"S{i}",
                "Humedad (VWC)": f"{val_vwc:.2f} %",
                "Temperatura": f"{val_temp:.1f} °C",
                "Presión Celda": f"{val_pt:.0f} mbar",
                "Nivel Fijo": f"{val_dpt:.1f} cm"
            })
        st.dataframe(pd.DataFrame(tabla_datos), hide_index=True, use_container_width=True)

    # --- GRÁFICO HISTÓRICO ---
    st.markdown("---")
    st.markdown(f"**📈 Curvas de Variación Temporal (Ventana de 7 días hacia atrás)**")
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

# 6. ASIGNACIÓN DE CONTENIDO A LAS PESTAÑAS
with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
