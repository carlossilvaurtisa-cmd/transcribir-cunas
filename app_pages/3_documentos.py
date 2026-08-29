# ============================================================
# BLOQUE 1: HERRAMIENTA 3 — DOCUMENTOS
# (CONVERTIR FORMATOS + PDF → IMÁGENES Y TEXTO)
# Con parámetros de personalización enfocados en el peso
# ============================================================
import io
import os
import tempfile
import zipfile

import streamlit as st
from PIL import Image, ImageOps

import giro_ui

try:
    import fitz  # PyMuPDF: leer/crear PDFs
except ImportError:
    st.error("❌ Falta la librería PyMuPDF (fitz). Ejecuta: pip install pymupdf")
    st.stop()

try:
    import docx  # python-docx: leer documentos de Word
except ImportError:
    docx = None


def pdf_a_texto(contenido):
    """Extrae el texto de un PDF, página por página."""
    doc = fitz.open(stream=contenido, filetype="pdf")
    paginas = []
    for i, pagina in enumerate(doc):
        texto = pagina.get_text().strip()
        paginas.append(f"--- Página {i + 1} ---\n{texto}")
    doc.close()
    return "\n\n".join(paginas)


def texto_a_pdf(texto, tamaño_pagina="A4", fontsize=10, margen=50, espaciado=14):
    """Crea un PDF a partir de un texto, con página, letra y márgenes elegibles."""
    if tamaño_pagina == "A4":
        ancho, alto = 595, 842
    else:  # Carta
        ancho, alto = 612, 792

    doc = fitz.open()
    pagina = doc.new_page(width=ancho, height=alto)
    y = margen
    chars_por_linea = max(20, int((ancho - 2 * margen) / (fontsize * 0.5)))

    for linea_original in texto.replace("\r", "").split("\n"):
        linea = linea_original
        while len(linea) > chars_por_linea:
            if y > alto - margen:
                pagina = doc.new_page(width=ancho, height=alto)
                y = margen
            pagina.insert_text((margen, y), linea[:chars_por_linea], fontsize=fontsize, fontname="helv")
            linea = linea[chars_por_linea:]
            y += espaciado
        if y > alto - margen:
            pagina = doc.new_page(width=ancho, height=alto)
            y = margen
        pagina.insert_text((margen, y), linea, fontsize=fontsize, fontname="helv")
        y += espaciado

    buf = io.BytesIO()
    doc.save(buf)
    doc.close()
    return buf.getvalue()


def docx_a_texto(contenido):
    """Extrae el texto de un documento de Word (.docx)."""
    if docx is None:
        raise RuntimeError("python-docx no está instalado")
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(contenido)
        ruta = tmp.name
    try:
        doc = docx.Document(ruta)
        return "\n".join(p.text for p in doc.paragraphs)
    finally:
        os.remove(ruta)


def pdf_a_imagenes(contenido, zoom, formato="PNG", calidad=80, bn=False):
    """Convierte cada página de un PDF en una imagen PNG o JPG.
    El formato y la calidad controlan directamente el peso final."""
    doc = fitz.open(stream=contenido, filetype="pdf")
    matriz = fitz.Matrix(zoom, zoom)
    imagenes = []
    for i, pagina in enumerate(doc):
        pix = pagina.get_pixmap(matrix=matriz)
        if formato == "PNG":
            datos = pix.tobytes("png")
            ext = "png"
        else:  # JPG pesa mucho menos
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            if bn:
                img = ImageOps.grayscale(img)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=calidad, optimize=True)
            datos = buf.getvalue()
            ext = "jpg"
        imagenes.append((f"pagina_{i + 1}.{ext}", datos))
    doc.close()
    return imagenes


def peso_mb(bytes_: bytes) -> float:
    """Convierte bytes a megabytes."""
    return len(bytes_) / (1024 * 1024)


# ---------- INTERFAZ ----------
st.title("📄 Documentos")
st.caption("Convierte formatos y transforma PDFs — con control del peso del archivo.")

herramienta = st.segmented_control(
    "¿Qué quieres hacer?",
    options=["Convertir formato de documento", "PDF → Imágenes y texto"],
    default="Convertir formato de documento",
)

