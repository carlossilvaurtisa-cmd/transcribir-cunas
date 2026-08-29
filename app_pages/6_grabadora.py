# ============================================================
# BLOQUE 1: HERRAMIENTA — GRABADORA DE AUDIO (PENSADA PARA MÓVIL)
# Graba hasta 10 min con BUENA calidad (48kHz mono 128kbps)
# y permite transcribir o comprimir el audio desde la plataforma.
# ============================================================
import base64
import io
import os
import tempfile
import urllib.parse

import av
import streamlit as st
from groq import Groq

import giro_ui

MODELO_GROQ = "whisper-large-v3-turbo"
MODELO_CHAT = "llama-3.3-70b-versatile"


@st.cache_resource
def get_cliente_groq():
    """Crea el cliente de Groq UNA sola vez."""
    return Groq(api_key=giro_ui.cargar_clave_api())


def transcribir_con_groq(client, ruta_audio):
    """Envía el audio grabado a la nube de Groq y devuelve el texto."""
    with open(ruta_audio, "rb") as f:
        respuesta = client.audio.transcriptions.create(
            file=(os.path.basename(ruta_audio), f.read()),
            model=MODELO_GROQ,
            language="es",
            response_format="json",
        )
    return respuesta.text


def mejorar_texto_con_ia(texto):
    """Limpia y ordena el texto de la transcripción usando IA:
    corrige errores, quita muletillas, puntúa y arma párrafos."""
    client = get_cliente_groq()
    respuesta = client.chat.completions.create(
        model=MODELO_CHAT,
        messages=[
            {"role": "system", "content": (
                "Eres un transcriptor profesional de entrevistas. Recibes una transcripción "
                "automática con errores y muletillas. Devuelve SOLO el texto corregido: "
                "corrige palabras mal escuchadas, elimina muletillas (eh, este, ya no, o sea, "
                "repetido), pon puntuación y mayúsculas correctas, y separa en párrafos "
                "cortos por idea. No agregues comentarios ni explicaciones."
            )},
            {"role": "user", "content": texto},
        ],
        temperature=0.2,
    )
    return respuesta.choices[0].message.content.strip()


def comprimir_a_mp3(ruta_entrada, ruta_salida, rate=16000, bitrate=64):
    """Comprime el audio grabado a MP3 pequeño (mono, 16kHz, 64kbps).
    Excelente para WhatsApp/correo; la voz se entiende perfecto."""
    buf = io.BytesIO()
    with av.open(ruta_entrada) as entrada:
        stream = entrada.streams.audio[0]
        resampler = av.AudioResampler(format="s16", layout="mono", rate=rate)
        with av.open(buf, "w", format="mp3") as salida:
            mp3 = salida.add_stream("mp3", rate=rate)
            mp3.bit_rate = bitrate * 1000
            mp3.layout = "mono"
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


# ---------- HTML del componente (el botón grande) ----------
HTML_GRABADORA = """
<div style="text-align:center; font-family:'Century Gothic',sans-serif;">
  <style>
    #btn {
      width: 150px; height: 150px;
      border-radius: 50%;
      border: 6px solid #F32624;
      background: #F32624;
      color: #fff;
      font-size: 1.1rem;
      font-weight: 800;
      font-family: inherit;
      cursor: pointer;
      box-shadow: 0 6px 18px rgba(243,38,36,.4);
      transition: transform .15s ease;
      -webkit-tap-highlight-color: transparent;
      user-select: none;
    }
    #btn:active { transform: scale(.95); }
    #btn.grabando {
      background: #CC2A5F;
      border-color: #CC2A5F;
      animation: pulso 1.2s ease-in-out infinite;
    }
    @keyframes pulso {
      0%,100% { box-shadow: 0 0 0 0 rgba(204,42,95,.5); }
      50%     { box-shadow: 0 0 0 22px rgba(204,42,95,0); }
    }
    #timer {
      font-size: 2.2rem;
      font-weight: 800;
      color: #F32624;
      margin: 14px 0 4px 0;
      letter-spacing: 2px;
    }
    #estado { color: #636363; font-size: .95rem; }
    #aviso { color: #636363; font-size: .8rem; margin-top: 10px; }
  </style>
  <button id="btn">🎙️<br>GRABAR</button>
  <div id="timer">00:00 / 10:00</div>
  <div id="estado">Listo para grabar</div>
  <div id="aviso">Calidad voz: 48 kHz · 128 kbps · mono</div>
</div>
"""

