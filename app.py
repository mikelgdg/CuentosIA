import streamlit as st
import google.generativeai as genai
import json
import os
import random
from rotacion_claves import get_api_rotator

# Configuración de página mejorada
st.set_page_config(
    page_title="AIfil",
    page_icon=".streamlit/logo2.png",  # Usar tu logo como icono de la pestaña
    layout="centered",
    initial_sidebar_state="expanded"
)

# Cargar CSS personalizado
def load_css():
    """Carga el CSS personalizado"""
    css_file = ".streamlit/_style.css"
    if os.path.exists(css_file):
        with open(css_file) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Obtener el rotador de claves API
api_rotator = get_api_rotator()

# --- Funciones de carga de base y procesamiento de texto (adaptadas de cuentos.py) ---
def cargar_base(path="base_textos.json"):
    """Carga la base de textos desde un archivo JSON."""
    if not os.path.exists(path):
        # Crear un archivo base_textos.json de ejemplo si no existe
        # Esto es crucial para que la aplicación no falle al iniciar si el usuario no tiene el archivo.
        ejemplo_base = [
            {
                "titulo": "El Arte de la Guerra",
                "autor": "Sun Tzu",
                "texto": "El arte de la guerra se basa en el engaño. Por lo tanto, cuando eres capaz de atacar, debes parecer incapaz; cuando las tropas se mueven, deben parecer inactivas. Cuando estás cerca del enemigo, debes hacerle creer que estás lejos; cuando estás lejos, debes hacerle creer que estás cerca. Pon cebos para atraer al enemigo. Simula desorden y aplástalo. Si el enemigo tiene buenas defensas, prepárate para la batalla. Si tiene una fuerza superior, evítala. Si tu oponente es iracundo, intenta irritarlo. Si es arrogante, trata de animar su vanidad. Si está en reposo, hazlo trabajar. Si su unidad es armoniosa, divídela. Ataca donde el enemigo no está preparado; aparece donde no te esperan. Estas son las claves de la victoria para el estratega."
            },
            {
                "titulo": "Meditaciones",
                "autor": "Marco Aurelio",
                "texto": "No te afanes por las cosas exteriores. Ocúpate de ti mismo. Los hombres existen los unos para los otros; instruye, pues, o soporta. El hombre está hecho para la virtud. La felicidad de tu vida depende de la calidad de tus pensamientos. No malgastes lo que te queda de vida en cavilaciones sobre otros, a menos que sea en bien común. A cada cual sucede lo que le conviene. Recuerda siempre que el hombre vive solo el presente, este instante. Todo lo demás es pasado o incierto. Breve es la vida, y en este único instante de vida reside tu facultad de elegir entre la virtud y la maldad. La razón es la única guía que puede llevarte a la vida buena."
            },
            {
                "titulo": "Así habló Zaratustra",
                "autor": "Friedrich Nietzsche",
                "texto": "Cuando Zaratustra tuvo treinta años, abandonó su patria y el lago de su patria y se fue a la montaña. Allí disfrutó de su espíritu y de su soledad, y no se cansó de ello durante diez años. Pero al fin su corazón se transformó, y una mañana, al levantarse con la aurora, se puso delante del sol y le habló así: ¡Gran astro! ¿Qué sería de tu felicidad si no tuvieras aquellos a quienes iluminas? Durante diez años has subido aquí a mi cueva: te habrías hastiado de tu luz y de este camino, de no ser por mí, por mi águila y mi serpiente. Pero nosotros te esperamos cada mañana, te recibimos tu sobreabundancia y te bendecimos por ella."
            }
        ]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(ejemplo_base, f, ensure_ascii=False, indent=4)
        st.warning(f"Se ha creado un archivo '{path}' de ejemplo. Por favor, edítalo con tus propios textos.")

    try:
        with open(path, "r", encoding="utf-8") as f:
            base = json.load(f)
        return base
    except FileNotFoundError:
        st.error(f"Error: No se encontró el archivo {path}. Asegúrate de que existe o edita la función 'cargar_base'.")
        st.stop()
    except json.JSONDecodeError as e:
        st.error(f"Error al decodificar JSON en {path}: {e}. Verifica la sintaxis del archivo.")
        st.stop()

def calcular_tokens_aproximados(texto):
    """Calcula una aproximación de tokens basada en caracteres (1 token ≈ 4 caracteres en español)."""
    return int(len(texto) / 4)

