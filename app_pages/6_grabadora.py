# ============================================================
# BLOQUE 1: HERRAMIENTA — GRABADORA DE AUDIO (PENSADA PARA MÓVIL)
# Graba hasta 10 min con compresión, botón grande bloqueado,
# y permite transcribir el audio desde la misma plataforma.
# Usa un componente custom v2 (HTML + JS inline).
# ============================================================
import base64
import os
import tempfile
import urllib.parse

import streamlit as st
from groq import Groq

import giro_ui

MODELO_GROQ = "whisper-large-v3-turbo"


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
  <div id="aviso">Toca GRABAR para empezar · toca DETENER para terminar</div>
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
      // ----- INICIAR GRABACIÓN -----
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const mime = MediaRecorder.isTypeSupported('audio/webm;codecs=opus') ? 'audio/webm;codecs=opus'
                   : MediaRecorder.isTypeSupported('audio/mp4') ? 'audio/mp4'
                   : '';
        mediaRecorder = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
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
st.caption("Graba hasta 10 minutos con el botón grande · el audio queda comprimido automáticamente.")

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
    c2.metric("Peso (comprimido)", f"{peso_mb:.2f} MB")
    c3.metric("Formato", "Opus/AAC (comprimido)")

    st.audio(datos_audio, format=formato)

    st.download_button(
        "⬇️ Descargar audio",
        data=datos_audio,
        file_name=nombre_audio,
        type="primary",
    )

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
                texto_editado = st.text_area("Transcripción", value=texto, height=200)
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        "⬇️ Descargar .txt",
                        data=texto_editado,
                        file_name=nombre_audio.rsplit(".", 1)[0] + ".txt",
                        type="primary",
                    )
                with c2:
                    mensaje = f"🎙️ Transcripción de grabación:\n\n{texto_editado}"[:4000]
                    st.link_button("📲 Compartir por WhatsApp",
                                   "https://wa.me/?text=" + urllib.parse.quote(mensaje))
        except Exception as e:
            st.error(f"❌ No pude transcribir: {e}")
        finally:
            os.remove(ruta)

st.info("📱 **Consejos para el celular:** acepta el permiso de micrófono · la pantalla no se apagará sola mientras grabas (Wake Lock) · en Android sigue grabando aunque bloquees la pantalla · en iPhone evita apagarla, el navegador corta la grabación")
# FIN BLOQUE 1
