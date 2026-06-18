"""
PARCHE app.py — Integración de vms_soil_profile
════════════════════════════════════════════════════════════════
Copia este bloque encima de tu función modal_radiografia() y
reemplaza la función completa por la versión de abajo.

PASO 1 — Agrega el import al inicio de app.py:
────────────────────────────────────────────────
from vms_soil_profile import render_soil_profile

PASO 2 — Reemplaza modal_radiografia() completo:
────────────────────────────────────────────────
"""

# ─────────────────────────────────────────────────────────────
# NUEVA modal_radiografia — pegar en app.py
# ─────────────────────────────────────────────────────────────

MODAL_RADIOGRAFIA_CODE = '''
@st.dialog("🏗️ Radiografía Estructural del Pozo", width="large")
def modal_radiografia(
    id_proyecto: str,
    df_data,
    ultimo_registro,
    cols_vwc, cols_temp, cols_pt, cols_dpt,
    fecha_sel,
    variable_grafico: str,
):
    cfg = CONFIG_PROYECTOS[id_proyecto]

    st.markdown(
        f"""
        <p style="color:#8b949e;font-size:0.85rem;margin-bottom:12px;">
        📍 <b style="color:#58a6ff">{id_proyecto}</b> &nbsp;·&nbsp;
        {cfg['max_sensores']} sensores activos &nbsp;·&nbsp;
        Pasa el cursor sobre un sensor para ver los datos.
        Haz <b>clic</b> para el análisis completo.
        </p>
        """,
        unsafe_allow_html=True,
    )

    # ── SVG dinámico ──────────────────────────────────────────
    html_code = render_soil_profile(
        id_proyecto = id_proyecto,
        cfg         = cfg,
        cols_vwc    = cols_vwc,
        cols_temp   = cols_temp,
        cols_pt     = cols_pt,
        cols_dpt    = cols_dpt,
        ultimo_reg  = ultimo_registro,
    )

    click_index = st.components.v1.html(html_code, height=680, scrolling=False)

    if click_index is not None and click_index != "":
        st.session_state[f"sensor_modal_{id_proyecto}"] = int(click_index)
        st.session_state[f"abrir_radio_{id_proyecto}"]  = False
        st.rerun()

    # ── Acceso rápido por botones (respaldo) ──────────────────
    st.markdown("---")
    st.markdown("##### Acceso directo por sensor:")
    cols_btns = st.columns(cfg["max_sensores"])
    for i, col in enumerate(cols_btns):
        with col:
            prof = _fmt_depth_btn(cols_vwc[i]) if i < len(cols_vwc) else ""
            if st.button(
                f"S{i+1}\\n{prof}",
                key=f"quick_{id_proyecto}_{i}",
                use_container_width=True,
            ):
                st.session_state[f"sensor_modal_{id_proyecto}"] = i
                st.session_state[f"abrir_radio_{id_proyecto}"]  = False
                st.rerun()
'''


# ─────────────────────────────────────────────────────────────
# HELPER que también debes agregar junto al import
# (o puedes importarlo desde vms_soil_profile)
# ─────────────────────────────────────────────────────────────

HELPER_FMT_DEPTH_BTN = '''
def _fmt_depth_btn(col_name: str) -> str:
    """Alias liviano para botones: '40cm' → '0.40m'"""
    try:
        parts = col_name.split("_")
        if len(parts) >= 3:
            cm = float(parts[2].replace("cm", "").replace("CM", ""))
            return f"{cm / 100:.2f}m"
    except Exception:
        pass
    return ""
'''


# ─────────────────────────────────────────────────────────────
# RESUMEN DE CAMBIOS EN app.py
# ─────────────────────────────────────────────────────────────
CHANGES_SUMMARY = """
CAMBIOS NECESARIOS EN app.py
══════════════════════════════════════════════════════

1. ELIMINA en app.py:
   - La función get_base64_image()         → ya no se necesita
   - La función render_imagen_con_pines()  → reemplazada por vms_soil_profile.py
   - El bloque "cfg['imagen']" en CONFIG_PROYECTOS (puedes dejarlo, se ignora)

2. AGREGA al inicio de app.py (junto a los imports):
   from vms_soil_profile import render_soil_profile

3. AGREGA la función _fmt_depth_btn() (ver arriba) en app.py,
   cerca de la función formatear_profundidad() existente.

4. REEMPLAZA modal_radiografia() completo por la versión
   de este archivo (ver MODAL_RADIOGRAFIA_CODE arriba).

5. NO cambia nada más: modal_sensor(), construir_interfaz_proyecto(),
   sidebar, pestañas — todo sigue igual.

ESTRUCTURA DE ARCHIVOS FINAL:
   app.py
   vms_soil_profile.py   ← nuevo
   Romeral.csv
   RomeralRain.csv
   requirements.txt      ← sin cambios (no hay nuevas dependencias)
"""

if __name__ == "__main__":
    print(CHANGES_SUMMARY)
    print("\n── _fmt_depth_btn ──")
    print(HELPER_FMT_DEPTH_BTN)
    print("\n── modal_radiografia ──")
    print(MODAL_RADIOGRAFIA_CODE)
