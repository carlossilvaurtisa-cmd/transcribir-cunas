# ============================================================
# BLOQUE 1: HERRAMIENTA 5 — VIDEO (COMPRIMIR)
# Con parámetros de ajuste enfocados en el peso del archivo
# ============================================================
import os
import tempfile

import av
import streamlit as st

import giro_ui

RESOLUCIONES = ["Original", "1080p", "720p", "480p"]
FPS_OPCIONES = ["Original", 30, 24, 15]
BITRATES_AUDIO = [64, 96, 128, 192, 256]


def comprimir_video(ruta_entrada, ruta_salida, crf, resolucion, fps, bitrate_audio):
    """Re-encodea un video a MP4 H.264 con los parámetros elegidos."""
    with av.open(ruta_entrada) as entrada:
        v_in = entrada.streams.video[0]

        # Resolución de salida
        w, h = v_in.width, v_in.height
        if resolucion != "Original":
            max_ancho = {"1080p": 1920, "720p": 1280, "480p": 854}[resolucion]
            if w > max_ancho:
                h = int(h * max_ancho / w)
                w = max_ancho
                w -= w % 2   # H.264 exige medidas pares
                h -= h % 2

        # FPS de salida
        rate = v_in.average_rate
        if fps != "Original":
            rate = int(fps)

        with av.open(ruta_salida, "w", format="mp4") as salida:
            v_out = salida.add_stream("libx264", rate=rate)
            v_out.width, v_out.height = w, h
            v_out.pix_fmt = "yuv420p"
            v_out.options = {"crf": str(crf), "preset": "veryfast"}

            astream_in = entrada.streams.audio[0] if entrada.streams.audio else None
            a_out = None
            if astream_in:
                a_out = salida.add_stream("aac", rate=44100)
                a_out.layout = "stereo"
                a_out.bit_rate = bitrate_audio * 1000

            for frame in entrada.decode(v_in):
                frame.pts = None
                for paquete in v_out.encode(frame):
                    salida.mux(paquete)
            for paquete in v_out.encode(None):
                salida.mux(paquete)

            if a_out:
                resampler = av.AudioResampler(format="s16", layout="stereo", rate=44100)
                for frame in entrada.decode(astream_in):
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


def comprimir_a_peso(ruta_entrada, ruta_salida, objetivo_mb, resolucion, fps, bitrate_audio):
    """Comprime probando varios niveles de CRF hasta acercarse al peso objetivo.
    Hasta 3 intentos; cada intento mide el resultado y ajusta la compresión."""
    crf = 28
    for intento in range(3):
        comprimir_video(ruta_entrada, ruta_salida, crf, resolucion, fps, bitrate_audio)
        peso = os.path.getsize(ruta_salida) / (1024 * 1024)
        if abs(peso - objetivo_mb) / max(objetivo_mb, 0.1) < 0.12:
            break
        # Más pesado de lo pedido → comprimir más (CRF mayor); y viceversa
        crf += 6 if peso > objetivo_mb else -6
        crf = max(18, min(45, crf))
    return peso


def duracion_segundos(ruta):
    """Calcula la duración del video en segundos."""
    with av.open(ruta) as entrada:
        v = entrada.streams.video[0]
        return v.duration / float(v.time_base) if v.duration else 0


# ---------- INTERFAZ ----------
st.title("🎬 Video")
st.caption("Comprime videos con control fino del peso del archivo.")

archivo = st.file_uploader(
    "Sube tu video",
    type=["mp4", "mov", "avi", "mkv", "webm", "m4v", "wmv"],
)
if archivo is None:
    st.info("👆 Sube un video para empezar")
    st.stop()

peso_original_mb = len(archivo.getvalue()) / (1024 * 1024)

# Información del video original
with tempfile.NamedTemporaryFile(suffix=".video", delete=False) as tmp_orig:
    tmp_orig.write(archivo.getvalue())
    ruta_orig = tmp_orig.name
