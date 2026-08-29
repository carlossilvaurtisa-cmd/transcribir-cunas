# ============================================================
# BLOQUE 1: HERRAMIENTA 3 — DOCUMENTOS
# (CONVERTIR FORMATOS + PDF → IMÁGENES Y TEXTO)
# ============================================================
import io
import os
import tempfile
import zipfile

import streamlit as st

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


def texto_a_pdf(texto):
    """Crea un PDF simple a partir de un texto (con paginación automática)."""
    doc = fitz.open()
    pagina = doc.new_page()
    y = 50
    for linea_original in texto.replace("\r", "").split("\n"):
        # Cortar líneas muy largas para que no se salgan de la página
        linea = linea_original
        while len(linea) > 90:
            if y > 780:
                pagina = doc.new_page()
                y = 50
            pagina.insert_text((50, y), linea[:90], fontsize=10, fontname="helv")
            linea = linea[90:]
            y += 14
        if y > 780:
            pagina = doc.new_page()
            y = 50
        pagina.insert_text((50, y), linea, fontsize=10, fontname="helv")
        y += 14
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
        return "\n".join(p.texto if False else p.text for p in doc.paragraphs)
    finally:
        os.remove(ruta)


def pdf_a_imagenes(contenido, zoom):
    """Convierte cada página de un PDF en una imagen PNG."""
    doc = fitz.open(stream=contenido, filetype="pdf")
    matriz = fitz.Matrix(zoom, zoom)
    imagenes = []
    for i, pagina in enumerate(doc):
        pix = pagina.get_pixmap(matrix=matriz)
        imagenes.append((f"pagina_{i + 1}.png", pix.tobytes("png")))
    doc.close()
    return imagenes


# ---------- INTERFAZ ----------
st.title("📄 Documentos")
st.caption("Convierte formatos de documentos y transforma PDFs en imágenes y texto.")

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
    # Destinos posibles según el tipo de archivo
    destinos = {"txt": ["PDF"], "md": ["PDF"], "pdf": ["TXT"], "docx": ["TXT", "PDF"]}
    opciones = destinos.get(ext, [])
    if not opciones:
        st.error(f"❌ No sé convertir .{ext} todavía. Formatos: txt, md, pdf, docx")
        st.stop()

    destino = st.selectbox("Convertir a", opciones)
    nombre_base = archivo.name.rsplit(".", 1)[0]

    if st.button("Convertir", type="primary"):
        contenido = archivo.getvalue()
        try:
            if destino == "TXT":
                if ext == "pdf":
                    texto = pdf_a_texto(contenido)
                else:  # docx
                    texto = docx_a_texto(contenido)
                st.text_area("Contenido del texto", value=texto, height=250)
                st.download_button("⬇️ Descargar .txt", data=texto,
                                   file_name=f"{nombre_base}.txt", type="primary")
            else:  # destino == "PDF"
                if ext in ("txt", "md"):
                    texto = contenido.decode("utf-8", errors="replace")
                else:  # docx
                    texto = docx_a_texto(contenido)
                pdf_bytes = texto_a_pdf(texto)
                st.success(f"✅ PDF creado con {len(pdf_bytes) // 1024} KB")
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

    zoom = st.slider("Calidad de las imágenes", 1.0, 4.0, 2.0, 0.5,
                     help="Más zoom = imágenes más nítidas pero más pesadas")
    incluir_texto = st.checkbox("Extraer también el texto (para copiar/editar)", value=True)

    if st.button("Convertir PDF", type="primary"):
        contenido = archivo.getvalue()
        try:
            imagenes = pdf_a_imagenes(contenido, zoom)
            st.success(f"✅ {len(imagenes)} página(s) convertida(s)")

            # Mostrar las páginas como imágenes
            for nombre, datos in imagenes:
                st.image(datos, caption=nombre)

            # Preparar el ZIP con las imágenes
            buf_zip = io.BytesIO()
            with zipfile.ZipFile(buf_zip, "w", zipfile.ZIP_DEFLATED) as z:
                for nombre, datos in imagenes:
                    z.writestr(nombre, datos)
                if incluir_texto:
                    z.writestr("texto_extraido.txt", pdf_a_texto(contenido))

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
