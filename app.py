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

# 2. CONFIGURACIÓN GEOGRÁFICA Y DE SENSORES (DRF: 7 | ROMERAL: 8)
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "Romeral.csv",  
        "csv_rain": "RomeralRain.csv",
        "imagen": "DRF.jpg", 
        "lat": -28.493772,  
        "lon": -71.254531,
        "max_sensores": 7,
        # Alturas verticales exactas (%) donde se dibujarán los pines sobre la línea del pozo en DRF.jpg
        "pines_y": [22, 31, 40, 49, 58, 67, 76]
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv", 
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg", 
        "lat": -29.726153,  
        "lon": -71.221878,
        "max_sensores": 8,
        # Alturas verticales exactas (%) donde se dibujarán los pines sobre la línea del pozo en Romeral.jpg
        "pines_y": [18, 26, 34, 42, 50, 58, 66, 74]
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

# 3. BARRA LATERAL (CONTROL DE SIMULACIÓN GLOBAL)
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")

df_rom_aux, _, _ = cargar_datos_proyecto("ROMERAL")
fechas_sim = sorted(df_rom_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_rom_aux is not None else []

fecha_sel = st.sidebar.selectbox("Selecciona Fecha de Simulación:", fechas_sim, key="global_fecha_sel")
variable_grafico = st.sidebar.selectbox("Variable para Tendencia:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key="global_var_sel")


# 4. VENTANA EMERGENTE MAESTRA (ST.DIALOG): RADIOGRAFÍA E INFRAESTRUCTURA DE INTERACCIÓN DIRECTA
@st.dialog("📸 Radiografía Estructural del Pozo", width="large")
def abrir_modal_radiografia_interactiva(id_proyecto, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    img_b64 = get_base64_image(cfg["imagen"])
    
    # Manejo de estados internos para saber si el usuario hizo clic en un pin de la foto
    if f"sensor_activo_{id_proyecto}" not in st.session_state:
        st.session_state[f"sensor_activo_{id_proyecto}"] = None

    # Si NO se ha seleccionado un sensor, se muestra la foto grande con los pines ADENTRO
    if st.session_state[f"sensor_activo_{id_proyecto}"] is None:
        st.markdown(f"### Perfil Estratigráfico Vertical — Pozo {id_proyecto}")
        st.caption("Haga clic directamente sobre los pines flotantes dispuestos sobre las cotas del pozo para auditar los gráficos telemétricos.")
        st.markdown("---")
        
        if img_b64:
            # Construcción del HTML y CSS absoluto inyectado para obligar a los pines a vivir DENTRO de la foto
            html_pines = ""
            for idx in range(cfg["max_sensores"]):
                col_name = cols_vwc[idx]
                prof_label = formatear_profundidad(col_name)
                top_pos = cfg["pines_y"][idx]
                
                # Cada pin es un enlace HTML que aprovecha los parámetros de query nativos para capturar la acción
                html_pines += f"""
                <a href="?target_sensor={idx}" target="_top" style="text-decoration: none;">
                    <div style="position: absolute; top: {top_pos}%; left: 50%; transform: translate(-50%, -50%); z-index: 9999; display: flex; align-items: center; cursor: pointer;">
                        <div style="width: 18px; height: 18px; background-color: #007BFF; border: 2px solid #FFFFFF; border-radius: 50%; box-shadow: 0 0 12px rgba(0,123,255,0.9);"></div>
                        <div style="background-color: #0F172A; color: #FFFFFF; font-family: 'Arial', sans-serif; font-size: 11px; font-weight: bold; padding: 2px 8px; border-radius: 12px; margin-left: 6px; border: 1px solid rgba(255,255,255,0.2); white-space: nowrap; box-shadow: 2px 2px 6px rgba(0,0,0,0.3);">
                            📍 S{idx+1} ({prof_label})
                        </div>
                    </div>
                </a>
                """

            # Renderizado en alta resolución de la imagen con su capa de pines fija e inamovible
            st.markdown(f"""
            <div style="position: relative; width: 100%; max-width: 480px; margin: 0 auto; background-color: #f8f9fa; border-radius: 12px; padding: 12px; box-shadow: 0px 10px 25px rgba(0,0,0,0.15);">
                <img src="data:image/jpeg;base64,{img_b64}" style="width: 100%; display: block; border-radius: 8px;">
                {html_pines}
            </div>
            """, unsafe_allow_html=True)
        else:
            st.error(f"Falta el archivo gráfico {cfg['imagen']} en la raíz del proyecto.")

    # Si se detecta una selección, transformamos el espacio del modal en el visor analítico de datos
    else:
        idx = st.session_state[f"sensor_activo_{id_proyecto}"]
        c_vwc = cols_vwc[idx]
        c_temp = cols_temp[idx] if idx < len(cols_temp) else None
        c_pt = cols_pt[idx] if idx < len(cols_pt) else None
        c_dpt = cols_dpt[idx] if idx < len(cols_dpt) else None
        prof_legible = formatear_profundidad(c_vwc)

        st.markdown(f"### 📊 Análisis Telemétrico: Sensor S{idx+1} ({prof_legible}) — {id_proyecto}")
        st.caption(f"📅 Ventana de Registro: {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
        st.markdown("---")

        # Fila de KPIS
        k1, k2, k3, k4 = st.columns(4)
        with k1: st.metric(label="Humedad (VWC)", value=f"{ultimo_registro.get(c_vwc, 0.0):.2f} %")
        with k2: st.metric(label="Temperatura Suelo", value=f"{ultimo_registro.get(c_temp, 0.0):.1f} °C" if c_temp else "N/A")
        with k3: st.metric(label="Presión de Poros", value=f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar" if c_pt else "N/A")
        with k4: st.metric(label="Nivel Hidrostático", value=f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm" if c_dpt else "N/A")

        st.markdown("---")
        st.markdown(f"#### 📈 Tendencia de Variación Dinámica (Últimos 7 días) — {variable_grafico}")

        # Gráfico histórico lineal
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

        # Botón de retorno limpio para volver a ver la imagen con sus pines
        if st.button("⬅️ Volver a la Radiografía", use_container_width=True):
            st.session_state[f"sensor_activo_{id_proyecto}"] = None
            st.query_params.clear()
            st.rerun()


# 5. ESCUCHA ACTIVA DE CLICS EN LOS PINES DE LA FOTO (QUERY PARAMS)
# Si se detecta el clic de la URL, se mapea al estado interno de la sesión de Streamlit
params = st.query_params
if "target_sensor" in params:
    sensor_idx = int(params["target_sensor"])
    # Se detecta automáticamente qué pestaña está activa para actualizar el proyecto correspondiente
    st.session_state["sensor_activo_DRF"] = sensor_idx
    st.session_state["sensor_activo_ROMERAL"] = sensor_idx


# 6. ESTRUCTURACIÓN DE PESTAÑAS PRINCIPALES DEL DASHBOARD
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, _, error = cargar_datos_proyecto(id_proyecto)
    
    if error or df_data is None:
        st.error(error)
        return

    # Separación y conteo exacto (DRF: 7 | Romeral: 8)
    num_sens = cfg["max_sensores"]
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("No hay registros disponibles para la fecha seleccionada.")
        return
    ultimo_registro = df_dia.iloc[-1]

    st.subheader(f"🗺️ Geolocalización Satelital Continua — {id_proyecto}")
    
    # Construcción del mapa satelital Folium
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satelital', control=False).add_to(m)
    folium.Marker([cfg["lat"], cfg["lon"]], tooltip=f"Haga clic aquí para desplegar la radiografía de {id_proyecto}", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

    mapa_output = st_folium(m, width="100%", height=450, key=f"mapa_full_v3_{id_proyecto}")

    # GATILLO: Al presionar el punto del mapa o si hay un sensor activo por el click de la foto, se despliega la ventana flotante grande
    if (mapa_output and mapa_output.get("last_object_clicked")) or (st.session_state.get(f"sensor_activo_{id_proyecto}") is not None):
        abrir_modal_radiografia_interactiva(id_proyecto, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
