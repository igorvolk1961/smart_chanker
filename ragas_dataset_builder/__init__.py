"""
RAGAS Dataset Builder - Генерация синтетических наборов данных для оценки RAG систем
"""

from dataset_builder import RagasDatasetBuilder
from llm_providers import LLMProvider, EmbeddingProvider

__version__ = "0.1.0"
__all__ = ["RagasDatasetBuilder", "LLMProvider", "EmbeddingProvider"]

