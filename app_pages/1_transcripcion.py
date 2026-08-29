# ============================================================
# BLOQUE 1: HERRAMIENTA 1 — TRANSCRIPCIÓN DE CUÑAS
# ============================================================
import os
import tempfile
import urllib.parse

import av
import streamlit as st
from groq import Groq
from faster_whisper import WhisperModel

import giro_ui

MODELO_GROQ = "whisper-large-v3-turbo"   # Whisper en la nube (más preciso)
MODELO_LOCAL = "small"                   # Whisper local (alternativa sin Groq)


@st.cache_resource
def get_cliente_groq():
    """Crea el cliente de Groq UNA sola vez (se reutiliza en cada clic)."""
    return Groq(api_key=giro_ui.cargar_clave_api())


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
st.title("🎙️ Transcripción de cuñas")
st.caption("Sube videos o audios y recibe el texto en español. Descarga el .txt o compártelo por WhatsApp.")

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
            estado = st.empty()
            progreso = st.empty()
            for i, archivo in enumerate(archivos):
                ruta_original = os.path.join(carpeta_tmp, archivo.name)
                with open(ruta_original, "wb") as f:
                    f.write(archivo.getbuffer())

                st.subheader(f"🎬 {archivo.name}")
                try:
                    estado.markdown(
                        f'<p class="giro-estado"><strong>{archivo.name}</strong> — extrayendo audio…</p>',
                        unsafe_allow_html=True,
                    )
                    progreso.markdown(giro_ui.barra_progreso(0, animado=True), unsafe_allow_html=True)

                    mp3s = extraer_audio_mp3(ruta_original, carpeta_tmp, f"audio_{i}")
                    partes = []
                    for j, m in enumerate(mp3s):
                        estado.markdown(
                            f'<p class="giro-estado"><strong>{archivo.name}</strong> — transcribiendo (parte {j+1} de {len(mp3s)})…</p>',
                            unsafe_allow_html=True,
                        )
                        if motor == "Nube (Groq)":
                            texto = transcribir_con_groq(get_cliente_groq(), m)
                        else:
                            texto = transcribir_con_local(get_modelo_local(), m)
                        if texto.strip():
                            partes.append(texto.strip())
                    texto_final = " ".join(partes)

                    with st.container(border=True):
                        texto_editado = st.text_area("Transcripción", value=texto_final, height=180)
                        c_desc, c_wa = st.columns(2)
                        with c_desc:
                            st.download_button(
                                "⬇️ Descargar .txt",
                                data=texto_editado,
                                file_name=os.path.splitext(archivo.name)[0] + ".txt",
                                key=f"desc_{i}",
                                type="primary",
                            )
                        with c_wa:
                            # Botón que abre WhatsApp con la transcripción lista para enviar
                            mensaje = f"🎙️ Transcripción de {archivo.name}:\n\n{texto_editado}"[:4000]
                            url_wa = "https://wa.me/?text=" + urllib.parse.quote(mensaje)
                            st.link_button("📲 Compartir por WhatsApp", url_wa)
                    st.success("✅ Listo")
                except Exception as e:
                    st.error(f"No pude transcribir {archivo.name}: {e}")
                pct = int((i + 1) / total * 100)
                progreso.markdown(giro_ui.barra_progreso(pct), unsafe_allow_html=True)
                estado.markdown(
                    f'<p class="giro-estado"><strong>{archivo.name}</strong> — transcripción completa ✅</p>',
                    unsafe_allow_html=True,
                )
            # Barra final en verde GIRO
            progreso.markdown(giro_ui.barra_progreso(100, ok=True), unsafe_allow_html=True)
            estado.markdown('<p class="giro-estado"><strong>🎉 ¡Todo transcrito!</strong> Descarga los .txt de cada cuña.</p>', unsafe_allow_html=True)
# FIN BLOQUE 1