# ---------- JS del componente (la lógica de grabación) ----------
JS_GRABADORA = """
export default function (component) {
  const { setStateValue, parentElement } = component;
  const btn = parentElement.querySelector('#btn');
  const timerEl = parentElement.querySelector('#timer');
  const estadoEl = parentElement.querySelector('#estado');
  const MAX_SEGUNDOS = 600; // 10 minutos

  let mediaRecorder = null;
  let chunks = [];
  let segundos = 0;
  let timerInt = null;

  function actualizarTimer() {
    const m = String(Math.floor(segundos / 60)).padStart(2, '0');
    const s = String(segundos % 60).padStart(2, '0');
    timerEl.textContent = m + ':' + s + ' / 10:00';
  }

  function bloquear(grabando) {
    btn.classList.toggle('grabando', grabando);
    btn.innerHTML = grabando ? '⏹️<br>DETENER' : '🎙️<br>GRABAR';
    estadoEl.textContent = grabando
      ? 'Grabando… (toca DETENER para terminar)'
      : 'Listo para grabar';
  }

  btn.addEventListener('click', async () => {
    if (mediaRecorder === null) {
      // ----- INICIAR GRABACIÓN (buena calidad para transcripción) -----
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            sampleRate: 48000,
            channelCount: 1
          }
        });
        const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus'
                   : MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4'
                   : '';
        const opciones = { audioBitsPerSecond: 128000 }; // 128 kbps: voz nítida
        if (mime) opciones.mimeType = mime;
        mediaRecorder = new MediaRecorder(stream, opciones);
        chunks = [];
        segundos = 0;
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
        mediaRecorder.onstop = finalizar;
        mediaRecorder.start();
        try { await navigator.wakeLock.request('screen'); } catch (e) { /* sin soporte */ }
        timerInt = setInterval(() => {
          segundos++;
          actualizarTimer();
          if (segundos >= MAX_SEGUNDOS) {
            mediaRecorder.stop(); // límite de 10 minutos alcanzado
          }
        }, 1000);
        bloquear(true);
      } catch (e) {
        estadoEl.textContent = '❌ Error: ' + (e.message || 'micrófono no disponible');
      }
    } else {
      // ----- DETENER GRABACIÓN -----
      mediaRecorder.stop();
    }
  });

  function finalizar() {
    clearInterval(timerInt);
    const tipo = mediaRecorder.mimeType || 'audio/webm';
    const blob = new Blob(chunks, { type: tipo });
    const esMp4 = tipo.includes('mp4');
    const nombre = 'grabacion_' + Date.now() + (esMp4 ? '.m4a' : '.webm');
    const reader = new FileReader();
    reader.onloadend = () => {
      const b64 = String(reader.result).split(',')[1];
      setStateValue('audio', {
        nombre: nombre,
        base64: b64,
        duracion: segundos,
        formato: tipo
      });
    };
    reader.readAsDataURL(blob);
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    mediaRecorder = null;
    bloquear(false);
    estadoEl.textContent = '✅ Grabación lista — mira abajo';
  }
}
"""

# Registro del componente (una sola vez, al importar el módulo)
_GRABADORA = st.components.v2.component(
    "grabadora_audio",
    html=HTML_GRABADORA,
    js=JS_GRABADORA,
)


# ---------- INTERFAZ ----------
st.title("🎙️ Grabadora")
st.caption("Graba hasta 10 minutos con buena calidad de voz (48 kHz · 128 kbps · mono).")

resultado = _GRABADORA(
    key="grabadora",
    on_value_change=lambda: None,
    on_submitted_change=lambda: None,
)

grabacion = getattr(resultado, "audio", None)

