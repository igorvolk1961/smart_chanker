"""
Модуль для интегрированного иерархического чанкинга
"""

import json
from typing import List, Dict, Any, Optional
from .hierarchy_parser import HierarchyParser, SectionNode
from .semantic_chunker import SemanticChunker, Chunk


class HierarchicalChunker:
    """Интегрированный иерархический чанкер"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Инициализация чанкера
        
        Args:
            config: Конфигурация чанкера
        """
        self.config = config or self._get_default_config()
        self.parser = HierarchyParser()
        self.chunker = SemanticChunker(
            max_chunk_size=self.config.get('max_chunk_size', 1000),
            preserve_lists=self.config.get('preserve_lists', True)
        )
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Получает конфигурацию по умолчанию"""
        return {
            'target_level': 3,
            'max_chunk_size': 1000,
            'preserve_lists': True,
            'include_parent_context': True
        }
    
    def process_text(self, text: str) -> Dict[str, Any]:
        """
        Обрабатывает текст и создает семантические чанки
        
        Args:
            text: Плоский текст с нумерацией
            
        Returns:
            Результат обработки с чанками и метаданными
        """
        # Парсим иерархию
        sections = self.parser.parse_hierarchy(text)
        
        # Генерируем чанки
        chunks = self.chunker.generate_chunks(
            sections, 
            target_level=self.config.get('target_level', 3)
        )
        
        # Создаем результат
        result = {
            'sections': self._serialize_sections(sections),
            'chunks': self._serialize_chunks(chunks),
            'metadata': {
                'total_sections': len(sections),
                'total_chunks': len(chunks),
                'target_level': self.config.get('target_level', 3),
                'max_chunk_size': self.config.get('max_chunk_size', 1000)
            }
        }
        
        return result
    
    def _serialize_sections(self, sections: List[SectionNode]) -> List[Dict[str, Any]]:
        """
        Сериализует разделы в словари
        
        Args:
            sections: Список разделов
            
        Returns:
            Список словарей с данными разделов
        """
        result = []
        for section in sections:
            result.append(self._serialize_section(section))
        return result
    
    def _serialize_section(self, section: SectionNode) -> Dict[str, Any]:
        """
        Сериализует один раздел в словарь
        
        Args:
            section: Раздел для сериализации
            
        Returns:
            Словарь с данными раздела
        """
        return {
            'number': section.number,
            'title': section.title,
            'level': section.level,
            'content': section.content,
            'parent_number': section.parent.number if section.parent else None,
            'children': [child.number for child in section.children],
            'chunks': section.chunks
        }
    
    def _serialize_chunks(self, chunks: List[Chunk]) -> List[Dict[str, Any]]:
        """
        Сериализует чанки в словари
        
        Args:
            chunks: Список чанков
            
        Returns:
            Список словарей с данными чанков
        """
        result = []
        for chunk in chunks:
            result.append(self._serialize_chunk(chunk))
        return result
    
    def _serialize_chunk(self, chunk: Chunk) -> Dict[str, Any]:
        """
        Сериализует один чанк в словарь
        
        Args:
            chunk: Чанк для сериализации
            
        Returns:
            Словарь с данными чанка
        """
        return {
            'content': chunk.content,
            'metadata': {
                'chunk_id': chunk.metadata.chunk_id,
                'chunk_number': chunk.metadata.chunk_number,
                'section_path': chunk.metadata.section_path,
                'parent_section': chunk.metadata.parent_section,
                'section_level': chunk.metadata.section_level,
                'children': chunk.metadata.children,
                'word_count': chunk.metadata.word_count,
                'char_count': chunk.metadata.char_count,
                'contains_lists': chunk.metadata.contains_lists,
                'is_complete_section': chunk.metadata.is_complete_section
            }
        }
    
    def get_chunks_by_level(self, text: str, level: int) -> List[Chunk]:
        """
        Получает чанки для конкретного уровня иерархии
        
        Args:
            text: Плоский текст с нумерацией
            level: Уровень иерархии
            
        Returns:
            Список чанков для заданного уровня
        """
        sections = self.parser.parse_hierarchy(text)
        return self.chunker.generate_chunks(sections, target_level=level)
    
    def get_section_context(self, text: str, section_number: str) -> Dict[str, Any]:
        """
        Получает контекст раздела (родитель + дочерние разделы)
        
        Args:
            text: Плоский текст с нумерацией
            section_number: Номер раздела
            
        Returns:
            Контекст раздела
        """
        sections = self.parser.parse_hierarchy(text)
        target_section = self._find_section_by_number(sections, section_number)
        
        if not target_section:
            return {'error': f'Section {section_number} not found'}
        
        context = {
            'section': self._serialize_section(target_section),
            'parent': self._serialize_section(target_section.parent) if target_section.parent else None,
            'children': [self._serialize_section(child) for child in target_section.children],
            'siblings': self._get_sibling_sections(target_section)
        }
        
        return context
    
    def _find_section_by_number(self, sections: List[SectionNode], 
                               number: str) -> Optional[SectionNode]:
        """
        Находит раздел по номеру
        
        Args:
            sections: Список разделов для поиска
            number: Номер раздела
            
        Returns:
            Найденный раздел или None
        """
        for section in sections:
            if section.number == number:
                return section
            
            # Рекурсивно ищем в дочерних разделах
            found = self._find_section_by_number(section.children, number)
            if found:
                return found
        
        return None
    
    def _get_sibling_sections(self, section: SectionNode) -> List[Dict[str, Any]]:
        """
        Получает соседние разделы
        
        Args:
            section: Раздел для поиска соседей
            
        Returns:
            Список соседних разделов
        """
        if not section.parent:
            return []
        
        siblings = []
        for child in section.parent.children:
            if child.number != section.number:
                siblings.append(self._serialize_section(child))
        
        return siblings
    
    def save_result(self, result: Dict[str, Any], output_path: str) -> None:
        """
        Сохраняет результат в JSON файл
        
        Args:
            result: Результат обработки
            output_path: Путь для сохранения
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    
    def load_result(self, input_path: str) -> Dict[str, Any]:
        """
        Загружает результат из JSON файла
        
        Args:
            input_path: Путь к файлу
            
        Returns:
            Загруженный результат
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            return json.load(f)
