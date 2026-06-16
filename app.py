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

# REINGENIERÍA VISUAL: CSS para inyectar los pines directamente sobre la imagen grande
st.markdown("""
    <style>
    /* Contenedor relativo para la imagen grande */
    .contenedor-mapa-relativo {
        position: relative;
        width: 100%;
        max-width: 600px; /* Imagen mucho más grande y comercial */
        margin: 0 auto;
        border-radius: 12px;
        box-shadow: 0px 10px 30px rgba(0,0,0,0.15);
        background-color: #f8f9fa;
        padding: 6px;
    }
    .imagen-estratigrafica {
        width: 100%;
        display: block;
        border-radius: 8px;
    }
    /* Estilo de los contenedores de botones de Streamlit para transformarlos en Pines flotantes */
    .zona-pin-flotante {
        position: absolute;
        left: 45%; /* Ajuste horizontal sobre la línea del pozo */
        transform: translate(-50%, -50%);
        z-index: 999;
    }
    /* Estilo premium para los botones simulando pines de geolocalización */
    div.stButton > button {
        background-color: #0F172A !important;
        color: #007BFF !important;
        border: 2px solid #007BFF !important;
        border-radius: 50% !important;
        width: 36px !important;
        height: 36px !important;
        padding: 0 !important;
        font-size: 16px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 0 12px rgba(0,123,255,0.6) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button:hover {
        background-color: #007BFF !important;
        color: white !important;
        border-color: white !important;
        transform: scale(1.2) !important;
        box-shadow: 0 0 18px rgba(0,123,255,0.9) !important;
    }
    </style>
""", unsafe_allow_html=True)

