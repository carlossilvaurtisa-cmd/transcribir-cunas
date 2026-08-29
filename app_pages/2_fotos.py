# ============================================================
# BLOQUE 1: HERRAMIENTA 2 — FOTOS
# (TRANSFORMAR LOTE + CORREGIR FOTO POR FOTO CON LOTE)
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


def corregir_imagen(img, brillo, contraste, saturacion, nitidez):
    """Aplica solo las correcciones de luz y color a una imagen."""
    nueva = ImageOps.exif_transpose(img)
    es_gris = nueva.mode == "L"
    nueva = ImageEnhance.Brightness(nueva).enhance(brillo)
    nueva = ImageEnhance.Contrast(nueva).enhance(contraste)
    if not es_gris:
        nueva = ImageEnhance.Color(nueva).enhance(saturacion)
    nueva = ImageEnhance.Sharpness(nueva).enhance(nitidez)
    return nueva


def transformar_imagen(img, rotacion, volteo, filtro, ajuste_tipo, ajuste_valor, formato_salida):
    """Aplica forma y ajuste de tamaño/peso a UNA imagen.
    ajuste_tipo: 'porcentaje' (escala %) o 'peso' (objetivo MB).
    Devuelve (imagen, bytes, extensión, peso_logrado_mb)."""
    nueva = ImageOps.exif_transpose(img)

    if rotacion:
        nueva = nueva.rotate(rotacion, expand=True)
    if volteo == "Horizontal":
        nueva = ImageOps.mirror(nueva)
    elif volteo == "Vertical":
        nueva = ImageOps.flip(nueva)

    if filtro == "Blanco y negro":
        nueva = ImageOps.grayscale(nueva)
    elif filtro == "Sepia":
        nueva = aplicar_sepia(nueva)
    elif filtro == "Desenfoque suave":
        nueva = nueva.filter(ImageFilter.GaussianBlur(2))

    ext = {"JPG": "jpg", "PNG": "png", "WEBP": "webp"}[formato_salida]

    # Ajuste por PORCENTAJE: se escala el tamaño de la foto
    if ajuste_tipo == "porcentaje":
        pct = ajuste_valor / 100
        nueva = nueva.resize((max(1, int(nueva.width * pct)), max(1, int(nueva.height * pct))), Image.LANCZOS)
        buf = io.BytesIO()
        if nueva.mode in ("RGBA", "P", "LA") and ext == "jpg":
            nueva = nueva.convert("RGB")
        if formato_salida == "JPG":
            nueva.save(buf, "JPEG", quality=90, optimize=True)
        elif formato_salida == "PNG":
            nueva.save(buf, "PNG", optimize=True)
        else:
            nueva.save(buf, "WEBP", quality=90, optimize=True)
        return nueva, buf.getvalue(), ext, peso_mb(buf.getvalue())

    # Ajuste por PESO OBJETIVO: se comprime hasta alcanzar el peso pedido
    fmt_pil = {"JPG": "JPEG", "WEBP": "WEBP"}.get(formato_salida)
    if fmt_pil is None:   # PNG no se puede comprimir a un peso pedido
        buf = io.BytesIO()
        if nueva.mode in ("RGBA", "P", "LA"):
            nueva = nueva.convert("RGB")
        nueva.save(buf, "PNG", optimize=True)
        return nueva, buf.getvalue(), ext, peso_mb(buf.getvalue())
    img_final, datos = ajustar_a_peso(nueva, ajuste_valor, fmt_pil)
    return img_final, datos, ext, peso_mb(datos)


