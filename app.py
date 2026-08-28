# ============================================================
# BLOQUE 1: WEB DE TRANSCRIPCIÓN DE CUÑAS (VERSIÓN NUBE)
# ============================================================
import os
import tempfile

import av
import streamlit as st
from groq import Groq
from faster_whisper import WhisperModel

MODELO_GROQ = "whisper-large-v3-turbo"   # Whisper en la nube (más preciso)
MODELO_LOCAL = "small"                   # Whisper local (alternativa sin Groq)


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


# ---------- INTERFAZ ----------
st.set_page_config(page_title="Transcripción de cuñas", page_icon="🎙️")
st.title("🎙️ Transcripción de cuñas")
st.caption("Sube videos o audios y recibe el texto. Descarga el .txt cuando quieras.")

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
                        )
                    st.success("✅ Listo")
                except Exception as e:
                    st.error(f"No pude transcribir {archivo.name}: {e}")
                progreso.progress((i + 1) / total, text=f"{i + 1} de {total}")
# FIN BLOQUE 1
