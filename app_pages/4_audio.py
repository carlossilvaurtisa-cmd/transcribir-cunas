# ============================================================
# BLOQUE 1: HERRAMIENTA 4 — AUDIO (CONVERTIR FORMATOS)
# ============================================================
import io
import os
import tempfile

import av
import streamlit as st

import giro_ui

# Formato de salida → (codec de audio, contenedor)
CODIFS = {
    "MP3": ("mp3", "mp3"),
    "WAV": ("pcm_s16le", "wav"),
    "OGG": ("libvorbis", "ogg"),
    "M4A": ("aac", "mp4"),
    "FLAC": ("flac", "flac"),
}
BITRATES = [64, 96, 128, 192, 256, 320]


def convertir_audio(ruta_entrada, formato_destino, bitrate, canales):
    """Convierte un audio a otro formato usando PyAV.
    Devuelve los bytes del archivo convertido."""
    codec, contenedor = CODIFS[formato_destino]
    buf = io.BytesIO()

    with av.open(ruta_entrada) as entrada:
        stream = entrada.streams.audio[0]
        layout = "mono" if canales == "Mono" else "stereo"
        resampler = av.AudioResampler(format="s16", layout=layout, rate=44100)

        with av.open(buf, "w", format=contenedor) as salida:
            salida_stream = salida.add_stream(codec, rate=44100)
            if formato_destino in ("MP3", "M4A", "OGG"):
                salida_stream.bit_rate = bitrate * 1000
            if formato_destino == "MP3":
                salida_stream.layout = layout
            elif formato_destino == "M4A":
                salida_stream.layout = layout
                salida_stream.options = {"b": f"{bitrate}k"}

            for frame in entrada.decode(stream):
                for rframe in resampler.resample(frame):
                    rframe.pts = None
                    for paquete in salida_stream.encode(rframe):
                        salida.mux(paquete)
            for rframe in resampler.resample(None):
                rframe.pts = None
                for paquete in salida_stream.encode(rframe):
                    salida.mux(paquete)
            for paquete in salida_stream.encode(None):
                salida.mux(paquete)

    return buf.getvalue()


# ---------- INTERFAZ ----------
st.title("🎵 Audio")
st.caption("Convierte audios (o el sonido de un video) a otro formato.")

archivo = st.file_uploader(
    "Sube tu audio o video",
    type=["mp3", "wav", "ogg", "m4a", "flac", "aac",
          "mp4", "mov", "avi", "mkv", "webm", "m4v", "wmv"],
)
if archivo is None:
    st.info("👆 Sube un audio o video para empezar")
    st.stop()

c1, c2, c3 = st.columns(3)
formato_destino = c1.selectbox("Formato de salida", list(CODIFS.keys()), index=0)
bitrate = c2.selectbox("Calidad (bitrate)", BITRATES, index=2)
canales = c3.selectbox("Canales", ["Stereo", "Mono"])

peso_original_mb = len(archivo.getvalue()) / (1024 * 1024)
st.caption(f"Peso del original: **{peso_original_mb:.1f} MB**")

if st.button("Convertir audio", type="primary"):
    with tempfile.NamedTemporaryFile(suffix=".audio", delete=False) as tmp:
        tmp.write(archivo.getvalue())
        ruta = tmp.name
    try:
        with st.spinner("Convirtiendo…"):
            datos = convertir_audio(ruta, formato_destino, bitrate, canales)
        peso_nuevo_mb = len(datos) / (1024 * 1024)
        st.success(f"✅ Convertido a {formato_destino} ({peso_nuevo_mb:.1f} MB)")
        st.metric("Tamaño original", f"{peso_original_mb:.1f} MB")
        st.metric("Tamaño convertido", f"{peso_nuevo_mb:.1f} MB")
        ext = CODIFS[formato_destino][1]
        st.download_button(
            "⬇️ Descargar audio convertido",
            data=datos,
            file_name=f"{archivo.name.rsplit('.', 1)[0]}.{ext}",
            type="primary",
        )
    except Exception as e:
        st.error(f"❌ No pude convertir el audio: {e}")
    finally:
        os.remove(ruta)
# FIN BLOQUE 1
