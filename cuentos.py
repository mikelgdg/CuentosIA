import json
import google.generativeai as genai
import random
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import re
import logging
from tqdm import tqdm
import time

genai.configure(api_key="AIzaSyALMtWMcZbBoUOoF3X1JFBN7visJrYH8cg")

# Configurar logging
def configurar_logging(carpeta_tema):
    """Configura el sistema de logging"""
    log_file = os.path.join(carpeta_tema, f"generacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"🚀 Iniciando generación de cuentos - Log guardado en: {log_file}")
    return logger

def cargar_base(path="base_textos.json"):
    """Carga la base de textos desde un archivo JSON"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            base = json.load(f)
        print(f"✅ Base de textos cargada: {len(base)} libros encontrados")
        return base
    except FileNotFoundError:
        print(f"❌ Error: No se encontró el archivo {path}")
        raise
    except json.JSONDecodeError as e:
        print(f"❌ Error al decodificar JSON: {e}")
        raise

def calcular_tokens_aproximados(texto):
    """Calcula una aproximación de tokens basada en caracteres y palabras"""
    # Aproximación: 1 token ≈ 4 caracteres en español
    # Para mayor precisión, consideramos espacios y puntuación
    palabras = len(texto.split())
    caracteres = len(texto)
    
    # Fórmula aproximada para español: promedio entre caracteres/4 y palabras*1.3
    tokens_por_chars = caracteres / 4
    tokens_por_palabras = palabras * 1.3
    
    return int((tokens_por_chars + tokens_por_palabras) / 2)

def obtener_texto_optimizado(libro, limite_tokens=800000):
    """
    Obtiene el máximo texto posible del libro sin exceder el límite de tokens.
    Deja margen de 50,000 tokens para el resto del prompt.
    """
    texto_completo = libro["texto"]
    
    # Si el texto es muy corto, devolverlo completo
    if len(texto_completo) < 10000:
        logging.info(f"📖 Texto corto detectado ({len(texto_completo)} caracteres), usando completo")
        return texto_completo
    
    # Calcular tokens del texto completo
    tokens_completos = calcular_tokens_aproximados(texto_completo)
    logging.info(f"📊 Texto original: {tokens_completos:,} tokens ({len(texto_completo):,} caracteres)")
    
    # Si cabe completo, devolverlo
    if tokens_completos <= limite_tokens:
        logging.info(f"✅ Texto completo cabe en el límite ({tokens_completos:,} <= {limite_tokens:,})")
        return texto_completo
    
    logging.warning(f"⚠️ Texto excede límite, aplicando optimización ({tokens_completos:,} > {limite_tokens:,})")
    
    # Si no cabe, calcular cuánto texto podemos usar
    ratio_permitido = limite_tokens / tokens_completos
    caracteres_permitidos = int(len(texto_completo) * ratio_permitido)
    logging.info(f"🔧 Ratio permitido: {ratio_permitido:.2%}, caracteres permitidos: {caracteres_permitidos:,}")
    
    # Cortar en un punto lógico (final de párrafo o frase)
    texto_cortado = texto_completo[:caracteres_permitidos]
    
    # Buscar el último punto o salto de línea para cortar limpiamente
    ultimo_punto = texto_cortado.rfind('.')
    ultimo_parrafo = texto_cortado.rfind('\n\n')
    
    punto_corte = max(ultimo_punto, ultimo_parrafo)
    
    if punto_corte > caracteres_permitidos * 0.8:  # Si el corte está cerca del final
        texto_final = texto_cortado[:punto_corte + 1]
    else:
        texto_final = texto_cortado
    
    # Verificar que no excedamos el límite
    tokens_finales = calcular_tokens_aproximados(texto_final)
    
    print(f"📊 Texto optimizado: {tokens_finales:,} tokens (~{len(texto_final):,} caracteres)")
    logging.info(f"📊 Optimización completada: {tokens_finales:,} tokens finales")
    
    return texto_final

def construir_prompt(libro, tema, personajes):
    logging.info(f"🔧 Construyendo prompt para '{libro['titulo']}' con tema '{tema}'")
    personajes_str = ", ".join(personajes)
    
    # Usar el sistema optimizado en lugar del límite fijo de 4000 caracteres
    texto = obtener_texto_optimizado(libro)
    
    prompt = f"""
Eres un narrador inspirado por textos sagrados y filosóficos.

Has leído un texto de sabiduría espiritual o filosófica. A partir de este texto:

--- TEXTO DEL LIBRO ---
{texto}
--- FIN DEL TEXTO ---

Ahora quiero que escribas un cuento corto original y extremadamente creativo, tanto en estilo como en contenido y estructura, que transmita el siguiente tema: "{tema}". 
Utiliza a los siguientes personajes: {personajes_str}.

El cuento debe transmitir la esencia del texto original, de forma poética o narrativa, como si fuera una parábola o una fábula.
Debe ir dirigido tanto a adultos como a niños muy pequeños. No debe incluir la moraleja explícitamente, sino que debe dejar que el lector la descubra por sí mismo.
Evita terminar diciendo que un personaje comprendió la lección, sino que el lector debe deducirla a partir de la historia.

La estructura ha de ser radicalmente innovadora, con un estilo único y creativo.
"""
    
    # Verificar el tamaño total del prompt
    tokens_prompt = calcular_tokens_aproximados(prompt)
    print(f"🔍 Prompt total: {tokens_prompt:,} tokens")
    logging.info(f"📊 Prompt construido: {tokens_prompt:,} tokens totales")
    
    return prompt

def generar_cuento(prompt, libro_titulo):
    """Genera un cuento usando el modelo Gemini"""
    logging.info(f"🤖 Iniciando generación de cuento para: {libro_titulo}")
    
    try:
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        with tqdm(total=1, desc=f"🤖 Generando cuento: {libro_titulo[:30]}...") as pbar:
            start_time = time.time()
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.2,
                    'max_output_tokens': 1000,
                }
            )
            end_time = time.time()
            pbar.update(1)
        
        generation_time = end_time - start_time
        cuento_length = len(response.text)
        
        logging.info(f"✅ Cuento generado exitosamente en {generation_time:.2f}s - {cuento_length} caracteres")
        print(f"⏱️ Tiempo de generación: {generation_time:.2f}s")
        
        return response.text
        
    except Exception as e:
        logging.error(f"❌ Error en generación de cuento para {libro_titulo}: {str(e)}")
        raise

def limpiar_nombre_archivo(nombre):
    """Limpia el nombre del archivo para que sea válido en el sistema de archivos"""
    nombre = re.sub(r'[<>:"/\\|?*]', '', nombre)
    nombre = nombre.replace(' ', '_')
    return nombre[:50]  # Limitar longitud

def crear_carpetas(tema):
    """Crea la estructura de carpetas necesaria"""
    logging.info(f"📁 Creando estructura de carpetas para tema: {tema}")
    
    tema_limpio = limpiar_nombre_archivo(tema)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    carpeta_base = "CUENTOS"
    carpeta_tema = os.path.join(carpeta_base, tema_limpio, timestamp)
    
    os.makedirs(carpeta_tema, exist_ok=True)
    logging.info(f"✅ Carpetas creadas: {carpeta_tema}")
    
    return carpeta_tema

def guardar_prompt(carpeta_tema, prompt, tema, personajes):
    """Guarda el prompt usado en un archivo de texto"""
    logging.info("💾 Guardando prompt de sesión")
    
    nombre_archivo = "prompt.txt"
    ruta_archivo = os.path.join(carpeta_tema, nombre_archivo)
    
    contenido = f"""GENERACIÓN DE CUENTOS - PROMPT USADO
=====================================

FECHA: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
TEMA: {tema}
PERSONAJES: {', '.join(personajes)}

PROMPT COMPLETO:
{'-' * 50}
{prompt}
{'-' * 50}
"""
    
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write(contenido)
    
    logging.info(f"✅ Prompt guardado en: {ruta_archivo}")
    return ruta_archivo

def crear_pdf_elegante(cuento, libro, tema, personajes, carpeta_tema):
    """Crea un PDF elegante con el cuento"""
    logging.info(f"📄 Creando PDF para: {libro['titulo']}")
    
    titulo_libro = limpiar_nombre_archivo(libro['titulo'])
    autor = libro.get('autor', 'Desconocido')

    
    nombre_pdf = f"{titulo_libro}.pdf"
    ruta_pdf = os.path.join(carpeta_tema, nombre_pdf)
    
    try:
        # Crear documento PDF
        doc = SimpleDocTemplate(ruta_pdf, pagesize=A4,
                              rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Estilos
        styles = getSampleStyleSheet()
        
        # Estilo personalizado para el título
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1,  # Centrado
            textColor='#2C3E50'
        )
        
        # Estilo para subtítulos
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=20,
            alignment=1,
            textColor='#34495E'
        )
        
        # Estilo para el cuerpo del texto
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=12,
            leading=18,
            spaceAfter=12,
            alignment=4,  # Justificado
            textColor='#2C3E50'
        )
        
        # Estilo para información adicional
        info_style = ParagraphStyle(
            'CustomInfo',
            parent=styles['Normal'],
            fontSize=10,
            leading=14,
            spaceAfter=6,
            textColor='#7F8C8D'
        )
        
        # Contenido del PDF
        story = []
        
        # Título principal
        story.append(Paragraph(f"Cuento Inspirado en:<br/>{libro['titulo']}", title_style))
        story.append(Spacer(1, 20))
        
        # Información del cuento
        story.append(Paragraph(f"Tema: {tema}", subtitle_style))
        story.append(Paragraph(f"Personajes: {', '.join(personajes)}", info_style))
        story.append(Paragraph(f"Inspirado en: {libro['titulo']} - {autor}", info_style))
        story.append(Paragraph(f"Generado el: {datetime.now().strftime('%d de %B de %Y')}", info_style))
        story.append(Spacer(1, 30))
        
        # Línea separadora
        story.append(Paragraph("─" * 50, info_style))
        story.append(Spacer(1, 20))
        
        # El cuento
        paragrafos = cuento.split('\n\n')
        for paragrafo in paragrafos:
            if paragrafo.strip():
                story.append(Paragraph(paragrafo.strip(), body_style))
                story.append(Spacer(1, 12))
        
        # Construir PDF
        doc.build(story)
        logging.info(f"✅ PDF creado exitosamente: {ruta_pdf}")
        return ruta_pdf
        
    except Exception as e:
        logging.error(f"❌ Error creando PDF para {libro['titulo']}: {str(e)}")
        raise

def cuentos_para_todos(tema, personajes):
    base = cargar_base()
    carpeta_tema = crear_carpetas(tema)
    
    # Configurar logging después de crear las carpetas
    logger = configurar_logging(carpeta_tema)
    logger.info(f"🎯 Iniciando generación masiva - Tema: '{tema}', Personajes: {personajes}")
    
    print(f"📁 Guardando cuentos en: {carpeta_tema}")
    
    # Guardar el prompt una sola vez por sesión
    libro_ejemplo = base[0] if base else {"texto": "Texto de ejemplo"}
    prompt_ejemplo = construir_prompt(libro_ejemplo, tema, personajes)
    ruta_prompt = guardar_prompt(carpeta_tema, prompt_ejemplo, tema, personajes)
    print(f"📝 Prompt guardado en: {ruta_prompt}")
    
    cuentos_generados = []
    errores = []
    
    # Usar tqdm para mostrar progreso
    with tqdm(total=len(base), desc="📚 Procesando libros", unit="libro") as pbar_libros:
        for i, libro in enumerate(base):
            try:
                pbar_libros.set_description(f"📚 {libro['titulo'][:30]}...")
                logger.info(f"📖 Procesando libro {i+1}/{len(base)}: {libro['titulo']}")
                
                prompt = construir_prompt(libro, tema, personajes)
                cuento = generar_cuento(prompt, libro['titulo'])
                
                # Mostrar en consola
                print(f"\n📘 Cuento inspirado en: {libro['titulo']}")
                print(cuento)
                print("\n" + "="*50 + "\n")
                
                # Crear PDF elegante
                ruta_pdf = crear_pdf_elegante(cuento, libro, tema, personajes, carpeta_tema)
                print(f"📄 PDF guardado: {ruta_pdf}")
                
                cuentos_generados.append({
                    'libro': libro['titulo'],
                    'autor': libro.get('autor', 'Desconocido'),
                    'pdf': ruta_pdf,
                    'cuento': cuento
                })
                
                logger.info(f"✅ Libro procesado exitosamente: {libro['titulo']}")
                
            except Exception as e:
                error_msg = f"Error generando cuento para {libro['titulo']}: {str(e)}"
                print(f"❌ {error_msg}")
                logger.error(f"❌ {error_msg}")
                errores.append({
                    'libro': libro['titulo'],
                    'error': str(e)
                })
            
            finally:
                pbar_libros.update(1)
                # Pequeña pausa para evitar rate limiting
                time.sleep(1)
    
    # Crear resumen de la sesión
    crear_resumen_sesion(carpeta_tema, tema, personajes, cuentos_generados, errores)
    
    # Resumen final
    total_procesados = len(cuentos_generados) + len(errores)
    logger.info(f"🏁 Procesamiento completado: {len(cuentos_generados)} éxitos, {len(errores)} errores de {total_procesados} libros")
    
    print(f"\n✅ Generación completada. {len(cuentos_generados)} cuentos guardados en {carpeta_tema}")
    if errores:
        print(f"⚠️ {len(errores)} errores ocurrieron durante el procesamiento")
        for error in errores:
            print(f"   - {error['libro']}: {error['error']}")
    
    return cuentos_generados, errores

def crear_resumen_sesion(carpeta_tema, tema, personajes, cuentos_generados, errores=None):
    """Crea un archivo resumen de la sesión"""
    logging.info("📊 Creando resumen de sesión")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_resumen = f"resumen_sesion_{timestamp}.txt"
    ruta_resumen = os.path.join(carpeta_tema, nombre_resumen)
    
    if errores is None:
        errores = []
    
    contenido = f"""RESUMEN DE SESIÓN - GENERACIÓN DE CUENTOS
=========================================

FECHA: {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
TEMA: {tema}
PERSONAJES: {', '.join(personajes)}
TOTAL CUENTOS GENERADOS: {len(cuentos_generados)}
TOTAL ERRORES: {len(errores)}
TASA DE ÉXITO: {len(cuentos_generados)/(len(cuentos_generados)+len(errores))*100:.1f}%

CUENTOS GENERADOS EXITOSAMENTE:
{'-' * 50}
"""
    
    for i, cuento_info in enumerate(cuentos_generados, 1):
        contenido += f"{i}. {cuento_info['libro']} - {cuento_info['autor']}\n"
        contenido += f"   PDF: {os.path.basename(cuento_info['pdf'])}\n\n"
    
    if errores:
        contenido += f"\nERRORES ENCONTRADOS:\n{'-' * 50}\n"
        for i, error in enumerate(errores, 1):
            contenido += f"{i}. {error['libro']}\n"
            contenido += f"   Error: {error['error']}\n\n"
    
    with open(ruta_resumen, "w", encoding="utf-8") as f:
        f.write(contenido)
    
    logging.info(f"✅ Resumen guardado en: {ruta_resumen}")

# Ejemplo de uso:
if __name__ == "__main__":
    cuentos_para_todos("el arrepentimiento y el perdón", ["una urraca", "un zorro", "un diamante"])