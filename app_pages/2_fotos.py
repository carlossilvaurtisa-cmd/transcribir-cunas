# ============================================================
# BLOQUE 1: HERRAMIENTA 2 — FOTOS
# (TRANSFORMAR POR LOTE + CORRECCIONES + REDUCIR 16MB)
# ============================================================
import io
import os
import zipfile

import streamlit as st
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

import giro_ui

FORMATOS_FOTO = ["jpg", "jpeg", "png", "webp", "bmp", "tiff"]
LÍMITE_WHATSAPP_MB = 16.0   # WhatsApp acepta fotos hasta 16 MB


def aplicar_sepia(img):
    """Convierte la imagen a tonos sepia (clásico de foto antigua)."""
    gris = ImageOps.grayscale(img)
    return ImageOps.colorize(gris, black=(45, 25, 10), white=(240, 225, 190))


def transformar_imagen(img, rotacion, volteo, filtro, brillo, contraste,
                       saturacion, nitidez, ancho_max, calidad, formato_salida):
    """Aplica todas las transformaciones a UNA imagen.
    Devuelve (imagen final, bytes, extensión)."""
    nueva = ImageOps.exif_transpose(img)   # respeta la orientación de la cámara

    if rotacion:
        nueva = nueva.rotate(rotacion, expand=True)
    if volteo == "Horizontal":
        nueva = ImageOps.mirror(nueva)
    elif volteo == "Vertical":
        nueva = ImageOps.flip(nueva)

    # Tamaño máximo (si se pide más pequeño)
    if ancho_max and nueva.width > ancho_max:
        nueva.thumbnail((ancho_max, ancho_max), Image.LANCZOS)

    # Filtros de color
    es_gris = False
    if filtro == "Blanco y negro":
        nueva = ImageOps.grayscale(nueva)
        es_gris = True
    elif filtro == "Sepia":
        nueva = aplicar_sepia(nueva)

    # Correcciones simples
    nueva = ImageEnhance.Brightness(nueva).enhance(brillo)
    nueva = ImageEnhance.Contrast(nueva).enhance(contraste)
    if not es_gris:   # la saturación no aplica en blanco y negro
        nueva = ImageEnhance.Color(nueva).enhance(saturacion)
    nueva = ImageEnhance.Sharpness(nueva).enhance(nitidez)

    # Guardar en el formato elegido
    buf = io.BytesIO()
    ext = {"JPG": "jpg", "PNG": "png", "WEBP": "webp"}[formato_salida]
    if nueva.mode in ("RGBA", "P", "LA") and ext == "jpg":
        nueva = nueva.convert("RGB")
    if formato_salida == "JPG":
        nueva.save(buf, "JPEG", quality=calidad, optimize=True)
    elif formato_salida == "PNG":
        nueva.save(buf, "PNG", optimize=True)
    else:
        nueva.save(buf, "WEBP", quality=calidad, optimize=True)
    return nueva, buf.getvalue(), ext


def reducir_para_whatsapp(img, limite_mb=LÍMITE_WHATSAPP_MB):
    """Reduce una foto hasta que pese menos del límite (en MB)."""
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    ancho_max = 4096
    if max(img.size) > ancho_max:
        img.thumbnail((ancho_max, ancho_max), Image.LANCZOS)

    calidad = 88
    while True:
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=calidad, optimize=True)
        peso_mb = buf.tell() / (1024 * 1024)
        if peso_mb <= limite_mb or calidad <= 30:
            break
        calidad -= 8

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
        if max(img.size) < 800:
            break

    return img, buf.getvalue()


def peso_mb(bytes_: bytes) -> float:
    """Convierte bytes a megabytes con dos decimales."""
    return len(bytes_) / (1024 * 1024)


# ---------- INTERFAZ ----------
st.title("📷 Fotos")
st.caption("Corrige, transforma y reduce tus fotografías — una a una o por lotes.")

herramienta = st.segmented_control(
    "¿Qué quieres hacer?",
    options=["Transformar fotografía", "Reducir tamaño (WhatsApp)"],
    default="Transformar fotografía",
)