def ajustar_a_peso(img, limite_mb, fmt="JPEG"):
    """Comprime una foto hasta que pese menos del límite (en MB).
    Baja la calidad primero; si no basta, baja la resolución."""
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")
    ancho_max = 4096
    if max(img.size) > ancho_max:
        img.thumbnail((ancho_max, ancho_max), Image.LANCZOS)
    calidad = 88
    while True:
        buf = io.BytesIO()
        img.save(buf, fmt, quality=calidad, optimize=True)
        peso_mb = buf.tell() / (1024 * 1024)
        if peso_mb <= limite_mb or calidad <= 30:
            break
        calidad -= 8
    while peso_mb > limite_mb:
        img.thumbnail((max(img.size) // 2, max(img.size) // 2), Image.LANCZOS)
        calidad = 85
        while True:
            buf = io.BytesIO()
            img.save(buf, fmt, quality=calidad, optimize=True)
            peso_mb = buf.tell() / (1024 * 1024)
            if peso_mb <= limite_mb or calidad <= 25:
                break
            calidad -= 8
        if max(img.size) < 800:
            break
    return img, buf.getvalue()


def reducir_para_whatsapp(img, limite_mb=LÍMITE_WHATSAPP_MB):
    """Reduce una foto hasta 16 MB (WhatsApp). Reutiliza el ajuste por peso."""
    return ajustar_a_peso(img, limite_mb, "JPEG")


def peso_mb(bytes_: bytes) -> float:
    """Convierte bytes a megabytes."""
    return len(bytes_) / (1024 * 1024)


# ---------- ESTADO DE SESIÓN (se conserva entre clics) ----------
if "lote" not in st.session_state:
    st.session_state["lote"] = []          # fotos corregidas: [(nombre, bytes)]
if "hechas" not in st.session_state:
    st.session_state["hechas"] = set()     # nombres de fotos ya corregidas
if "editando" not in st.session_state:
    st.session_state["editando"] = None    # foto que se está corrigiendo ahora


# ---------- INTERFAZ ----------
st.title("📷 Fotos")
st.caption("Transforma lotes de fotos o corrige una por una y exporta.")

herramienta = st.segmented_control(
    "¿Qué desea hacer?",
    options=["Transformar foto / lote", "Corregir foto por foto"],
    default="Transformar foto / lote",
)

# ============================================================
# MODO 1: TRANSFORMAR FOTO / LOTE (forma + tamaño + exportar)
# ============================================================
if herramienta == "Transformar foto / lote":
    st.subheader("1 · Elige tus fotos (puedes subir varias)")
    archivos = st.file_uploader("Arrastra una o varias fotos", type=FORMATOS_FOTO,
                                accept_multiple_files=True, key="transformar_lote")

    # Memoria: guarda los archivos y los recupera al volver a esta pestaña
    if archivos:
        giro_ui.recordar_archivos("memoria_fotos", archivos)
    elif giro_ui.archivos_en_memoria("memoria_fotos"):
        archivos = giro_ui.archivos_en_memoria("memoria_fotos")

    if not archivos:
        st.info("👆 Sube una o varias fotos para empezar")
        st.stop()

    giro_ui.mostrar_aviso_memoria(
        "memoria_fotos",
        f"📌 {len(archivos)} foto(s) recordadas de la sesión anterior — se usarán estas",
    )

    st.caption(f"Subidas: **{len(archivos)} foto(s)** — mismas transformaciones para todas")
    previews = st.columns(min(len(archivos), 6))
    for col, archivo in zip(previews, archivos):
        with col:
            st.image(Image.open(archivo), width=110)
            st.caption(f"{archivo.name[:16]}… ({peso_mb(archivo.getvalue()):.1f} MB)")

    with st.expander("🔄 Ajustes de forma — rotar, voltear, filtro", expanded=False):
        c5, c6, c7 = st.columns(3)
        rotacion = c5.selectbox("Rotar", [0, 90, 180, 270], index=0)
        volteo = c6.selectbox("Voltear", ["Ninguno", "Horizontal", "Vertical"])
        filtro = c7.selectbox("Filtro", ["Ninguno", "Blanco y negro", "Sepia", "Desenfoque suave"])

    with st.expander("⚖️ Tamaño y peso de salida", expanded=False):
        modo_tamaño = st.selectbox(
            "Ajustar por",
            ["Porcentaje del tamaño original", "Peso del archivo (MB)"],
            help="Porcentaje = escala la foto al % del tamaño. Peso = comprime hasta alcanzar los MB pedidos.",
        )
        if modo_tamaño == "Porcentaje del tamaño original":
            ajuste_tipo = "porcentaje"
            ajuste_valor = st.slider("Porcentaje del tamaño original (%)", 10, 100, 50, 5,
                                     help="50% = la foto queda a la mitad de su tamaño en píxeles")
        else:
            ajuste_tipo = "peso"
            ajuste_valor = st.slider("Peso objetivo (MB)", 0.5, 32.0, 5.0, 0.5,
                                     help="La app baja calidad y resolución hasta acercarse a este peso")
        formato_salida = st.selectbox("Formato de salida", ["JPG", "PNG", "WEBP"])
        if ajuste_tipo == "peso" and formato_salida == "PNG":
            st.warning("⚠️ El formato PNG no se puede comprimir a un peso pedido. Usa JPG o WEBP para el peso objetivo.")
        st.caption("💡 El modo **Peso (MB)** es ideal para WhatsApp, correo o subir a la web.")

    total_original = sum(peso_mb(a.getvalue()) for a in archivos)

    if st.button(f"Transformar {len(archivos)} foto(s)", type="primary"):
        buf_zip = io.BytesIO()
        resultados = []
        estado = st.empty()
        progreso = st.empty()

        with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for i, archivo in enumerate(archivos):
                estado.markdown(
                    f'<p class="giro-estado"><strong>{archivo.name}</strong> — transformando…</p>',
                    unsafe_allow_html=True,
                )
                progreso.markdown(giro_ui.barra_progreso(0, animado=True), unsafe_allow_html=True)

                img = Image.open(archivo)
                img_final, datos, ext, peso_logrado = transformar_imagen(
                    img, rotacion, volteo, filtro, ajuste_tipo, ajuste_valor, formato_salida,
                )
                nombre_salida = f"{archivo.name.rsplit('.', 1)[0]}_{filtro.replace(' ', '_').lower() or 'editada'}.{ext}"
                z.writestr(nombre_salida, datos)
                resultados.append((archivo.name, img_final, datos, nombre_salida))

                pct = int((i + 1) / len(archivos) * 100)
                progreso.markdown(giro_ui.barra_progreso(pct), unsafe_allow_html=True)

        progreso.markdown(giro_ui.barra_progreso(100, ok=True), unsafe_allow_html=True)
        estado.markdown('<p class="giro-estado"><strong>✅ ¡Todas las fotos transformadas!</strong></p>',
                        unsafe_allow_html=True)

        total_nuevo = peso_mb(buf_zip.getvalue())
        st.success(f"✅ {len(resultados)} foto(s) transformadas")
        c_meta1, c_meta2, c_meta3 = st.columns(3)
        c_meta1.metric("Peso original (todas)", f"{total_original:.1f} MB")
        c_meta2.metric("Peso final (ZIP)", f"{total_nuevo:.1f} MB",
                       delta=f"{-100 + total_nuevo / max(total_original, 0.001) * 100:.0f}%")
        if ajuste_tipo == "peso":
            c_meta3.metric("Peso por foto", f"{peso_logrado:.1f} MB",
                           delta=f"objetivo: {ajuste_valor:.1f} MB")
        else:
            c_meta3.metric("Dimensiones finales", f"{img_final.width} × {img_final.height} px")

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

# ============================================================
# MODO 2: CORREGIR FOTO POR FOTO (con lote y confirmación)
# ============================================================
else:
    st.subheader("1 · Sube las fotos a corregir")
    archivos = st.file_uploader("Arrastra una o varias fotos", type=FORMATOS_FOTO,
                                accept_multiple_files=True, key="corregir_lote")

    # Memoria: guarda los archivos y los recupera al volver a esta pestaña
    if archivos:
        giro_ui.recordar_archivos("memoria_fotos", archivos)
    elif giro_ui.archivos_en_memoria("memoria_fotos"):
        archivos = giro_ui.archivos_en_memoria("memoria_fotos")

    if not archivos:
        st.info("👆 Sube las fotos que quieres corregir")
        st.stop()

    giro_ui.mostrar_aviso_memoria(
        "memoria_fotos",
        f"📌 {len(archivos)} foto(s) recordadas de la sesión anterior",
    )

    pendientes = [a for a in archivos if a.name not in st.session_state["hechas"]]

    # ---------- Fotos pendientes (elige una para corregir) ----------
    if pendientes:
        st.subheader("2 · Elige una foto para corregir")
        cols = st.columns(min(len(pendientes), 4))
        for col, a in zip(cols, pendientes):
            with col:
                st.image(Image.open(a), width=130)
                st.caption(f"{a.name[:16]}… ({peso_mb(a.getvalue()):.1f} MB)")
                if st.button(f"✏️ Editar {a.name[:14]}", key=f"edit_{a.name}", width="stretch"):
                    st.session_state["editando"] = a.name
                    st.rerun()

    # ---------- Panel de edición de la foto elegida ----------
    if st.session_state["editando"]:
        archivo_actual = next((a for a in archivos if a.name == st.session_state["editando"]), None)
        if archivo_actual is not None:
            st.divider()
            st.subheader(f"✏️ Corrigiendo: {archivo_actual.name}")
            img = Image.open(archivo_actual)
            img = ImageOps.exif_transpose(img)

            c1, c2 = st.columns(2)
            brillo = c1.slider("💡 Brillo", 0.5, 1.5, 1.0, 0.05, key=f"br_{archivo_actual.name}")
            contraste = c2.slider("◐ Contraste", 0.5, 1.5, 1.0, 0.05, key=f"co_{archivo_actual.name}")
            c3, c4 = st.columns(2)
            saturacion = c3.slider("🎨 Saturación", 0.0, 2.0, 1.0, 0.05, key=f"sa_{archivo_actual.name}")
            nitidez = c4.slider("✨ Nitidez", 0.0, 2.0, 1.0, 0.05, key=f"ni_{archivo_actual.name}")

            corregida = corregir_imagen(img, brillo, contraste, saturacion, nitidez)

            v1, v2 = st.columns(2)
            with v1:
                st.image(img, caption="Original")
            with v2:
                st.image(corregida, caption="Corregida")

            c_ok, c_reset, c_wa = st.columns(3)
            if c_ok.button("✅ Confirmar y añadir al lote", type="primary", key=f"ok_{archivo_actual.name}"):
                buf = io.BytesIO()
                if corregida.mode in ("RGBA", "P", "LA"):
                    corregida = corregida.convert("RGB")
                corregida.save(buf, "JPEG", quality=92, optimize=True)
                st.session_state["lote"].append((archivo_actual.name, buf.getvalue()))
                st.session_state["hechas"].add(archivo_actual.name)
                st.session_state["editando"] = None
                st.rerun()

            if c_reset.button("🔄 Restablecer", key=f"reset_{archivo_actual.name}"):
                for prefijo in ("br_", "co_", "sa_", "ni_"):
                    st.session_state.pop(f"{prefijo}{archivo_actual.name}", None)
                st.rerun()

            with c_wa:
                if st.button("📱 Reducir para WhatsApp", key=f"wa_{archivo_actual.name}",
                             help="Comprime la foto corregida a menos de 16 MB y la añade al lote"):
                    img_final, bytes_jpg = reducir_para_whatsapp(corregida)
                    st.session_state["lote"].append((f"wa_{archivo_actual.name}", bytes_jpg))
                    st.session_state["hechas"].add(archivo_actual.name)
                    st.session_state["editando"] = None
                    st.rerun()

    # ---------- Lote de fotos corregidas ----------
    if st.session_state["lote"]:
        st.divider()
        st.subheader(f"📦 Lote de corregidas ({len(st.session_state['lote'])})")
        lote = st.session_state["lote"]
        cols = st.columns(min(len(lote), 4))
        for col, (nombre, datos) in zip(cols, lote):
            with col:
                st.image(datos, width=130)
                st.caption(f"{nombre[:16]}… ({peso_mb(datos):.1f} MB)")
                if st.button(f"🗑️ Quitar", key=f"quitar_{nombre}"):
                    st.session_state["lote"] = [(n, d) for n, d in st.session_state["lote"] if n != nombre]
                    st.rerun()

        total_lote = sum(peso_mb(d) for _, d in lote)
        st.metric("Peso total del lote", f"{total_lote:.1f} MB")

        buf_zip = io.BytesIO()
        with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED) as z:
            for i, (nombre, datos) in enumerate(lote):
                z.writestr(f"{i + 1:02d}_{nombre.rsplit('.', 1)[0]}.jpg", datos)

        st.download_button(
            "📦 Exportar lote (ZIP)",
            data=buf_zip.getvalue(),
            file_name="lote_corregidas.zip",
            type="primary",
        )

        if st.button("🧹 Vaciar lote"):
            st.session_state["lote"] = []
            st.session_state["hechas"] = set()
            st.session_state["editando"] = None
            st.rerun()
# FIN BLOQUE 1