# ---------- MODO 1: CONVERTIR FORMATOS ----------
if herramienta == "Convertir formato de documento":
    archivo = st.file_uploader("Sube tu documento", type=["txt", "md", "pdf", "docx"])
    if archivo is None:
        st.info("👆 Sube un documento para empezar")
        st.stop()

    ext = archivo.name.rsplit(".", 1)[-1].lower()
    destinos = {"txt": ["PDF"], "md": ["PDF"], "pdf": ["TXT"], "docx": ["TXT", "PDF"]}
    opciones = destinos.get(ext, [])
    if not opciones:
        st.error(f"❌ No sé convertir .{ext} todavía. Formatos: txt, md, pdf, docx")
        st.stop()

    destino = st.selectbox("Convertir a", opciones)
    nombre_base = archivo.name.rsplit(".", 1)[0]

    # Parámetros de personalización del PDF (solo si el destino es PDF)
    if destino == "PDF":
        st.subheader("Personalización del PDF")
        c1, c2 = st.columns(2)
        tamaño_pagina = c1.selectbox("Tamaño de página", ["A4", "Carta"])
        fontsize = c2.slider("Tamaño de letra", 8, 24, 11)
        c3, c4 = st.columns(2)
        margen = c3.slider("Margen (px)", 20, 90, 50)
        espaciado = c4.slider("Espaciado entre líneas (px)", 8, 40, 15)

    if st.button("Convertir", type="primary"):
        contenido = archivo.getvalue()
        try:
            if destino == "TXT":
                texto = pdf_a_texto(contenido) if ext == "pdf" else docx_a_texto(contenido)
                st.text_area("Contenido del texto", value=texto, height=250)
                st.download_button("⬇️ Descargar .txt", data=texto,
                                   file_name=f"{nombre_base}.txt", type="primary")
            else:  # destino == PDF
                texto = contenido.decode("utf-8", errors="replace") if ext in ("txt", "md") else docx_a_texto(contenido)
                pdf_bytes = texto_a_pdf(texto, tamaño_pagina, fontsize, margen, espaciado)
                st.metric("Peso del PDF resultante", f"{peso_mb(pdf_bytes):.2f} MB")
                st.success(f"✅ PDF creado ({len(pdf_bytes) // 1024} KB) con letra {fontsize}pt, página {tamaño_pagina}")
                st.download_button("⬇️ Descargar .pdf", data=pdf_bytes,
                                   file_name=f"{nombre_base}.pdf", type="primary")
        except Exception as e:
            st.error(f"❌ No pude convertir el archivo: {e}")

# ---------- MODO 2: PDF → IMÁGENES Y TEXTO ----------
else:
    archivo = st.file_uploader("Sube tu PDF", type=["pdf"])
    if archivo is None:
        st.info("👆 Sube un PDF para empezar")
        st.stop()

    peso_pdf = peso_mb(archivo.getvalue())

    st.subheader("Parámetros de conversión")
    c1, c2 = st.columns(2)
    zoom = c1.slider("Resolución (zoom)", 1.0, 4.0, 2.0, 0.5,
                     help="Más zoom = más nítido pero más pesado")
    formato_img = c2.selectbox("Formato de las imágenes", ["PNG (más pesado)", "JPG (más liviano)"])
    c3, c4 = st.columns(2)
    calidad_jpg = c3.slider("Calidad JPG (peso)", 30, 95, 75,
                            help="Menos calidad = mucho menos peso") if "JPG" in formato_img else c3.empty()
    bn = c4.checkbox("Blanco y negro (pesa menos)", value=False)
    incluir_texto = st.checkbox("Extraer también el texto (para copiar/editar)", value=True)

    if st.button("Convertir PDF", type="primary"):
        contenido = archivo.getvalue()
        try:
            formato = "JPG" if "JPG" in formato_img else "PNG"
            imagenes = pdf_a_imagenes(contenido, zoom, formato, calidad_jpg, bn)
            st.success(f"✅ {len(imagenes)} página(s) convertida(s) a {formato}")

            # Mostrar las páginas como imágenes
            for nombre, datos in imagenes:
                st.image(datos, caption=nombre)

            # ZIP con todo
            buf_zip = io.BytesIO()
            with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED) as z:
                for nombre, datos in imagenes:
                    z.writestr(nombre, datos)
                if incluir_texto:
                    z.writestr("texto_extraido.txt", pdf_a_texto(contenido))

            peso_zip = peso_mb(buf_zip.getvalue())
            st.metric("Peso del PDF original", f"{peso_pdf:.2f} MB")
            st.metric("Peso del ZIP resultante", f"{peso_zip:.2f} MB",
                      delta=f"{-100 + peso_zip / max(peso_pdf, 0.001) * 100:.0f}%")

            nombre_base = archivo.name.rsplit(".", 1)[0]
            st.download_button(
                "⬇️ Descargar ZIP (imágenes + texto)",
                data=buf_zip.getvalue(),
                file_name=f"{nombre_base}_paginas.zip",
                type="primary",
            )
        except Exception as e:
            st.error(f"❌ No pude convertir el PDF: {e}")
# FIN BLOQUE 1
