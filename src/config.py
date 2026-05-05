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


def get_settings() -> Settings:
    """Devuelve un Settings cacheado por proceso.

    Returns:
        Instancia única de Settings cargada desde .env.
    """
    return Settings()
