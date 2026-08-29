# ============================================================
# BLOQUE 1: SUITE DE HERRAMIENTAS GIRO — ENTRADA PRINCIPAL
# ============================================================
"""
Punto de entrada de la suite. Muestra el menú lateral con las
5 herramientas y ejecuta la página elegida.
"""
import os

import streamlit as st

import giro_ui

favicon = giro_ui.resolver_ruta(giro_ui.RUTA_LOGO_ALT)

st.set_page_config(
    page_title="GIRO · Suite de herramientas",
    page_icon=favicon if os.path.exists(favicon) else "🎙️",
    layout="wide",
)

# Identidad visual GIRO en todas las páginas
giro_ui.inyectar_estilo_giro()
giro_ui.header_giro()

# Menú lateral con las 5 herramientas
paginas = st.navigation([
    st.Page("app_pages/1_transcripcion.py", title="Transcripción de cuñas",
            icon=":material/mic:", default=True),
    st.Page("app_pages/6_grabadora.py", title="Grabadora",
            icon=":material/fiber_manual_record:"),
    st.Page("app_pages/2_fotos.py", title="Fotos",
            icon=":material/photo_camera:"),
    st.Page("app_pages/3_documentos.py", title="Documentos",
            icon=":material/description:"),
    st.Page("app_pages/4_audio.py", title="Audio",
            icon=":material/music_note:"),
    st.Page("app_pages/5_video.py", title="Video",
            icon=":material/movie:"),
])
paginas.run()

giro_ui.footer_giro()
# FIN BLOQUE 1