if grabacion and grabacion.get("base64"):
    datos_audio = base64.b64decode(grabacion["base64"])
    nombre_audio = grabacion["nombre"]
    duracion = grabacion.get("duracion", 0)
    formato = grabacion.get("formato", "audio/webm")
    ext = ".m4a" if "mp4" in formato else ".webm"
    peso_mb = len(datos_audio) / (1024 * 1024)

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Duración", f"{int(duracion // 60)} min {int(duracion % 60)} s")
    c2.metric("Peso (calidad voz)", f"{peso_mb:.1f} MB")
    c3.metric("Calidad", "48 kHz / 128 kbps")

    st.audio(datos_audio, format=formato)

    c_desc, c_compr = st.columns(2)
    with c_desc:
        st.download_button(
            "⬇️ Descargar audio (calidad)",
            data=datos_audio,
            file_name=nombre_audio,
            type="primary",
        )
    with c_compr:
        # Comprimir a MP3 pequeño para WhatsApp/correo
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(datos_audio)
            ruta_orig = tmp.name
        try:
            ruta_mp3 = os.path.join(os.path.dirname(ruta_orig), "mp3_final.mp3")
            comprimir_a_mp3(ruta_orig, ruta_mp3)
            with open(ruta_mp3, "rb") as f:
                datos_mp3 = f.read()
            peso_mp3 = len(datos_mp3) / (1024 * 1024)
            st.download_button(
                f"🗜️ MP3 pequeño ({peso_mp3:.1f} MB)",
                data=datos_mp3,
                file_name=nombre_audio.rsplit(".", 1)[0] + ".mp3",
                help="Comprimido a 64 kbps mono: ideal para WhatsApp (10 min ≈ 5 MB)",
            )
        finally:
            os.remove(ruta_orig)
            if os.path.exists(ruta_mp3):
                os.remove(ruta_mp3)

    # ----- TRANSCRIBIR DESDE LA MISMA PLATAFORMA -----
    st.subheader("📝 Transcribir esta grabación")
    if st.button("🎙️ Transcribir ahora (Groq)", type="primary"):
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(datos_audio)
            ruta = tmp.name
        try:
            estado = st.empty()
            progreso = st.empty()
            estado.markdown('<p class="giro-estado"><strong>Enviando a Groq…</strong></p>', unsafe_allow_html=True)
            progreso.markdown(giro_ui.barra_progreso(0, animado=True), unsafe_allow_html=True)

            texto = transcribir_con_groq(get_cliente_groq(), ruta)

            progreso.markdown(giro_ui.barra_progreso(100, ok=True), unsafe_allow_html=True)
            estado.markdown('<p class="giro-estado"><strong>✅ Transcripción lista</strong></p>', unsafe_allow_html=True)

            with st.container(border=True):
                st.text_area("Transcripción", value=texto, height=200, key="ta_grabadora")
                c_mej, c1, c2 = st.columns(3)
                with c_mej:
                    if st.button("✨ Mejorar con IA", key="mejorar_grab"):
                        with st.spinner("Mejorando el texto…"):
                            mejorado = mejorar_texto_con_ia(st.session_state["ta_grabadora"])
                        st.session_state["ta_grabadora"] = mejorado
                        st.rerun()
                with c1:
                    st.download_button(
                        "⬇️ Descargar .txt",
                        data=st.session_state["ta_grabadora"],
                        file_name=nombre_audio.rsplit(".", 1)[0] + ".txt",
                        key="desc_grab",
                        type="primary",
                    )
                with c2:
                    mensaje = f"🎙️ Transcripción de grabación:\n\n{st.session_state['ta_grabadora']}"[:4000]
                    st.link_button("📲 Compartir por WhatsApp",
                                   "https://wa.me/?text=" + urllib.parse.quote(mensaje))
        except Exception as e:
            st.error(f"❌ No pude transcribir: {e}")
        finally:
            os.remove(ruta)

st.info("📱 **Consejos para el celular:** acepta el permiso de micrófono · la pantalla no se apagará sola mientras grabas (Wake Lock) · en Android sigue grabando aunque bloquees la pantalla · en iPhone evita apagarla, el navegador corta la grabación")
# FIN BLOQUE 1
