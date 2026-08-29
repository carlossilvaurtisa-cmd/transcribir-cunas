# ============================================================
# BLOQUE 1: MÓDULO COMPARTIDO — IDENTIDAD GIRO (CSS + helpers)
# ============================================================
"""
Este módulo es el "armario común" de la suite:
- El estilo GIRO (colores, tipografías, botones, barra de progreso)
- El header con el logotipo
- El footer con la identidad de marca
Todas las páginas lo usan para verse iguales.
"""
import os
import base64

import streamlit as st

RUTA_LOGO = "logos/logotipo_pag01_transp.png"      # Logo principal (header)
RUTA_LOGO_ALT = "logos/logotipo_pag24_transp.png"  # Logo secundario (footer/favicon)


def resolver_ruta(ruta_relativa):
    """Encuentra un archivo tanto si la app corre desde la raíz como desde otra carpeta."""
    candidatas = [ruta_relativa, os.path.join(os.path.dirname(os.path.abspath(__file__)), ruta_relativa)]
    for c in candidatas:
        if os.path.exists(c):
            return c
    return ruta_relativa


def logo_base64(ruta):
    """Convierte el PNG del logo a texto base64 para incrustarlo en la página."""
    ruta = resolver_ruta(ruta)
    if not os.path.exists(ruta):
        return None
    with open(ruta, "rb") as f:
        return base64.b64encode(f.read()).decode()


