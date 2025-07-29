import os
import fitz  # PyMuPDF
import json
import uuid

def extraer_texto_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    texto = ""
    for page in doc:
        texto += page.get_text()
    return texto

def crear_entrada_libro(pdf_path):
    texto = extraer_texto_pdf(pdf_path)
    nombre_archivo = os.path.basename(pdf_path)
    entrada = {
        "id": str(uuid.uuid4()),
        "archivo": nombre_archivo,
        "titulo": nombre_archivo.replace(".pdf", ""),
        "autor": "Desconocido",
        "año": None,
        "texto": texto
    }
    return entrada

def procesar_carpeta(carpeta_pdf, salida_json="base_textos.json"):
    base = []
    for archivo in os.listdir(carpeta_pdf):
        if archivo.endswith(".pdf"):
            ruta_pdf = os.path.join(carpeta_pdf, archivo)
            print(f"Procesando: {archivo}")
            entrada = crear_entrada_libro(ruta_pdf)
            base.append(entrada)
    
    with open(salida_json, "w", encoding="utf-8") as f:
        json.dump(base, f, ensure_ascii=False, indent=2)
    print(f"Base guardada en {salida_json}")

# Ejecutar:
procesar_carpeta("SABIDURÍA/")