# ---------- MODO 1: TRANSFORMAR (con lote) ----------
if herramienta == "Transformar fotografía":
    st.subheader("1 · Elige tus fotos (puedes subir varias)")
    archivos = st.file_uploader(
        "Arrastra una o varias fotos",
        type=FORMATOS_FOTO,
        accept_multiple_files=True,
    )

    if not archivos:
        st.info("👆 Sube una o varias fotos para empezar")
        st.stop()

    # Vista previa de las fotos subidas
    st.caption(f"Subidas: **{len(archivos)} foto(s)** — se aplicarán los mismos ajustes a todas")
    previews = st.columns(min(len(archivos), 6))
    for col, archivo in zip(previews, archivos):
        with col:
            st.image(Image.open(archivo), width=110)
            st.caption(f"{archivo.name[:18]}… ({peso_mb(archivo.getvalue()):.1f} MB)")

    st.subheader("2 · Correcciones simples")
    c1, c2 = st.columns(2)
    brillo = c1.slider("💡 Brillo", 0.5, 1.5, 1.0, 0.05)
    contraste = c2.slider("◐ Contraste", 0.5, 1.5, 1.0, 0.05)
    c3, c4 = st.columns(2)
    saturacion = c3.slider("🎨 Saturación", 0.0, 2.0, 1.0, 0.05)
    nitidez = c4.slider("✨ Nitidez", 0.0, 2.0, 1.0, 0.05)

    st.subheader("3 · Ajustes de forma")
    c5, c6, c7 = st.columns(3)
    rotacion = c5.selectbox("Rotar", [0, 90, 180, 270], index=0)
    volteo = c6.selectbox("Voltear", ["Ninguno", "Horizontal", "Vertical"])
    filtro = c7.selectbox("Filtro", ["Ninguno", "Blanco y negro", "Sepia", "Desenfoque suave"])

    st.subheader("4 · Tamaño y peso de salida")
    c8, c9, c10 = st.columns(3)
    ancho_max = c8.selectbox(
        "Ancho máximo (px)",
        ["Original", 4096, 2560, 1920, 1280, 800],
        help="Si la foto es más ancha, se reduce. 'Original' la deja igual.",
    )
    calidad = c9.slider("Calidad (JPG/WebP)", 30, 100, 85,
                        help="Menos calidad = menos peso. Recomendado: 85")
    formato_salida = c10.selectbox("Formato de salida", ["JPG", "PNG", "WEBP"])

    total_original = sum(peso_mb(a.getvalue()) for a in archivos)

    if st.button(f"Transformar {len(archivos)} foto(s)", type="primary"):
        # Preparar el ZIP con todas las fotos transformadas
        buf_zip = io.BytesIO()
        resultados = []
        estado = st.empty()
        progreso = st.empty()
        ancho_num = ancho_max if isinstance(ancho_max, int) else None

        with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for i, archivo in enumerate(archivos):
                estado.markdown(
                    f'<p class="giro-estado"><strong>{archivo.name}</strong> — transformando…</p>',
                    unsafe_allow_html=True,
                )
                progreso.markdown(giro_ui.barra_progreso(0, animado=True), unsafe_allow_html=True)

                img = Image.open(archivo)
                img_final, datos, ext = transformar_imagen(
                    img, rotacion, volteo, filtro, brillo, contraste,
                    saturacion, nitidez, ancho_num, calidad, formato_salida,
                )
                nombre_salida = f"{archivo.name.rsplit('.', 1)[0]}_{filtro.replace(' ', '_').lower() or 'editada'}.{ext}"
                z.writestr(nombre_salida, datos)
                resultados.append((archivo.name, img_final, datos, nombre_salida))

                pct = int((i + 1) / len(archivos) * 100)
                progreso.markdown(giro_ui.barra_progreso(pct), unsafe_allow_html=True)

        progreso.markdown(giro_ui.barra_progreso(100, ok=True), unsafe_allow_html=True)
        estado.markdown('<p class="giro-estado"><strong>✅ ¡Todas las fotos transformadas!</strong></p>',
                        unsafe_allow_html=True)

        # Métricas globales (peso y tamaño)
        total_nuevo = peso_mb(buf_zip.getvalue())
        st.success(f"✅ {len(resultados)} foto(s) transformadas")
        c_meta1, c_meta2, c_meta3 = st.columns(3)
        c_meta1.metric("Peso original (todas)", f"{total_original:.1f} MB")
        c_meta2.metric("Peso final (ZIP)", f"{total_nuevo:.1f} MB",
                       delta=f"{-100 + total_nuevo / max(total_original, 0.001) * 100:.0f}%")
        c_meta3.metric("Dimensiones finales", f"{img_final.width} × {img_final.height} px")

        # Previsualización de cada resultado
        st.subheader("Resultados")
        columnas = st.columns(min(len(resultados), 4))
        for col, (nombre_orig, img_final, datos, nombre_salida) in zip(columnas, resultados):
            with col:
                st.image(img_final, width=160)
                st.caption(f"{nombre_salida}\n({peso_mb(datos):.1f} MB)")

        st.download_button(
            "⬇️ Descargar ZIP con todas las fotos",
            data=buf_zip.getvalue(),
            file_name=f"fotos_transformadas_{len(resultados)}.zip",
            type="primary",
        )

# ---------- MODO 2: REDUCIR PARA WHATSAPP ----------
else:
    archivo = st.file_uploader("Sube la foto pesada", type=FORMATOS_FOTO, key="reducir")
    if archivo is None:
        st.info("👆 Sube una foto para empezar")
        st.stop()

    imagen_original = Image.open(archivo)
    imagen_original = ImageOps.exif_transpose(imagen_original)
    peso_original = peso_mb(archivo.getvalue())

    c_antes, c_despues = st.columns(2)
    with c_antes:
        st.image(imagen_original, caption=f"Original ({peso_original:.1f} MB)")
        st.caption(f"Dimensiones: **{imagen_original.width} × {imagen_original.height} px**")

    if st.button("Reducir para WhatsApp", type="primary"):
        img_final, bytes_jpg = reducir_para_whatsapp(imagen_original)
        peso_nuevo = peso_mb(bytes_jpg)

        with c_despues:
            st.image(img_final, caption=f"Reducida ({peso_nuevo:.1f} MB)")

        st.metric("Tamaño original", f"{peso_original:.1f} MB")
        st.metric("Tamaño reducido", f"{peso_nuevo:.1f} MB",
                  delta=f"{-100 + peso_nuevo / max(peso_original, 0.001) * 100:.0f}%")
        st.metric("Dimensiones", f"{img_final.width} × {img_final.height} px")

        if peso_nuevo <= LÍMITE_WHATSAPP_MB:
            st.success(f"✅ Lista para WhatsApp: pesa {peso_nuevo:.1f} MB (límite 16 MB)")
        else:
            st.warning("⚠️ Sigue pesando más de 16 MB (foto extremadamente grande)")

        st.download_button(
            "⬇️ Descargar foto reducida",
            data=bytes_jpg,
            file_name=f"whatsapp_{archivo.name.rsplit('.', 1)[0]}.jpg",
            type="primary",
        )
# FIN BLOQUE 1
