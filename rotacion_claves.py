"""
Sistema de rotación de claves API para Gemini
Maneja múltiples claves API y rota automáticamente cuando se encuentra un error 429
"""

import google.generativeai as genai
import logging
from dataclasses import dataclass
from typing import List, Optional
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, TimeoutError

@dataclass
class APIKeyInfo:
    """Información de una clave API"""
    key: str
    name: str
    last_used: float = 0.0
    failed_count: int = 0
    is_blocked: bool = False
    block_until: float = 0.0

class GeminiAPIRotator:
    """Gestor de rotación de claves API para Gemini"""
    
    def __init__(self):
        """Inicializa el rotador con las claves disponibles"""
        self.api_keys = [
            APIKeyInfo("AIzaSyBVhWdlUeqXlxvf9Nldq-OId9Awoy4n1X4", "mikel_main"),
            APIKeyInfo("AIzaSyBkpLD0fw-zFodOhRGnkF4bzQBYOzFu8d0", "mikel_2"),
            APIKeyInfo("AIzaSyAj0ppjyHkzmln9GQyPq6vRPGrncD9g3tE", "mikel_3"),
            APIKeyInfo("AIzaSyCiOU_-G44UGRJp4QP9trrXsWBO0GlTXPQ", "mikel_4"),
            APIKeyInfo("AIzaSyBT3yn5B42JT28fqKkA-kgDgVOfgJ3IOmM", "frank_1"),
            APIKeyInfo("AIzaSyBul84D3oblaj09308kOa-Ptb1Rh9XKHJo", "frank_2"),
        ]
        self.current_key_index = 0
        self.logger = logging.getLogger(__name__)
        
        # Configurar la primera clave
        self._configure_current_key()
    
    def _configure_current_key(self):
        """Configura Gemini con la clave actual"""
        current_key = self.api_keys[self.current_key_index]
        genai.configure(api_key=current_key.key)
        current_key.last_used = time.time()
        self.logger.info(f"Configurada clave API: {current_key.name}")
    
    def _get_next_available_key(self) -> Optional[int]:
        """Encuentra la siguiente clave disponible"""
        current_time = time.time()
        
        # Primero, desbloquear claves que han pasado su tiempo de bloqueo
        for key_info in self.api_keys:
            if key_info.is_blocked and current_time > key_info.block_until:
                key_info.is_blocked = False
                key_info.failed_count = 0
                self.logger.info(f"Clave {key_info.name} desbloqueada")
        
        # Buscar una clave no bloqueada
        available_keys = [i for i, key in enumerate(self.api_keys) if not key.is_blocked]
        
        if not available_keys:
            return None
        
        # Seleccionar la clave que hace más tiempo que no se usa
        best_key_index = min(available_keys, key=lambda i: self.api_keys[i].last_used)
        return best_key_index
    
    def _block_current_key(self, duration_minutes: int = 60, reason: str = "error 429"):
        """Bloquea la clave actual por un tiempo determinado"""
        current_key = self.api_keys[self.current_key_index]
        current_key.is_blocked = True
        current_key.block_until = time.time() + (duration_minutes * 60)
        current_key.failed_count += 1
        
        self.logger.warning(f"Clave {current_key.name} bloqueada por {duration_minutes} minutos debido a {reason}")
    
    def _rotate_key_silently(self) -> bool:
        """Rota a la siguiente clave disponible sin bloquear la actual (para timeouts)"""
        next_key_index = self._get_next_available_key()
        
        if next_key_index is None:
            self.logger.error("No hay claves API disponibles. Todas están bloqueadas.")
            return False
        
        # Solo cambiar clave sin bloquear la actual (útil para timeouts)
        if next_key_index != self.current_key_index:
            self.current_key_index = next_key_index
            self._configure_current_key()
            return True
        
        return False
    
    def _generate_content_single_attempt(self, model_name: str, prompt: str, generation_config: dict):
        """Intenta generar contenido una sola vez"""
        model = genai.GenerativeModel(model_name)
        return model.generate_content(prompt, generation_config=generation_config)
    
    def _try_generate_with_timeout(self, model_name: str, prompt: str, generation_config: dict, timeout_seconds: int = 30):
        """Intenta generar contenido con timeout usando ThreadPoolExecutor"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._generate_content_single_attempt, model_name, prompt, generation_config)
            try:
                # Esperar por la respuesta con timeout
                response = future.result(timeout=timeout_seconds)
                return response, False  # respuesta, timeout_occurred
            except TimeoutError:
                # Cancelar la tarea pendiente
                future.cancel()
                return None, True  # respuesta, timeout_occurred
    
    def rotate_key(self) -> bool:
        """Rota a la siguiente clave disponible"""
        next_key_index = self._get_next_available_key()
        
        if next_key_index is None:
            self.logger.error("No hay claves API disponibles. Todas están bloqueadas.")
            return False
        
        # Bloquear la clave actual si falló
        if next_key_index != self.current_key_index:
            self._block_current_key()
        
        # Cambiar a la nueva clave
        self.current_key_index = next_key_index
        self._configure_current_key()
        
        return True
    
    def generate_content_with_retry(self, model_name: str, prompt: str, generation_config: dict, max_retries: int = 3, timeout_seconds: int = 30):
        """
        Genera contenido con reintentos automáticos, rotación de claves y timeout
        
        Args:
            model_name: Nombre del modelo (ej: 'gemini-2.0-flash')
            prompt: El prompt para generar
            generation_config: Configuración de generación
            max_retries: Número máximo de reintentos
            timeout_seconds: Timeout en segundos para cada intento
        
        Returns:
            Respuesta del modelo o lanza excepción si fallan todos los intentos
        """
        
        for attempt in range(max_retries + 1):
            current_key = self.api_keys[self.current_key_index]
            
            try:
                # Intentar generar contenido con timeout
                response, timeout_occurred = self._try_generate_with_timeout(
                    model_name, prompt, generation_config, timeout_seconds
                )
                
                if timeout_occurred:
                    # Timeout: rotar clave silenciosamente sin bloquear
                    self.logger.info(f"Timeout de {timeout_seconds}s con clave {current_key.name}. Rotando...")
                    
                    if attempt < max_retries:
                        if self._rotate_key_silently():
                            continue  # Probar con la siguiente clave
                        else:
                            break  # No hay más claves disponibles
                    else:
                        # Último intento falló por timeout
                        break
                
                else:
                    # Generación exitosa
                    self.logger.info(f"Contenido generado exitosamente con clave: {current_key.name}")
                    return response
                
            except Exception as e:
                error_str = str(e).lower()
                
                # Verificar si es un error 429 (rate limit)
                if "429" in error_str or "quota" in error_str or "rate limit" in error_str:
                    self.logger.warning(f"Error 429 con clave {current_key.name}. Intento {attempt + 1}/{max_retries + 1}")
                    
                    if attempt < max_retries:
                        # Intentar rotar clave (bloqueando la actual)
                        if self.rotate_key():
                            time.sleep(random.uniform(1, 3))  # Pausa antes del siguiente intento
                            continue
                        else:
                            self.logger.error("No se pudo rotar a otra clave API")
                            break
                    else:
                        self.logger.error(f"Agotados todos los reintentos. Último error: {e}")
                        raise e
                
                else:
                    # Para otros errores, no rotar clave, solo propagar el error
                    self.logger.error(f"Error no relacionado con límites: {e}")
                    raise e
        
        # Si llegamos aquí, significa que agotamos todos los reintentos
        raise RuntimeError("Se agotaron todos los reintentos y claves API disponibles")
    
    def get_current_key_info(self) -> APIKeyInfo:
        """Retorna información sobre la clave actual"""
        return self.api_keys[self.current_key_index]
    
    def get_status_summary(self) -> dict:
        """Retorna un resumen del estado de todas las claves"""
        current_time = time.time()
        summary = {
            "current_key": self.api_keys[self.current_key_index].name,
            "total_keys": len(self.api_keys),
            "blocked_keys": sum(1 for key in self.api_keys if key.is_blocked),
            "available_keys": sum(1 for key in self.api_keys if not key.is_blocked),
            "keys_status": []
        }
        
        for key in self.api_keys:
            key_status = {
                "name": key.name,
                "is_blocked": key.is_blocked,
                "failed_count": key.failed_count,
                "minutes_until_unblock": max(0, int((key.block_until - current_time) / 60)) if key.is_blocked else 0
            }
            summary["keys_status"].append(key_status)
        
        return summary

# Instancia global del rotador
api_rotator = GeminiAPIRotator()

def get_api_rotator() -> GeminiAPIRotator:
    """Retorna la instancia global del rotador de APIs"""
    return api_rotator