def obtener_texto_optimizado(libro, limite_tokens=80000):
    """Obtiene el máximo texto posible del libro sin exceder el límite de tokens."""
    texto_completo = libro["texto"]
    tokens_completos = calcular_tokens_aproximados(texto_completo)

    if tokens_completos <= limite_tokens:
        return texto_completo
    
    ratio_permitido = limite_tokens / tokens_completos
    caracteres_permitidos = int(len(texto_completo) * ratio_permitido)
    
    texto_cortado = texto_completo[:caracteres_permitidos]
    
    # Cortar en un punto lógico (final de párrafo o frase)
    ultimo_punto = texto_cortado.rfind('.')
    ultimo_parrafo = texto_cortado.rfind('\n\n')
    
    punto_corte = max(ultimo_punto, ultimo_parrafo)
    
    if punto_corte > caracteres_permitidos * 0.8: # Si el corte está cerca del final
        texto_final = texto_cortado[:punto_corte + 1]
    else:
        texto_final = texto_cortado
            
    return texto_final

def construir_prompt_anecdota(pregunta, libro_texto, story_length=3):
    """Construye el prompt para generar una anécdota/fábula breve."""
    
    # Calcular el rango de frases basado en la longitud seleccionada
    min_frases = 5 + (story_length - 1) * 1  # De 5 a 14 frases mínimo
    max_frases = 7 + (story_length - 1) * 1  # De 7 a 16 frases máximo
    
    prompt = f"""
Eres un sabio narrador. El usuario te hará una pregunta personal, existencial o filosófica, te planteará un escenario o te pedirá consejo.
Debes responder con una anécdota, un cuento corto o una fábula muy breve, inspirada en el siguiente texto de referencia.
La historia debe ser concisa, evocadora y responder indirectamente a la pregunta, dejando espacio para la interpretación del usuario.
No menciones explícitamente el texto de referencia ni la fuente.

--- TEXTO DE REFERENCIA ---
{libro_texto}
--- FIN DEL TEXTO DE REFERENCIA ---

--- PREGUNTA DEL USUARIO ---
{pregunta}
--- FIN DE LA PREGUNTA ---

Por favor, crea una anécdota, cuento o fábula breve (entre {min_frases} y {max_frases} frases) que explore la pregunta del usuario a través de la esencia del texto de referencia.
Finalmente, cita un fragmento del texto de referencia con la enseñanza de la historia, y su localización en el texto, junto a un resumen de una frase de longitud sobre su contenido. Ejemplo: "Inspirado en: [Título del libro], [sección, cuento, versiculo, o capitulo]- '[RESUMEN EN UNA FRASE DEL CONTENIDO]'."
"""
    return prompt

def calcular_max_tokens_por_longitud(story_length):
    """Calcula los tokens máximos basado en la longitud de historia seleccionada."""
    # Longitud 1 (5-7 frases) ≈ 400-600 tokens
    # Longitud 10 (15-17 frases) ≈ 1200-1700 tokens
    base_tokens = 400
    tokens_por_nivel = 150
    return base_tokens + (story_length - 1) * tokens_por_nivel

# --- UI Principal ---
# Header con logo al estilo Gemini
col1, col2, col3 = st.columns([1, 0.4, 1])
with col2:
    # Logo centrado con alta calidad
    st.image(".streamlit/logo2.png", use_container_width=False)
    
    # Título con clase CSS personalizada
    #st.markdown('<h1 class="main-header">AIfil</h1>', unsafe_allow_html=True)
    #st.markdown('<p class="subtitle">Powered by Gemini AI</p>', unsafe_allow_html=True)
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    st.image(".streamlit/UWU.png", use_container_width=False)

st.markdown('##')


#st.markdown("**💬 Escribe tu pregunta existencial y descubre una historia que te inspire...**")

# Inicializar el historial de chat si no existe
if "messages" not in st.session_state:
    st.session_state.messages = []

# Cargar la base de textos
try:
    base_textos = cargar_base()
except Exception:
    st.stop()

libros_disponibles = {libro["titulo"]: libro for libro in base_textos}
nombres_libros = list(libros_disponibles.keys())