# 2. CONFIGURACIÓN DE PARÁMETROS Y ALTURAS DE PINES (DRF: 7 | ROMERAL: 8)
CONFIG_PROYECTOS = {
    "DRF": {
        "csv_data": "Romeral.csv",  
        "csv_rain": "RomeralRain.csv",
        "imagen": "DRF.jpg", 
        "lat": -28.493772,  
        "lon": -71.254531,
        "max_sensores": 7,
        # Coordenadas en % (de arriba a abajo) para encajar sobre las marcas del pozo DRF.jpg
        "posiciones_y": [15, 24, 33, 42, 51, 60, 69]
    },
    "ROMERAL": {
        "csv_data": "Romeral.csv", 
        "csv_rain": "RomeralRain.csv",
        "imagen": "Romeral.jpg", 
        "lat": -29.726153,  
        "lon": -71.221878,
        "max_sensores": 8,
        # Coordenadas en % para encajar sobre las marcas del pozo Romeral.jpg
        "posiciones_y": [12, 20, 28, 36, 44, 52, 60, 68]
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

# 3. PANEL LATERAL DE CONTROL
st.sidebar.image("https://sensoil.com/wp-content/uploads/2021/04/Sensoil-Logo-Vertical.png", width=140)
st.sidebar.title("VMS GeoCloud Dashboard")
st.sidebar.markdown("---")

df_rom_aux, _, _ = cargar_datos_proyecto("ROMERAL")
fechas_sim = sorted(df_rom_aux['TIMESTAMP'].dt.date.unique(), reverse=True) if df_rom_aux is not None else []

fecha_sel = st.sidebar.selectbox("Selecciona Fecha de Simulación:", fechas_sim, key="global_fecha_sel")
variable_grafico = st.sidebar.selectbox("Variable para Gráfico Histórico:", ["Humedad (VWC %)", "Temperatura (°C)", "Presión de Celda (mbar)", "Nivel (cm)"], key="global_var_sel")

st.sidebar.markdown("---")
st.sidebar.warning("💡 **Instrucciones de Uso:**\n1. Haz clic en el marcador azul del mapa.\n2. Aparecerá la radiografía técnica ampliada abajo.\n3. Presiona **cualquier marcador azul (📍)** montado encima de la imagen del pozo para abrir la telemetría.")


# 4. MODAL FLOTANTE: DETALLE ANALÍTICO DE LECTURAS Y CURVAS DE TENDENCIA
@st.dialog("📊 Desglose Analítico del Sensor", width="large")
def mostrar_modal_datos_sensor(id_proyecto, idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt):
    c_vwc = cols_vwc[idx] if idx < len(cols_vwc) else None
    c_temp = cols_temp[idx] if idx < len(cols_temp) else None
    c_pt = cols_pt[idx] if idx < len(cols_pt) else None
    c_dpt = cols_dpt[idx] if idx < len(cols_dpt) else None

    prof_legible = formatear_profundidad(c_vwc) if c_vwc else "N/A"

    st.markdown(f"### 🔍 Canal Sensor S{idx+1} ({prof_legible}) — Faena {id_proyecto}")
    st.caption(f"📅 Fecha y Hora del Reporte: {ultimo_registro['TIMESTAMP'].strftime('%Y-%m-%d %H:%M:%S')}")
    st.markdown("---")

    # Tarjetas de Métricas de Alta Fidelidad
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric(label="Humedad Volumétrica (VWC)", value=f"{ultimo_registro.get(c_vwc, 0.0):.2f} %" if c_vwc else "N/A")
    with m2: st.metric(label="Temperatura Suelo", value=f"{ultimo_registro.get(c_temp, 0.0):.1f} °C" if c_temp else "N/A")
    with m3: st.metric(label="Presión de Poros", value=f"{ultimo_registro.get(c_pt, 0.0):.0f} mbar" if c_pt else "N/A")
    with m4: st.metric(label="Nivel Hidrostático", value=f"{ultimo_registro.get(c_dpt, 0.0):.1f} cm" if c_dpt else "N/A")

    st.markdown("---")
    st.markdown(f"#### 📈 Curva Histórica de Variación Dinámica (Últimos 7 días) — {variable_grafico}")

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


# 5. ASIGNACIÓN Y CONTROL EN LAS PESTAÑAS PRINCIPALES
tab_drf, tab_romeral = st.tabs(["📍 Estación DRF Chile", "📍 Estación El Romeral"])

def construir_interfaz_proyecto(id_proyecto):
    cfg = CONFIG_PROYECTOS[id_proyecto]
    df_data, _, error = cargar_datos_proyecto(id_proyecto)
    
    if error or df_data is None:
        st.error(error)
        return

    # Mapeo exacto respetando las cantidades nativas (DRF: 7 sensores | Romeral: 8 sensores)
    num_sens = cfg["max_sensores"]
    cols_vwc = sorted([c for c in df_data.columns if c.startswith('VWC_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_temp = sorted([c for c in df_data.columns if c.startswith('TEMP_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_pt = sorted([c for c in df_data.columns if c.startswith('PT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]
    cols_dpt = sorted([c for c in df_data.columns if c.startswith('DPT_')], key=lambda x: int(x.split('_')[1]) if x.split('_')[1].isdigit() else 0)[:num_sens]

    df_dia = df_data[df_data['TIMESTAMP'].dt.date == fecha_sel]
    if df_dia.empty:
        st.warning("No hay registros telemétricos cargados para esta fecha en el servidor.")
        return
    ultimo_registro = df_dia.iloc[-1]

    st.subheader(f"🗺️ Geolocalización Satelital Continua — {id_proyecto}")
    
    m = folium.Map(location=[cfg["lat"], cfg["lon"]], zoom_start=16)
    folium.TileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', attr='Esri', name='Satelital', control=False).add_to(m)
    folium.Marker([cfg["lat"], cfg["lon"]], tooltip=f"Desplegar Infraestructura Interna {id_proyecto}", icon=folium.Icon(color="blue", icon="info-sign")).add_to(m)

    mapa_output = st_folium(m, width="100%", height=400, key=f"mapa_comercial_{id_proyecto}")

    if f"ver_perfil_{id_proyecto}" not in st.session_state:
        st.session_state[f"ver_perfil_{id_proyecto}"] = False

    if mapa_output and mapa_output.get("last_object_clicked"):
        st.session_state[f"ver_perfil_{id_proyecto}"] = True

    # --- SECCIÓN INTEGRADA DEL POZO EN TAMAÑO REAL Y PINES FLOTANTES DIRECTOS ---
    if st.session_state[f"ver_perfil_{id_proyecto}"]:
        st.markdown("---")
        st.markdown(f"### 📸 Radiografía de Infraestructura de Pozos y Perfil Estratigráfico: {id_proyecto}")
        st.caption("Los puntos geolocalizados han sido montados sobre las marcas reales de profundidad. Presione cualquiera de ellos para ver la data:")
        
        img_b64 = get_base64_image(cfg["imagen"])
        
        if img_b64:
            # Iniciamos el contenedor HTML con la radiografía gigante de fondo
            st.markdown(f"""
            <div class="contenedor-mapa-relativo">
                <img src="data:image/jpeg;base64,{img_b64}" class="imagen-fondo">
            """, unsafe_allow_html=True)
            
            # Insertamos los botones interactivos nativos exactamente sobre las marcas de la foto
            for idx in range(num_sens):
                col_name = cols_vwc[idx]
                prof_label = formatear_profundidad(col_name)
                y_pos = cfg["posiciones_y"][idx]
                
                # Inyección del contenedor posicionado con CSS absoluto
                st.markdown(f'<div class="zona-pin-flotante" style="top: {y_pos}%;">', unsafe_allow_html=True)
                
                # El botón de Streamlit se dibuja en el punto exacto, capturando el clic
                if st.button("📍", key=f"pin_real_{id_proyecto}_{idx}", help=f"Sensor S{idx+1} ({prof_label})"):
                    mostrar_modal_datos_sensor(id_proyecto, idx, df_data, ultimo_registro, cols_vwc, cols_temp, cols_pt, cols_dpt)
                    
                st.markdown('</div>', unsafe_allow_html=True)
                
            # Cerramos el contenedor principal
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
        else:
            st.error(f"Falta el archivo gráfico {cfg['imagen']} para renderizar la radiografía.")

with tab_drf:
    construir_interfaz_proyecto("DRF")

with tab_romeral:
    construir_interfaz_proyecto("ROMERAL")
