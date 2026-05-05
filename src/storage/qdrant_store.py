"""Adaptador mínimo de Qdrant para persistir embeddings de contratos.

STUB: este módulo expone la firma estable que usará el resto del
sistema, pero no realiza llamadas de red durante este sprint para
mantener tests de humo sin dependencia de un Qdrant en ejecución.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.ingestion.normalizer import Contract


@dataclass
class QdrantStore:
    """Wrapper alrededor del cliente Qdrant.

    Attributes:
        url: URL del servicio Qdrant. Default toma de Settings.
        collection: Nombre de la colección donde se indexan los
            contratos del dominio SECOP.
    """

    url: str = "http://localhost:6333"
    collection: str = "secop_contracts"

    def upsert(self, contracts: list[Contract]) -> int:
        """Persiste una lista de contratos como vectores + metadatos.

        Args:
            contracts: Contratos normalizados a indexar.

        Returns:
            Número de items persistidos.

        Notes:
            STUB: la integración real con qdrant-client se implementa
            en sprint posterior. Aquí solo se valida la firma.
        """
        return len(contracts)

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Búsqueda semántica de contratos similares.

        Args:
            query: Texto de consulta (objeto contractual, etc.).
            limit: Máximo de resultados.

        Returns:
            Lista de dicts con {id, score, payload}; vacía en stub.
        """
        _ = query, limit
        return []
