# ============================================================
# BLOQUE 1: WEB DE TRANSCRIPCIÓN DE CUÑAS — IDENTIDAD GIRO
# ============================================================
import os
import base64
import tempfile

import av
import streamlit as st
from groq import Groq
from faster_whisper import WhisperModel

MODELO_GROQ = "whisper-large-v3-turbo"   # Whisper en la nube (más preciso)
MODELO_LOCAL = "small"                   # Whisper local (alternativa sin Groq)
RUTA_LOGO = "logos/logotipo_pag01_transp.png"   # Logo principal (header)
RUTA_LOGO_ALT = "logos/logotipo_pag24_transp.png"  # Logo secundario (footer/favicon)


def resolver_ruta(ruta_relativa):
    """Encuentra un archivo tanto si la web corre desde la raíz como desde otra carpeta."""
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


@st.cache_resource
def get_cliente_groq():
    """Crea el cliente de Groq UNA sola vez (se reutiliza en cada clic)."""
    return Groq(api_key=cargar_clave_api())


@st.cache_resource
def get_modelo_local():
    """Carga el modelo Whisper local UNA sola vez (la primera tarda un poco)."""
    return WhisperModel(MODELO_LOCAL, device="cpu", compute_type="int8")


def extraer_audio_mp3(ruta_video, carpeta_tmp, nombre_base):
    """Saca el audio del video y lo convierte a mp3 pequeño (mono, 16kHz, 64kbps).
    Si el video es largo, lo divide en trozos de 15 min. Devuelve la lista de mp3."""
    archivos = []
    with av.open(ruta_video) as entrada:
        stream = entrada.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        max_muestras = 900 * 16000
        salida = None
        mp3_stream = None
        muestras = 0

        def cerrar():
            nonlocal salida
            if salida is None:
                return
            for paquete in mp3_stream.encode(None):
                salida.mux(paquete)
            ruta = salida.name
            salida.close()
            if muestras > 0:
                archivos.append(ruta)
            else:
                os.remove(ruta)
            salida = None

        def escribir(rframe):
            nonlocal salida, muestras, mp3_stream
            rframe.pts = None
            if salida is None:
                salida = av.open(os.path.join(carpeta_tmp, f"{nombre_base}_p{len(archivos)+1}.mp3"), "w")
                mp3_stream = salida.add_stream("mp3", rate=16000)
                mp3_stream.bit_rate = 64000
                muestras = 0
            for paquete in mp3_stream.encode(rframe):
                salida.mux(paquete)
            muestras += rframe.samples
            if muestras >= max_muestras:
                cerrar()

        for frame in entrada.decode(stream):
            for rframe in resampler.resample(frame):
                escribir(rframe)
        for rframe in resampler.resample(None):
            escribir(rframe)
        cerrar()
    return archivos


def transcribir_con_groq(client, ruta_mp3):
    """Envía un mp3 a la nube de Groq y devuelve el texto."""
    with open(ruta_mp3, "rb") as f:
        respuesta = client.audio.transcriptions.create(
            file=(os.path.basename(ruta_mp3), f.read()),
            model=MODELO_GROQ,
            language="es",
            response_format="json",
        )
    return respuesta.text


def transcribir_con_local(modelo, ruta_mp3):
    """Transcribe un mp3 con Whisper local y devuelve el texto."""
    segmentos, info = modelo.transcribe(ruta_mp3, language="es", vad_filter=True)
    return " ".join(seg.text.strip() for seg in segmentos)


