"""Adapters de ingestión: SECOP II y datasets Socrata genéricos.

Las reglas estadísticas (HHI, IQR, OP-01..OP-13) son agnósticas al
dominio. Si Día 1 del hackathon trae un dataset distinto (energía,
salud, ambiente), el ``GenericSocrataAdapter`` permite alimentar el
``RuleEngine`` definiendo solo un ``field_mapping`` mínimo.
"""

from src.ingestion.adapters.base import BaseAdapter
from src.ingestion.adapters.generic_socrata import GenericSocrataAdapter
from src.ingestion.adapters.secop import SecopAdapter

__all__ = ["BaseAdapter", "GenericSocrataAdapter", "SecopAdapter"]
