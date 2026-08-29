# ============================================================
# BLOQUE 1: HERRAMIENTA 5 — VIDEO (COMPRIMIR)
# ============================================================
import os
import tempfile

import av
import streamlit as st

import giro_ui

# Calidad → valor CRF de H.264 (más alto = más compresión, peor calidad)
CALIDADES = {
    "Alta (poco se nota)": 23,
    "Media (recomendada)": 28,
    "Baja (máxima compresión)": 32,
}


def comprimir_video(ruta_entrada, ruta_salida, crf):
    """Re-encodea un video a MP4 H.264 con el nivel de compresión elegido."""
    with av.open(ruta_entrada) as entrada:
        with av.open(ruta_salida, "w", format="mp4") as salida:
            vstream_in = entrada.streams.video[0]
            astream_in = entrada.streams.audio[0] if entrada.streams.audio else None

            vstream_out = salida.add_stream("libx264", rate=vstream_in.average_rate)
            vstream_out.width = vstream_in.width
            vstream_out.height = vstream_in.height
            vstream_out.pix_fmt = "yuv420p"
            vstream_out.options = {"crf": str(crf), "preset": "veryfast"}

            astream_out = None
            if astream_in:
                astream_out = salida.add_stream("aac", rate=44100)
                astream_out.layout = "stereo"

            for frame in entrada.decode(vstream_in):
                frame.pts = None
                for paquete in vstream_out.encode(frame):
                    salida.mux(paquete)
            for paquete in vstream_out.encode(None):
                salida.mux(paquete)

            if astream_out:
                resampler = av.AudioResampler(format="s16", layout="stereo", rate=44100)
                for frame in entrada.decode(astream_in):
                    for rframe in resampler.resample(frame):
                        rframe.pts = None
                        for paquete in astream_out.encode(rframe):
                            salida.mux(paquete)
                for rframe in resampler.resample(None):
                    rframe.pts = None
                    for paquete in astream_out.encode(rframe):
                        salida.mux(paquete)
                for paquete in astream_out.encode(None):
                    salida.mux(paquete)


# ---------- INTERFAZ ----------
st.title("🎬 Video")
st.caption("Comprime videos para enviarlos por WhatsApp o subirlos más rápido.")

archivo = st.file_uploader(
    "Sube tu video",
    type=["mp4", "mov", "avi", "mkv", "webm", "m4v", "wmv"],
)
if archivo is None:
    st.info("👆 Sube un video para empezar")
    st.stop()

calidad = st.selectbox("Nivel de compresión", list(CALIDADES.keys()), index=1)
st.caption("💡 'Media' es ideal: reduce mucho el peso y casi no se nota la diferencia.")

peso_original_mb = len(archivo.getvalue()) / (1024 * 1024)
st.metric("Peso original", f"{peso_original_mb:.1f} MB")

if st.button("Comprimir video", type="primary"):
    st.caption("⏳ Los videos largos tardan unos minutos en comprimirse (es normal).")
    with tempfile.TemporaryDirectory() as carpeta:
        ruta_entrada = os.path.join(carpeta, "entrada" + os.path.splitext(archivo.name)[1])
        ruta_salida = os.path.join(carpeta, "salida.mp4")
        with open(ruta_entrada, "wb") as f:
            f.write(archivo.getvalue())

        estado = st.empty()
        estado.markdown('<p class="giro-estado"><strong>Comprimiendo…</strong> esto puede tardar varios minutos</p>',
                        unsafe_allow_html=True)

        try:
            comprimir_video(ruta_entrada, ruta_salida, CALIDADES[calidad])
            with open(ruta_salida, "rb") as f:
                datos = f.read()
            peso_nuevo_mb = len(datos) / (1024 * 1024)
            reduccion = 100 - peso_nuevo_mb / max(peso_original_mb, 0.001) * 100

            estado.markdown(giro_ui.barra_progreso(100, ok=True), unsafe_allow_html=True)
            st.success(f"✅ Video comprimido: {peso_nuevo_mb:.1f} MB (reducción del {reduccion:.0f}%)")
            st.metric("Peso original", f"{peso_original_mb:.1f} MB")
            st.metric("Peso comprimido", f"{peso_nuevo_mb:.1f} MB", delta=f"−{reduccion:.0f}%")
            st.download_button(
                "⬇️ Descargar video comprimido",
                data=datos,
                file_name=f"comprimido_{archivo.name.rsplit('.', 1)[0]}.mp4",
                type="primary",
            )
        except Exception as e:
            st.error(f"❌ No pude comprimir el video: {e}")
# FIN BLOQUE 1
