import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN MAESTRA DE LAS ESTACIONES
# ==========================================
# Basada en los archivos del Datalogger .CR1X de DRF y Romeral
ESTACIONES_CONFIG = {
    "DRF": {
        "num_sensores": 7,
        "profundidades": {
            "VWC": [40, 82, 184, 287, 389, 491, 594],
            "PT": [40, 123, 225, 328, 430, 532, 635],
            "TEMP": [40, 40, 40, 40, 40, 40, 40], # En DRF tu cabecera reporta _40cm en todos
            "DPT": [50, 152, 254, 356, 459, 561, 664]
        }
    },
    "Romeral": {
        "num_sensores": 8,
        "profundidades": {
            "VWC": [158, 518, 878, 1239, 1599, 1960, 2320, 2681],
            "PT": [203, 563, 923, 1284, 1644, 2005, 2365, 2726],
            "TEMP": [158, 518, 878, 1239, 1599, 1960, 2320, 2681],
            "DPT": [244, 604, 964, 1325, 1685, 2046, 2406, 2767]
        }
    }
}

NOMBRES_VARIABLES = {
    "VWC": "Contenido Volumétrico de Agua (Humedad)",
    "PT": "Presión de Poros (PT)",
    "TEMP": "Temperatura (TEMP)",
    "DPT": "Nivel Hidrostático Digital (DPT)"
}

# ==========================================
# 2. FUNCIONES DE PROCESAMIENTO DE DATOS
# ==========================================
def cargar_csv_campbell(uploaded_file):
    """Carga un archivo tipo TOA5 de Campbell Scientific saltando metadatos."""
    try:
        # Fila 0: Metadatos, Fila 2: Unidades, Fila 3: Abrev. Mantenemos Fila 1 como header.
        df = pd.read_csv(uploaded_file, skiprows=[0, 2, 3])
        if "TIMESTAMP" in df.columns:
            df["TIMESTAMP"] = pd.to_datetime(df["TIMESTAMP"])
            df.set_index("TIMESTAMP", inplace=True)
        return df
    except Exception as e:
        st.error(f"Error al procesar el archivo CSV: {e}")
        return None

def extraer_datos_sensor(df, tipo_variable, config_estacion):
    """Busca dinámicamente columnas por prefijo y les asigna la profundidad real."""
    resultado = pd.DataFrame(index=df.index)
    profundidades = config_estacion["profundidades"].get(tipo_variable, [])
    
    for idx in range(1, config_estacion["num_sensores"] + 1):
        col_prefix = f"{tipo_variable}_{idx}_"
        # Busca cualquier columna que comience con el prefijo (ej: VWC_1_) sin importar el sufijo de profundidad
        col_real = [c for c in df.columns if c.startswith(col_prefix)]
        
        if col_real:
            col_name = col_real[0]
            prof = profundidades[idx-1] if idx-1 < len(profundidades) else f"S{idx}"
            resultado[f"{prof} cm"] = pd.to_numeric(df[col_name], errors='coerce')
            
    return resultado

# ==========================================
# 3. INTERFAZ DE USUARIO (STREAMLIT APP)
# ==========================================
st.set_page_config(page_title="Dashboard Geotécnico", layout="wide")

st.title("📊 Sistema de Visualización de Estaciones Geotécnicas")
st.markdown("Plataforma unificada para el monitoreo de pozos instrumentados y pluviometría.")

# Sidebar de configuración
st.sidebar.header("⚙️ Configuración")
estacion_sel = st.sidebar.selectbox("1. Selecciona la Estación", ["DRF", "Romeral"])
config = ESTACIONES_CONFIG[estacion_sel]

st.sidebar.markdown("---")
st.sidebar.header("📁 Carga de Datos")
file_datos = st.sidebar.file_uploader(f"Subir archivo principal ({estacion_sel}.csv)", type=["csv"])
file_lluvia = st.sidebar.file_uploader(f"Subir archivo de lluvia ({estacion_sel}Rain.csv)", type=["csv"])

# Pestañas principales de visualización
tab_sensores, tab_lluvia, tab_resumen = st.tabs(["🕳️ Sensores en Pozo", "🌧️ Pluviometría", "📋 Resumen de Archivos"])

