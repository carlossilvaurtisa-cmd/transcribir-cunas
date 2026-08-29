# ============================================================
# BLOQUE 1: HERRAMIENTA 2 — FOTOS (TRANSFORMAR + REDUCIR 16MB)
# ============================================================
import io

import streamlit as st
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

import giro_ui

FORMATOS_FOTO = ["jpg", "jpeg", "png", "webp", "bmp", "tiff"]
LÍMITE_WHATSAPP_MB = 16.0   # WhatsApp acepta fotos hasta 16 MB


def reducir_para_whatsapp(img, limite_mb=LÍMITE_WHATSAPP_MB):
    """Reduce una foto hasta que pese menos del límite (en MB).
    Estrategia: baja resolución y calidad JPEG hasta lograrlo."""
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    # 1) Redimensionar si es gigante (máx 4096 px en el lado largo)
    ancho_max = 4096
    if max(img.size) > ancho_max:
        img.thumbnail((ancho_max, ancho_max), Image.LANCZOS)

    # 2) Bajar la calidad JPEG hasta pasar el límite
    calidad = 88
    while True:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=calidad, optimize=True)
        peso_mb = buf.tell() / (1024 * 1024)
        if peso_mb <= limite_mb or calidad <= 30:
            break
        calidad -= 8

    # 3) Si aún pesa más: reducir resolución a la mitad y repetir
    while peso_mb > limite_mb:
        img.thumbnail((max(img.size) // 2, max(img.size) // 2), Image.LANCZOS)
        calidad = 85
        while True:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=calidad, optimize=True)
            peso_mb = buf.tell() / (1024 * 1024)
            if peso_mb <= limite_mb or calidad <= 25:
                break
            calidad -= 8
        if max(img.size) < 800:   # ya no se puede reducir más
            break

    return img, buf.getvalue()


def aplicar_sepia(img):
    """Convierte la imagen a tonos sepia (clásico de foto antigua)."""
    gris = ImageOps.grayscale(img)
    return ImageOps.colorize(gris, black=(45, 25, 10), white=(240, 225, 190))


# ---------- INTERFAZ ----------
st.title("📷 Fotos")
st.caption("Transforma tus fotografías o redúcelas para enviarlas por WhatsApp.")

herramienta = st.segmented_control(
    "¿Qué quieres hacer?",
    options=["Transformar fotografía", "Reducir tamaño (WhatsApp)"],
    default="Transformar fotografía",
)

archivo = st.file_uploader("Sube una foto", type=FORMATOS_FOTO)

if archivo is None:
    st.info("👆 Sube una foto para empezar")
    st.stop()

imagen_original = Image.open(archivo)
imagen_original = ImageOps.exif_transpose(imagen_original)  # respeta la orientación de la cámara
peso_original_mb = len(archivo.getvalue()) / (1024 * 1024)

# ---------- MODO 1: TRANSFORMAR ----------
if herramienta == "Transformar fotografía":
    c_antes, c_despues = st.columns(2)
    with c_antes:
        st.image(imagen_original, caption=f"Original ({peso_original_mb:.1f} MB)")

    c1, c2, c3 = st.columns(3)
    rotacion = c1.selectbox("Rotar", [0, 90, 180, 270], index=0)
    volteo = c2.selectbox("Voltear", ["Ninguno", "Horizontal", "Vertical"])
    escala = c3.slider("Escala (%)", 10, 200, 100, step=5)

    filtro = st.selectbox("Filtro", [
        "Ninguno", "Blanco y negro", "Sepia",
        "Brillo +30%", "Contraste +30%", "Desenfoque suave",
    ])
    formato_salida = st.selectbox("Formato de salida", ["JPG", "PNG", "WEBP"])

    if st.button("Transformar", type="primary"):
        nueva = imagen_original
        if rotacion:
            nueva = nueva.rotate(rotacion, expand=True)
        if volteo == "Horizontal":
            nueva = ImageOps.mirror(nueva)
        elif volteo == "Vertical":
            nueva = ImageOps.flip(nueva)
        if escala != 100:
            nueva = nueva.resize((int(nueva.width * escala / 100), int(nueva.height * escala / 100)), Image.LANCZOS)
        if filtro == "Blanco y negro":
            nueva = ImageOps.grayscale(nueva)
        elif filtro == "Sepia":
            nueva = aplicar_sepia(nueva)
        elif filtro == "Brillo +30%":
            nueva = ImageEnhance.Brightness(nueva).enhance(1.3)
        elif filtro == "Contraste +30%":
            nueva = ImageEnhance.Contrast(nueva).enhance(1.3)
        elif filtro == "Desenfoque suave":
            nueva = nueva.filter(ImageFilter.GaussianBlur(2))

        with c_despues:
            st.image(nueva, caption="Resultado")

        # Guardar en el formato elegido
        buf = io.BytesIO()
        ext = {"JPG": "jpg", "PNG": "png", "WEBP": "webp"}[formato_salida]
        if nueva.mode in ("RGBA", "P", "LA") and ext == "jpg":
            nueva = nueva.convert("RGB")
        nueva.save(buf, formato_salida)
        peso_nuevo_mb = buf.tell() / (1024 * 1024)

        st.metric("Peso del resultado", f"{peso_nuevo_mb:.2f} MB",
                  delta=f"{(peso_nuevo_mb - peso_original_mb) / max(peso_original_mb, 0.001) * 100:.0f}%")
        st.download_button(
            "⬇️ Descargar foto transformada",
            data=buf.getvalue(),
            file_name=f"transformada_{archivo.name.rsplit('.', 1)[0]}.{ext}",
            type="primary",
        )

# ---------- MODO 2: REDUCIR PARA WHATSAPP ----------
else:
    c_antes, c_despues = st.columns(2)
    with c_antes:
        st.image(imagen_original, caption=f"Original ({peso_original_mb:.1f} MB)")
        st.caption(f"Peso actual: **{peso_original_mb:.1f} MB**")

    if st.button("Reducir para WhatsApp", type="primary"):
        img_final, bytes_jpg = reducir_para_whatsapp(imagen_original)
        peso_nuevo_mb = len(bytes_jpg) / (1024 * 1024)

        with c_despues:
            st.image(img_final, caption=f"Reducida ({peso_nuevo_mb:.1f} MB)")

        # Mostrar el resultado con métricas GIRO
        st.metric("Tamaño original", f"{peso_original_mb:.1f} MB")
        st.metric("Tamaño reducido", f"{peso_nuevo_mb:.1f} MB",
                  delta=f"{-100 + peso_nuevo_mb / max(peso_original_mb, 0.001) * 100:.0f}%")
        if peso_nuevo_mb <= LÍMITE_WHATSAPP_MB:
            st.success(f"✅ Lista para WhatsApp: pesa {peso_nuevo_mb:.1f} MB (límite 16 MB)")
        else:
            st.warning("⚠️ Sigue pesando más de 16 MB (foto extremadamente grande)")

        st.download_button(
            "⬇️ Descargar foto reducida",
            data=bytes_jpg,
            file_name=f"whatsapp_{archivo.name.rsplit('.', 1)[0]}.jpg",
            type="primary",
        )
# FIN BLOQUE 1
