# Sistema de Rotación de Claves API

## Configuración de Claves API

### Archivo secrets.toml

El sistema ahora lee las claves API desde el archivo `.streamlit/secrets.toml`. 

**Estructura requerida:**

```toml
[google]
# Clave principal para autenticación simple
api_key = "TU_CLAVE_PRINCIPAL"

# Configuración de múltiples claves API para rotación
[[google.api_keys]]
key = "CLAVE_API_1"
name = "nombre_descriptivo_1"

[[google.api_keys]]
key = "CLAVE_API_2"
name = "nombre_descriptivo_2"

# ... agregar más claves según necesites
```

### Beneficios del nuevo sistema:

1. **🔒 Seguridad**: Las claves no están hardcodeadas en el código
2. **🔧 Configurabilidad**: Fácil agregar/remover claves sin modificar código  
3. **📊 Identificación**: Cada clave tiene un nombre descriptivo para logging
4. **🔄 Fallback**: Si falla la carga desde secrets, usa claves por defecto como respaldo

### ¿Cómo funciona?

1. Al iniciar, `load_api_keys_from_secrets()` lee el archivo `secrets.toml`
2. Carga todas las claves definidas en `[[google.api_keys]]`
3. Si hay error o no encuentra claves, usa las claves hardcodeadas como fallback
4. El sistema funciona igual: rotación automática, timeouts, logging, etc.

### Logs del sistema:

- ✅ `"Iniciando rotador de claves API con X claves disponibles"`
- ⚠️ `"No se encontraron claves API en secrets.toml, usando claves por defecto"`
- ❌ `"Error cargando claves API desde secrets: [error]"`

### Para agregar nuevas claves:

1. Edita `.streamlit/secrets.toml`
2. Agrega un nuevo bloque `[[google.api_keys]]`
3. Reinicia la aplicación

No necesitas modificar código Python para agregar/remover claves.