# --- PESTAÑA 1: SENSORES EN POZO ---
with tab_sensores:
    st.subheader(f"Monitoreo de Sensores - Estación {estacion_sel}")
    
    if file_datos is not None:
        df_datos = cargar_csv_campbell(file_datos)
        
        if df_datos is not None:
            # Selector del tipo de sensor a graficar
            var_sel = st.selectbox("Selecciona la Variable Geotécnica", list(NOMBRES_VARIABLES.keys()), format_func=lambda x: NOMBRES_VARIABLES[x])
            
            # Extraer las variables mapeadas dinámicamente con sus profundidades
            df_grafico = extraer_datos_sensor(df_datos, var_sel, config)
            
            if not df_grafico.empty:
                # Filtro de rango de fechas dinámico
                fecha_min, fecha_max = df_grafico.index.min().to_pydatetime(), df_grafico.index.max().to_pydatetime()
                rango_fechas = st.slider("Filtrar por Rango de Fechas", min_value=fecha_min, max_value=fecha_max, value=(fecha_min, fecha_max), format="DD/MM/YYYY HH:mm")
                
                # Filtrar DataFrame
                df_filtrado = df_grafico.loc[rango_fechas[0]:rango_fechas[1]]
                
                # Crear gráfico interactivo usando Plotly
                fig = go.Figure()
                for col in df_filtrado.columns:
                    fig.add_trace(go.Scatter(x=df_filtrado.index, y=df_filtrado[col], mode='lines', name=col))
                
                fig.update_layout(
                    title=f"Histórico - {NOMBRES_VARIABLES[var_sel]}",
                    xaxis_title="Fecha y Hora",
                    yaxis_title="Lectura",
                    legend_title="Profundidad",
                    hovermode="x unified",
                    height=550
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Mostrar datos en crudo opcional
                with st.expander("Ver tabla de datos procesados"):
                    st.dataframe(df_filtrado)
            else:
                st.warning(f"No se detectaron columnas con el prefijo '{var_sel}_' en el archivo cargado.")
    else:
        st.info(f"Por favor, carga el archivo `{estacion_sel}.csv` en la barra lateral para ver las gráficas de los sensores.")

# --- PESTAÑA 2: PLUVIOMETRÍA ---
with tab_lluvia:
    st.subheader(f"Datos de Lluvia - Estación {estacion_sel}")
    
    if file_lluvia is not None:
        df_lluvia = cargar_csv_campbell(file_lluvia)
        
        if df_lluvia is not None:
            # Asegurar que existan las columnas de lluvia estándar de Campbell
            cols_lluvia = [c for c in ["Rain_hr", "Rain_day"] if c in df_lluvia.columns]
            
            if cols_lluvia:
                fig_lluvia = go.Figure()
                
                if "Rain_hr" in df_lluvia.columns:
                    fig_lluvia.add_trace(go.Bar(x=df_lluvia.index, y=pd.to_numeric(df_lluvia["Rain_hr"], errors='coerce'), name="Lluvia por Hora (mm/hr)", marker_color='rgb(55, 83, 109)'))
                
                if "Rain_day" in df_lluvia.columns:
                    fig_lluvia.add_trace(go.Scatter(x=df_lluvia.index, y=pd.to_numeric(df_lluvia["Rain_day"], errors='coerce'), mode='lines', name="Lluvia Acumulada Diaria (mm/day)", line=dict(color='rgb(26, 118, 255)', width=2)))
                
                fig_lluvia.update_layout(
                    title=f"Registro Pluviométrico - {estacion_sel}",
                    xaxis_title="Fecha y Hora",
                    yaxis_title="Precipitación (mm)",
                    hovermode="x unified",
                    height=500
                )
                st.plotly_chart(fig_lluvia, use_container_width=True)
            else:
                st.error("El archivo cargado no contiene las columnas estándar 'Rain_hr' o 'Rain_day'.")
    else:
        st.info(f"Por favor, carga el archivo `{estacion_sel}Rain.csv` en la barra lateral para desplegar los datos de lluvia.")

# --- PESTAÑA 3: RESUMEN DE ARCHIVOS ---
with tab_resumen:
    st.subheader("Estructura de las variables detectadas")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(f"**Configuración de la estación {estacion_sel}:**")
        st.write(f"- Cantidad de sensores por variable: `{config['num_sensores']}`")
        st.write("- Profundidades configuradas:")
        st.json(config["profundidades"])
        
    with col2:
        st.markdown("**Vista previa de archivos cargados:**")
        if file_datos is not None:
            st.success(f"✅ Archivo {file_datos.name} cargado.")
        if file_lluvia is not None:
            st.success(f"✅ Archivo {file_lluvia.name} cargado.")
        if file_datos is None and file_lluvia is None:
            st.write("Ningún archivo activo en memoria.")
