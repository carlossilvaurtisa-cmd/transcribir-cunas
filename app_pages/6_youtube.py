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
        # Clientes que esquivar el bloqueo 403 (probados: tv_embedded y android_safari)
        "extractor_args": {"youtube": {"player_client": ["tv_embedded", "android_safari", "android", "web"]}},
    }


def info_video(url):
    """Consulta los datos del video en YouTube (título, duración, canal…)."""
    opts = opciones_base()
    opts["skip_download"] = True
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False)


def descargar_archivo(url, tipo):
    """Descarga el video/audio de YouTube a una carpeta temporal.
    Para video: baja pista de video y audio por separado y las fusiona en MP4.
    Devuelve (info, ruta_del_archivo)."""
    carpeta = tempfile.mkdtemp()
    opts = opciones_base()

    if tipo == "🎵 Audio MP3":
        opts["format"] = "bestaudio/best"
        opts["outtmpl"] = os.path.join(carpeta, "audio.%(ext)s")
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
        archivos = [a for a in os.listdir(carpeta) if not a.endswith((".part", ".ytdl"))]
        ruta = os.path.join(carpeta, archivos[0]) if archivos else None
        return info, ruta

    # ----- Video: 1) descargar SOLO la pista de video -----
    altura = {"🎬 Video 1080p": 1080, "🎬 Video 720p": 720, "🎬 Video 480p": 480}[tipo]
    opts["format"] = f"bestvideo[height<={altura}]/bestvideo/best"
    opts["outtmpl"] = os.path.join(carpeta, "v.%(ext)s")
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    archivos = [a for a in os.listdir(carpeta) if a.startswith("v.") and not a.endswith((".part", ".ytdl"))]
    ruta_video = os.path.join(carpeta, archivos[0]) if archivos else None
    if ruta_video is None:
        raise RuntimeError("No se encontró la pista de video")

    # ----- 2) descargar SOLO el audio -----
    opts2 = opciones_base()
    opts2["format"] = "bestaudio/best"
    opts2["outtmpl"] = os.path.join(carpeta, "a.%(ext)s")
    with yt_dlp.YoutubeDL(opts2) as ydl:
        ydl.extract_info(url, download=True)
    archivos_a = [a for a in os.listdir(carpeta) if a.startswith("a.") and not a.endswith((".part", ".ytdl"))]
    ruta_audio = os.path.join(carpeta, archivos_a[0]) if archivos_a else None

    # ----- 3) fusionar video + audio en un MP4 -----
    ruta_final = os.path.join(carpeta, "video_final.mp4")
    fusionar_video_audio(ruta_video, ruta_audio, ruta_final)
    return info, ruta_final


def fusionar_video_audio(ruta_video, ruta_audio, ruta_salida):
    """Une la pista de video y la de audio en un solo MP4 (H.264 + AAC),
    usando PyAV (no necesita ffmpeg instalado)."""
    with av.open(ruta_video) as vin, av.open(ruta_audio) as ain:
        v_stream = vin.streams.video[0]
        a_stream = ain.streams.audio[0]
        with av.open(ruta_salida, "w", format="mp4") as salida:
            v_out = salida.add_stream("libx264", rate=v_stream.average_rate)
            v_out.width, v_out.height = v_stream.width, v_stream.height
            v_out.pix_fmt = "yuv420p"
            v_out.options = {"crf": "23", "preset": "veryfast"}

            a_out = salida.add_stream("aac", rate=44100)
            a_out.layout = "stereo"
            resampler = av.AudioResampler(format="s16", layout="stereo", rate=44100)

            # Frames de video
            for frame in vin.decode(v_stream):
                frame.pts = None
                for paquete in v_out.encode(frame):
                    salida.mux(paquete)
            for paquete in v_out.encode(None):
                salida.mux(paquete)

            # Frames de audio
            for frame in ain.decode(a_stream):
                for rframe in resampler.resample(frame):
                    rframe.pts = None
                    for paquete in a_out.encode(rframe):
                        salida.mux(paquete)
            for rframe in resampler.resample(None):
                rframe.pts = None
                for paquete in a_out.encode(rframe):
                    salida.mux(paquete)
            for paquete in a_out.encode(None):
                salida.mux(paquete)


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
