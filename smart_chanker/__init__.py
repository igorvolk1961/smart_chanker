"""
Smart Chanker - модуль для обработки текстовых файлов
"""

from .smart_chanker import SmartChanker
from .hierarchy_parser import HierarchyParser, SectionNode, FlatList, ChunkMetadata
from .semantic_chunker import SemanticChunker, Chunk
from .hierarchical_chunker import HierarchicalChunker

__version__ = "1.0.0"
__all__ = [
    "SmartChanker", 
    "HierarchyParser", 
    "SectionNode", 
    "FlatList", 
    "ChunkMetadata",
    "SemanticChunker", 
    "Chunk",
    "HierarchicalChunker"
]