def inyectar_estilo_giro():
    """Inyecta el CSS con la identidad corporativa GIRO."""
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Jost:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        background: #FFFFFF;
        font-family: 'Century Gothic', 'Jost', 'Gotham', sans-serif;
        color: #000000;
    }

    /* Header con logo (área de seguridad 2x: 32px de margen blanco) */
    .giro-header {
        display: flex;
        align-items: center;
        gap: 28px;
        padding: 28px 32px;
        background: #FFFFFF;
        border-bottom: 4px solid #F32624;
        margin-bottom: 20px;
    }
    .giro-header img {
        max-height: 64px;
        width: auto;
    }
    .giro-header h1 {
        margin: 0;
        font-family: 'Century Gothic', 'Jost', sans-serif;
        font-weight: 800;
        font-size: 1.8rem;
        color: #F32624;
        letter-spacing: 1px;
    }
    .giro-header p {
        margin: 4px 0 0 0;
        color: #636363;
        font-size: 0.9rem;
    }

    /* Títulos generales */
    h1, h2, h3 {
        font-family: 'Century Gothic', 'Jost', sans-serif;
        font-weight: 800;
        color: #000000;
        letter-spacing: 0.5px;
    }
    h2 { color: #CC2A5F; }

    /* Botón principal (rojo GIRO) */
    .stButton > button[kind="primary"] {
        background-color: #F32624;
        border: 2px solid #F32624;
        color: #FFFFFF;
        font-family: 'Century Gothic', 'Jost', sans-serif;
        font-weight: 700;
        border-radius: 8px;
        padding: 0.6rem 2.4rem;
        transition: all 0.2s ease;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #CC2A5F;
        border-color: #CC2A5F;
        transform: translateY(-2px);
        color: #FFFFFF;
    }

    /* Zona de subida (borde punteado rojo, SIEMPRE fondo claro y letra negra) */
    [data-testid="stFileUploader"] {
        border: 2px dashed #F32624;
        border-radius: 12px;
        padding: 10px;
        background: #FFFFFF;
    }
    [data-testid="stFileUploader"]:hover { border-color: #FF9723; }
    [data-testid="stFileUploaderDropzone"] {
        background: #FFFFFF;
        color: #000000;
    }
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzone"] button {
        color: #000000;
    }
    [data-testid="stFileUploaderFile"] {
        background: #FFFFFF;
        color: #000000;
    }

    /* Selector de motor: opción activa en rojo GIRO */
    [data-testid="stSegmentedControl"] button {
        font-family: 'Century Gothic', 'Jost', sans-serif;
    }
    [data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: #F32624;
        color: #FFFFFF;
        border-color: #F32624;
    }

    /* Cajas de texto (SIEMPRE fondo blanco y letra negra) */
    [data-testid="stTextArea"] textarea {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 2px solid #F32624 !important;
        border-radius: 8px;
        font-family: 'Century Gothic', 'Jost', sans-serif;
    }
    [data-testid="stTextArea"] label p,
    [data-testid="stWidgetLabel"] p {
        color: #000000;
    }

    /* Barra de progreso GIRO */
    .giro-bar {
        background: #F5E6E6;
        border: 1px solid #F32624;
        border-radius: 10px;
        height: 24px;
        overflow: hidden;
        margin: 14px 0;
    }
    .giro-bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #F32624, #FF9723);
        color: #FFFFFF;
        font-family: 'Century Gothic', 'Jost', sans-serif;
        font-weight: 700;
        font-size: 12px;
        line-height: 24px;
        text-align: center;
        border-radius: 10px;
        transition: width 0.4s ease;
        white-space: nowrap;
        padding: 0 8px;
    }
    .giro-bar-fill.anim {
        width: 100% !important;
        background: repeating-linear-gradient(45deg, #F32624 0 12px, #CC2A5F 12px 24px);
        animation: giro-rayas 1s linear infinite;
    }
    .giro-bar-fill.ok {
        background: #12E092;
    }
    @keyframes giro-rayas {
        from { background-position: 0 0; }
        to { background-position: 34px 0; }
    }
    .giro-estado {
        font-family: 'Century Gothic', 'Jost', sans-serif;
        color: #636363;
        font-size: 0.9rem;
        margin: 6px 0 2px 0;
    }
    .giro-estado strong { color: #F32624; }

    /* Botón de WhatsApp (verde oficial #25D366) */
    .stLinkButton a {
        background-color: #25D366 !important;
        border: 2px solid #25D366 !important;
        color: #FFFFFF !important;
        font-family: 'Century Gothic', 'Jost', sans-serif;
        font-weight: 700;
        border-radius: 8px;
        padding: 0.6rem 1.4rem;
        transition: all 0.2s ease;
    }
    .stLinkButton a:hover {
        background-color: #1DA851 !important;
        border-color: #1DA851 !important;
        color: #FFFFFF !important;
    }

    /* Footer GIRO */
    .giro-footer {
        text-align: center;
        padding: 22px 16px;
        margin-top: 36px;
        border-top: 3px solid #FF9723;
        color: #636363;
        font-size: 0.8rem;
    }
    .giro-footer img { max-height: 40px; opacity: 0.85; }
    .giro-footer strong { color: #F32624; }
    </style>
    """, unsafe_allow_html=True)


def header_giro():
    """Muestra el encabezado con el logotipo GIRO arriba a la izquierda."""
    logo = logo_base64(RUTA_LOGO)
    if logo:
        st.markdown(f"""
        <div class="giro-header">
            <img src="data:image/png;base64,{logo}" alt="Logotipo GIRO"/>
            <div>
                <h1>Suite de herramientas</h1>
                <p>Transcripción · Fotos · Documentos · Audio · Video</p>
            </div>
        </div>
        """, unsafe_allow_html=True)


def footer_giro():
    """Muestra el pie de página con la identidad GIRO."""
    logo = logo_base64(RUTA_LOGO_ALT)
    if logo:
        st.markdown(f"""
        <div class="giro-footer">
            <img src="data:image/png;base64,{logo}" alt="GIRO"/>
            <p>© 2026 <strong>GIRO</strong> · Suite de herramientas para periodistas y fotógrafos</p>
        </div>
        """, unsafe_allow_html=True)


def barra_progreso(pct, animado=False, ok=False):
    """Genera el HTML de la barra de progreso con colores GIRO."""
    if animado:
        return '<div class="giro-bar"><div class="giro-bar-fill anim">Procesando…</div></div>'
    clase = "giro-bar-fill ok" if ok else "giro-bar-fill"
    texto = "✅ ¡Completado!" if ok else f"{pct}%"
    return f'<div class="giro-bar"><div class="{clase}" style="width:{pct}%">{texto}</div></div>'


def cargar_clave_api():
    """Busca la clave de Groq: primero en variables del entorno (nube),
    luego en el archivo .env (si se ejecuta en tu PC)."""
    clave = os.environ.get("GROQ_API_KEY", "")
    if not clave and os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8") as f:
            for linea in f:
                linea = linea.strip()
                if linea.startswith("GROQ_API_KEY"):
                    clave = linea.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    return clave or None
# FIN BLOQUE 1
