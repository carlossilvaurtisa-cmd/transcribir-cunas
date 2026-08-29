# ============================================================
# BLOQUE 1: HERRAMIENTA 6 — YOUTUBE (DESCARGAR AUDIO/VIDEO)
# ============================================================
import io
import os
import tempfile

import av
import streamlit as st
import yt_dlp

import giro_ui

# Límites razonables para la nube (memoria del servidor gratis)
MAX_DURACION_NUBE = 20 * 60      # 20 minutos
MAX_PESO_NUBE_MB = 400

# "Disfraz" de navegador: YouTube bloquea descargas sin estos datos
UA_CHROME = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
             "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")


def opciones_base():
    """Opciones comunes para yt-dlp que evitan el bloqueo 403 de YouTube."""
    return {
        "quiet": True,
        "no_warnings": True,
        "nocheckcertificate": True,
        "http_headers": {
            "User-Agent": UA_CHROME,
            "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        },
        # El cliente "android" de YouTube esquiva los bloqueos de descarga
        "extractor_args": {"youtube": {"player_client": ["android", "web_safari", "web"]}},
    }


def info_video(url):
    """Consulta los datos del video en YouTube (título, duración, canal…)."""
    opts = opciones_base()
    opts["skip_download"] = True
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def descargar_archivo(url, tipo):
    """Descarga el video/audio de YouTube a una carpeta temporal.
    Devuelve (info, ruta_del_archivo, es_audio)."""
    carpeta = tempfile.mkdtemp()
    opts = opciones_base()
    if tipo == "🎵 Audio MP3":
        # m4a (aac) es el formato de audio más compatible para descargar
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        opts["outtmpl"] = os.path.join(carpeta, "audio.%(ext)s")
    else:
        altura = {"🎬 Video 1080p": 1080, "🎬 Video 720p": 720, "🎬 Video 480p": 480}[tipo]
        opts["format"] = f"best[ext=mp4][height<={altura}]/best[ext=mp4]/best"
        opts["outtmpl"] = os.path.join(carpeta, "video.%(ext)s")
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    archivos = [a for a in os.listdir(carpeta) if not a.endswith((".part", ".ytdl"))]
    ruta = os.path.join(carpeta, archivos[0]) if archivos else None
    return info, ruta


def a_mp3(ruta_entrada, ruta_salida, bitrate=192):
    """Convierte el audio descargado a MP3 usando PyAV (sin necesitar ffmpeg)."""
    buf = io.BytesIO()
    with av.open(ruta_entrada) as entrada:
        stream = entrada.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="stereo", rate=44100)
        with av.open(buf, "w", format="mp3") as salida:
            mp3 = salida.add_stream("mp3", rate=44100)
            mp3.bit_rate = bitrate * 1000
            mp3.layout = "stereo"
            for frame in entrada.decode(stream):
                for rframe in resampler.resample(frame):
                    rframe.pts = None
                    for paquete in mp3.encode(rframe):
                        salida.mux(paquete)
            for rframe in resampler.resample(None):
                rframe.pts = None
                for paquete in mp3.encode(rframe):
                    salida.mux(paquete)
            for paquete in mp3.encode(None):
                salida.mux(paquete)
    with open(ruta_salida, "wb") as f:
        f.write(buf.getvalue())
    return ruta_salida


def duracion_texto(segundos):
    """Formatea segundos a 'min s'."""
    if not segundos:
        return "?"
    return f"{int(segundos // 60)} min {int(segundos % 60)} s"


# ---------- INTERFAZ ----------
st.title("▶️ YouTube")
st.caption("Descarga el audio (MP3) o el video (MP4) de un enlace de YouTube.")

url = st.text_input(
    "Pega el enlace del video",
    placeholder="https://www.youtube.com/watch?v=…",
)
tipo = st.selectbox(
    "¿Qué quieres descargar?",
    ["🎵 Audio MP3", "🎬 Video 1080p", "🎬 Video 720p", "🎬 Video 480p"],
)
st.caption("💡 El MP3 es ideal para guardar entrevistas o podcasts · ⚠️ Solo descarga contenido que tengas derecho a usar.")

if st.button("Descargar", type="primary"):
    if not url or "youtube.com" not in url and "youtu.be" not in url:
        st.error("❌ Pega un enlace válido de YouTube (youtube.com/watch?v=… o youtu.be/…)")
        st.stop()

    estado = st.empty()
    progreso = st.empty()
    estado.markdown('<p class="giro-estado"><strong>Consultando YouTube…</strong></p>', unsafe_allow_html=True)
    progreso.markdown(giro_ui.barra_progreso(0, animado=True), unsafe_allow_html=True)

    try:
        info = info_video(url)

        # Mostrar los datos del video
        c1, c2, c3 = st.columns(3)
        c1.metric("Título", info.get("title", "?")[:30])
        c2.metric("Canal", info.get("channel", "?"))
        c3.metric("Duración", duracion_texto(info.get("duration")))

        # Aviso de límites en la nube (videos muy largos/pesados)
        duracion = info.get("duration") or 0
        if duracion > MAX_DURACION_NUBE:
            st.warning(f"⚠️ El video dura {duracion_texto(duracion)}. En la web pública puede fallar si es muy largo — en tu PC local no hay problema.")

        estado.markdown('<p class="giro-estado"><strong>Descargando…</strong> esto puede tardar según el tamaño</p>',
                        unsafe_allow_html=True)

        info, ruta = descargar_archivo(url, tipo)
        if ruta is None:
            raise RuntimeError("No se pudo obtener el archivo (video restringido o formato no disponible)")

        # Si pidió MP3, convertir el audio nativo a MP3
        if tipo == "🎵 Audio MP3":
            ruta_mp3 = os.path.join(os.path.dirname(ruta), "audio_final.mp3")
            a_mp3(ruta, ruta_mp3)
            ruta = ruta_mp3

        with open(ruta, "rb") as f:
            datos = f.read()

        peso_mb = len(datos) / (1024 * 1024)
        if peso_mb > MAX_PESO_NUBE_MB:
            st.warning(f"⚠️ El archivo pesa {peso_mb:.0f} MB — en la nube gratis puede fallar la entrega; en tu PC local funciona.")

        progreso.markdown(giro_ui.barra_progreso(100, ok=True), unsafe_allow_html=True)
        st.success(f"✅ ¡Descargado! ({peso_mb:.1f} MB)")
        st.metric("Peso del archivo", f"{peso_mb:.1f} MB")

        titulo_limpio = "".join(c for c in (info.get("title") or "video") if c not in '\\/:*?"<>|')[:60]
        ext = "mp3" if tipo == "🎵 Audio MP3" else "mp4"
        st.download_button(
            "⬇️ Guardar archivo",
            data=datos,
            file_name=f"{titulo_limpio}.{ext}",
            type="primary",
        )
    except Exception as e:
        st.error(f"❌ No pude descargar: {e}")
        st.caption("Causas comunes: enlace inválido, video privado, restringido por región o eliminado.")
# FIN BLOQUE 1
