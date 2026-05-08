"""Configuración global del agente.

Carga variables desde .env vía pydantic-settings y las expone tipadas.
"""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings del agente GobIA Auditor.

    Attributes:
        anthropic_api_key: Clave de Anthropic para Claude Opus 4.7 (modelo
            principal del LLM Router).
        ollama_base_url: URL base de Ollama local (modelo fallback).
        qdrant_url: URL del servicio Qdrant (memory store vectorial).
        postgres_url: URL de Postgres para metadatos y trazabilidad.
        secop_api_base: Endpoint Socrata público de SECOP II en datos.gov.co.
            No debe modificarse: la auditabilidad depende de mantener la
            fuente fija.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    anthropic_api_key: str = Field(default="", description="API key de Anthropic")
    ollama_base_url: str = Field(default="http://localhost:11434")
    qdrant_url: str = Field(default="http://localhost:6333")
    postgres_url: str = Field(
        default="postgresql://gobia:gobia@localhost:5432/gobia"
    )
    secop_api_base: str = Field(
        default="https://www.datos.gov.co/resource/jbjy-vk9h.json"
    )
    offline_mode: bool = Field(
        default=False,
        description=(
            "Si True (env OFFLINE_MODE=1), el llm_router NO consulta "
            "Anthropic y va directo a Ollama local. Útil para demo D2 "
            "del jurado y para entornos sin acceso a API externas."
        ),
    )
    ollama_model: str = Field(
        default="qwen3:1.7b",
        description=(
            "Modelo Ollama del fallback offline (ADR-010). Default "
            "endurecido para T495 sin GPU. Override con env "
            "OLLAMA_MODEL=qwen3:8b si hay GPU."
        ),
    )
    ollama_keep_alive: str = Field(
        default="30m",
        description=(
            "TTL del modelo cargado en memoria (ADR-010). Mantiene "
            "caliente entre demos. Override OLLAMA_KEEP_ALIVE=-1 "
            "para tener el modelo siempre cargado."
        ),
    )
    ollama_think: bool = Field(
        default=False,
        description=(
            "Modo thinking de qwen3 (ADR-010). OFF por default: "
            "para scoring [0,1] el reasoning explícito agrega "
            "latencia sin aportar calidad. Override "
            "OLLAMA_THINK=1 para tareas complejas."
        ),
    )
    ollama_num_predict: int = Field(
        default=120,
        description=(
            "Tope de tokens en la respuesta Ollama (ADR-010). "
            "Override OLLAMA_NUM_PREDICT=512 si el prompt requiere "
            "rationale extendida."
        ),
    )
    ollama_temperature: float = Field(
        default=0.3,
        description=(
            "Temperatura del fallback Ollama (ADR-010). 0.3 evita "
            "repetition-loops del 1.7B; bajar a 0.0 si el modelo "
            "primario es más grande y determinístico."
        ),
    )


def get_settings() -> Settings:
    """Devuelve un Settings cacheado por proceso.

    Returns:
        Instancia única de Settings cargada desde .env.
    """
    return Settings()