# ---------- IDENTIDAD CORPORATIVA GIRO ----------
# Paleta: #F32624 (rojo) #CC2A5F (magenta) #FF9723 (naranja) #12E092 (verde)
#          #000000 #636363 #AAA1C8 #C44E79 #EC8112
# Tipografía: CenturyGothic (principal) con respaldo Jost de Google Fonts
def inyectar_estilo_giro():
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
        padding: 32px 36px;
        background: #FFFFFF;
        border-bottom: 4px solid #F32624;
        margin-bottom: 28px;
    }
    .giro-header img {
        max-height: 72px;          /* mínimo digital: 70px */
        width: auto;
    }
    .giro-header h1 {
        margin: 0;
        font-family: 'Century Gothic', 'Jost', sans-serif;
        font-weight: 800;
        font-size: 2rem;
        color: #F32624;
        letter-spacing: 1px;
    }
    .giro-header p {
        margin: 4px 0 0 0;
        color: #636363;
        font-size: 0.95rem;
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

    /* Zona de subida (borde punteado rojo) */
    [data-testid="stFileUploader"] {
        border: 2px dashed #F32624;
        border-radius: 12px;
        padding: 10px;
        background: #FFF8F8;
    }
    [data-testid="stFileUploader"]:hover { border-color: #FF9723; }

    /* Selector de motor: opción activa en rojo GIRO */
    [data-testid="stSegmentedControl"] button {
        font-family: 'Century Gothic', 'Jost', sans-serif;
    }
    [data-testid="stSegmentedControl"] button[aria-checked="true"] {
        background: #F32624;
        color: #FFFFFF;
        border-color: #F32624;
    }

    /* Caja del texto transcrito */
    [data-testid="stTextArea"] textarea {
        border: 2px solid #F32624 !important;
        border-radius: 8px;
        font-family: 'Century Gothic', 'Jost', sans-serif;
    }

    /* Textos de ayuda */
    .stCaption, [data-testid="stCaptionContainer"] p { color: #636363; }

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


# ---------- INTERFAZ ----------
logo_principal = logo_base64(RUTA_LOGO)
logo_secundario = logo_base64(RUTA_LOGO_ALT)
favicon = resolver_ruta(RUTA_LOGO_ALT)

st.set_page_config(
    page_title="GIRO · Transcripción de cuñas",
    page_icon=favicon if os.path.exists(favicon) else "🎙️",
    layout="centered",
)

inyectar_estilo_giro()

# Header con el logotipo (esquina superior izquierda, área de seguridad 2x)
if logo_principal:
    st.markdown(f"""
    <div class="giro-header">
        <img src="data:image/png;base64,{logo_principal}" alt="Logotipo GIRO"/>
        <div>
            <h1>Transcripción de cuñas</h1>
            <p>Sube videos o audios y recibe el texto en español · Descarga el .txt cuando quieras</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
else:
    st.title("Transcripción de cuñas")

archivos = st.file_uploader(
    "Arrastra o elige tus videos/audios",
    type=["mp4", "mov", "avi", "mkv", "webm", "m4v", "wmv",
          "mp3", "wav", "m4a", "ogg", "flac", "aac"],
    accept_multiple_files=True,
)

motor = st.segmented_control(
    "Motor de transcripción",
    options=["Nube (Groq)", "Local"],
    default="Nube (Groq)",
)
st.caption("☁️ Nube = usa la API de Groq (rápida y precisa) · 💻 Local = usa el Whisper del servidor")

if st.button("Transcribir", type="primary"):
    if not archivos:
        st.warning("Primero sube al menos un video o audio.")
    else:
        with tempfile.TemporaryDirectory() as carpeta_tmp:
            total = len(archivos)
            progreso = st.progress(0.0, text="Empezando…")
            for i, archivo in enumerate(archivos):
                ruta_original = os.path.join(carpeta_tmp, archivo.name)
                with open(ruta_original, "wb") as f:
                    f.write(archivo.getbuffer())

                st.subheader(f"🎬 {archivo.name}")
                try:
                    mp3s = extraer_audio_mp3(ruta_original, carpeta_tmp, f"audio_{i}")
                    partes = []
                    for m in mp3s:
                        if motor == "Nube (Groq)":
                            texto = transcribir_con_groq(get_cliente_groq(), m)
                        else:
                            texto = transcribir_con_local(get_modelo_local(), m)
                        if texto.strip():
                            partes.append(texto.strip())
                    texto_final = " ".join(partes)

                    with st.container(border=True):
                        texto_editado = st.text_area("Transcripción", value=texto_final, height=180)
                        st.download_button(
                            "⬇️ Descargar .txt",
                            data=texto_editado,
                            file_name=os.path.splitext(archivo.name)[0] + ".txt",
                            key=f"desc_{i}",
                            type="primary",
                        )
                    st.success("✅ Listo")
                except Exception as e:
                    st.error(f"No pude transcribir {archivo.name}: {e}")
                progreso.progress((i + 1) / total, text=f"{i + 1} de {total}")

# Footer con la identidad GIRO
if logo_secundario:
    st.markdown(f"""
    <div class="giro-footer">
        <img src="data:image/png;base64,{logo_secundario}" alt="GIRO"/>
        <p>© 2026 <strong>GIRO</strong> · Transcripción automática de cuñas · Hecho con Whisper y Groq</p>
    </div>
    """, unsafe_allow_html=True)
# FIN BLOQUE 1