try:
    with av.open(ruta_orig) as entrada:
        v = entrada.streams.video[0]
        res_original = f"{v.width} × {v.height}"
        dur = duracion_segundos(ruta_orig)
        dur_texto = f"{int(dur // 60)} min {int(dur % 60)} s"
except Exception:
    res_original = "?"
    dur_texto = "?"

c_info1, c_info2, c_info3 = st.columns(3)
c_info1.metric("Peso original", f"{peso_original_mb:.1f} MB")
c_info2.metric("Resolución", res_original)
c_info3.metric("Duración", dur_texto)

# Modo de compresión
modo = st.segmented_control(
    "Modo de compresión",
    options=["Calidad fija", "Peso objetivo (MB)"],
    default="Calidad fija",
)

c1, c2, c3 = st.columns(3)
resolucion = c1.selectbox("Resolución de salida", RESOLUCIONES, index=1,
                          help="Reducir la resolución es lo que más baja el peso")
fps = c2.selectbox("FPS (cuadros/segundo)", FPS_OPCIONES, index=0)
bitrate_audio = c3.selectbox("Bitrate de audio (kbps)", BITRATES_AUDIO, index=2)

if modo == "Calidad fija":
    crf = st.slider(
        "Nivel de compresión (CRF)",
        18, 40, 28, 1,
        help="Más alto = más compresión y menos peso. 18 casi sin pérdida, 28 recomendado, 40 muy liviano",
    )
else:
    objetivo_mb = st.slider("Peso objetivo del video (MB)", 5, 200, 30, 5,
                            help="La app prueba niveles de compresión hasta acercarse a este peso")
    st.caption("⏳ El modo objetivo comprime varias veces (hasta 3) para ajustar el peso — tarda más.")

if st.button("Comprimir video", type="primary"):
    st.caption("⏳ Los videos largos tardan unos minutos en comprimirse (es normal).")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta_entrada = os.path.join(carpeta, "entrada" + os.path.splitext(archivo.name)[1])
        ruta_salida = os.path.join(carpeta, "salida.mp4")
        with open(ruta_entrada, "wb") as f:
            f.write(archivo.getvalue())

        estado = st.empty()
        progreso = st.empty()
        estado.markdown('<p class="giro-estado"><strong>Comprimiendo…</strong> esto puede tardar varios minutos</p>',
                        unsafe_allow_html=True)
        progreso.markdown(giro_ui.barra_progreso(0, animado=True), unsafe_allow_html=True)

        try:
            if modo == "Calidad fija":
                comprimir_video(ruta_entrada, ruta_salida, crf, resolucion, fps, bitrate_audio)
                peso_nuevo = os.path.getsize(ruta_salida) / (1024 * 1024)
            else:
                peso_nuevo = comprimir_a_peso(ruta_entrada, ruta_salida, objetivo_mb,
                                              resolucion, fps, bitrate_audio)

            with open(ruta_salida, "rb") as f:
                datos = f.read()
            reduccion = 100 - peso_nuevo / max(peso_original_mb, 0.001) * 100

            progreso.markdown(giro_ui.barra_progreso(100, ok=True), unsafe_allow_html=True)
            st.success(f"✅ Video comprimido: {peso_nuevo:.1f} MB (reducción del {reduccion:.0f}%)")
            st.metric("Peso original", f"{peso_original_mb:.1f} MB")
            st.metric("Peso comprimido", f"{peso_nuevo:.1f} MB", delta=f"−{reduccion:.0f}%")
            st.download_button(
                "⬇️ Descargar video comprimido",
                data=datos,
                file_name=f"comprimido_{archivo.name.rsplit('.', 1)[0]}.mp4",
                type="primary",
            )
        except Exception as e:
            st.error(f"❌ No pude comprimir el video: {e}")
        finally:
            if os.path.exists(ruta_orig):
                os.remove(ruta_orig)
# FIN BLOQUE 1