# Sidebar mejorada
with st.sidebar:

    col1, col2, col3 = st.sidebar.columns([1, 1, 1])
    with col2:
    # Logo centrado con alta calidad
        st.image(".streamlit/logo2.png", use_container_width=False)

    col1, col2, col3 = st.sidebar.columns([1, 3, 1])
    with col2:
    # Logo centrado con alta calidad
        st.image(".streamlit/UWU.png", use_container_width=False)
    
    st.sidebar.markdown('###')

    # Desplegables con información
    with st.expander("¿Qué es AIfil?", expanded=False):
        st.markdown("""
        **AIfil** es una herramienta que utiliza la inteligencia artificial de Gemini para generar historias breves y evocadoras basadas en textos clásicos de sabiduría universal.

        AIfil combina la profundidad de los grandes textos filosóficos con la capacidad narrativa de la IA moderna.
        """)

    with st.expander("¿Cómo usar AIfil?", expanded=False):
        st.markdown("""
        1. **Selecciona una fuente**: Elige un libro que te inspire
        2. **Haz tu pregunta**: Escribe una pregunta existencial o filosófica
        3. **Ajusta los parámetros**: Configura la temperatura y los tokens según tu preferencia
        4. **Genera la historia**: Haz clic en enviar y espera la respuesta
        
        💡 **Tip**: Las mejores historias surgen de preguntas profundas y reflexivas.
        """)
    
    
    
    st.markdown("### Ajustes")

    # Forzar visibilidad con título prominent
    selected_book_name = st.selectbox(
        "Fuente:",
        nombres_libros,
        index=0,
        help="Selecciona el texto que inspirará las historias generadas"
    )
    
    
    temperature = st.slider(
        "Temperatura (Creatividad):",
        min_value=0.0,
        max_value=1.0,
        value=0.7,
        step=0.05,
        help="Controla la aleatoriedad de la respuesta. Valores más altos generan textos más creativos."
    )
    
    story_length = st.slider(
        "Longitud de la Historia:",
        min_value=1,
        max_value=10,
        value=1,
        step=1,
        help="Controla la longitud de la historia. 1 = muy breve (5-7 frases), 10 = más extensa (15-17 frases)."
    )

    # Información del estado de las claves API
    with st.expander("Estado de claves API", expanded=False):
        status = api_rotator.get_status_summary()
        st.markdown(f"**Claves disponibles:** {status['available_keys']}/{status['total_keys']}")
        
    


selected_book = libros_disponibles[selected_book_name]
optimized_book_text = obtener_texto_optimizado(selected_book)

# Mostrar mensajes previos del chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Entrada del chat
if prompt := st.chat_input("Haz tu pregunta..."):
    # Añadir pregunta del usuario al historial
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generar respuesta de Gemini
    with st.chat_message("assistant", avatar=".streamlit/logo2.png"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            gemini_prompt = construir_prompt_anecdota(prompt, optimized_book_text, story_length)
            max_output_tokens = calcular_max_tokens_por_longitud(story_length)
            
            generation_config = {
                'temperature': temperature,
                'max_output_tokens': max_output_tokens,
            }
            
            with st.spinner("🌟 Creando tu historia..."):
                # Usar el rotador de claves para generar contenido con reintentos automáticos y timeout
                response = api_rotator.generate_content_with_retry(
                    model_name='gemini-2.0-flash',
                    prompt=gemini_prompt,
                    generation_config=generation_config,
                    max_retries=2,
                    timeout_seconds=10
                )

            full_response = response.text
            message_placeholder.markdown(full_response)
            
            # Añadir respuesta de Gemini al historial
            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            error_str = str(e).lower()
            
            if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
                error_message = "⏳ **Límite de velocidad alcanzado**\n\nSe están rotando las claves API automáticamente. Por favor, intenta de nuevo en unos momentos."
                st.warning(error_message)
            elif "timeout" in error_str or "se agotaron todos los reintentos" in error_str:
                error_message = "⏰ **Tiempo de espera agotado**\n\nEl sistema probó múltiples claves pero todas tardaron demasiado. Por favor, intenta de nuevo."
                st.warning(error_message)
            elif "api key" in error_str:
                error_message = "🔑 **Error de clave API**\n\nTodas las claves API están temporalmente bloqueadas. Por favor, intenta más tarde."
                st.error(error_message)
            else:
                error_message = f"❌ **Error inesperado**\n\n{str(e)}"
                st.error(error_message)
            
            st.session_state.messages.append({"role": "assistant", "content": error_message})


