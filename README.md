# 🎙️ Transcripción de cuñas (Web en la nube)

Sube videos o audios y recibe el texto transcrito en español. Descarga el `.txt` cuando quieras.

## 🚀 Cómo publicarla en internet (Hugging Face Spaces) — ~10 minutos

1. **Crea una cuenta gratis** en [huggingface.co](https://huggingface.co/join) (correo + contraseña).

2. **Crea un Space** (botón "+ New" → "New Space"):
   - Space name: `transcribir-cunas` (o el que quieras)
   - License: MIT
   - **SDK: Streamlit**
   - Visibility: **Public** (para que tu colega entre sin cuenta)
   - Clic en "Create Space"

3. **Sube los archivos**: entra a la pestaña **"Files"** → botón **"Upload files"** (o arrastra y suelta):
   - `app.py`
   - `requirements.txt`

4. **Pon la clave de Groq como secreto** (es seguro, nadie puede verla):
   - Pestaña **"Settings"** → sección **"Secrets and variables"** → "New secret"
   - Name: `GROQ_API_KEY`
   - Value: tu clave (la misma que está en tu archivo `.env`)
   - Guardar.

5. **Espera ~2-5 minutos** mientras se instalan las librerías (pestaña "Builder"/"Logs" muestra el progreso).

6. **¡Listo!** Tu web queda en:
   ```
   https://huggingface.co/spaces/TU_USUARIO/transcribir-cunas
   ```
   Comparte ese enlace con tu colega. Funciona desde **cualquier lugar con internet** y **no necesitas tu PC encendida**.

## 💡 Notas

- El plan gratuito **"se duerme"** si nadie la usa por 48 horas; al volver a abrirla tarda ~1 min en despertar.
- El motor **"Nube (Groq)"** es el recomendado (rápido y preciso).
- El motor **"Local"** usa el Whisper del servidor (más lento, pero no gasta créditos de Groq).
- Videos de más de 15 minutos se dividen automáticamente en trozos.
