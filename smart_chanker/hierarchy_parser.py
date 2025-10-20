"""
Модуль для парсинга иерархии из плоского текста с многоуровневой нумерацией
"""

import re
import uuid
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class SectionNode:
    """Узел раздела в иерархии документа"""
    number: str
    title: str
    level: int
    content: str
    parent: Optional['SectionNode'] = None
    children: List['SectionNode'] = None
    chunks: List[str] = None  # список ID чанков в разделе
    
    def __post_init__(self):
        if self.children is None:
            self.children = []
        if self.chunks is None:
            self.chunks = []


@dataclass
class FlatList:
    """Плоский список внутри раздела"""
    items: List[str]
    list_type: str  # 'numbered', 'bulleted', 'lettered'
    prefix_paragraph: Optional[str] = None  # абзац с двоеточием перед списком


@dataclass
class ChunkMetadata:
    """Метаданные чанка"""
    chunk_id: str
    chunk_number: int  # порядковый номер чанка в разделе
    section_path: List[str]
    parent_section: str
    section_level: int
    children: List[str]
    word_count: int
    char_count: int
    contains_lists: bool
    is_complete_section: bool


class HierarchyParser:
    """Парсер иерархии из плоского текста"""
    
    def __init__(self):
        """Инициализация парсера"""
        self.patterns = self._init_patterns()
        self.sections = []
        self.flat_lists = []
    
    def _init_patterns(self) -> Dict[str, re.Pattern]:
        """Инициализация регулярных выражений"""
        return {
            'simple_numbered': re.compile(r'^\s*(?:Раздел|Пункт|Часть)?\s*(\d+)\)\.?\s*'),
            'multi_level': re.compile(r'^\s*(?:Раздел|Пункт|Часть)?\s*(\d+(?:\.\d+)*)\.?\s*'),
            'lettered': re.compile(r'^\s*(?:Раздел|Пункт|Часть)?\s*([a-zа-я])\.?\s*'),
            'bulleted': re.compile(r'^\s*([•\-*])\s*')
        }
    
    def parse_hierarchy(self, text: str) -> List[SectionNode]:
        """
        Парсит иерархию из плоского текста
        
        Args:
            text: Плоский текст с нумерацией
            
        Returns:
            Плоский список всех разделов с установленными parent связями
        """
        lines = text.split('\n')
        self.sections = []
        self.flat_lists = []
        
        # Стек для отслеживания текущего уровня иерархии
        hierarchy_stack = []
        current_flat_list = None
        last_section = None  # Последний созданный раздел
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            element_type, number = self._classify_element(line)
            
            if element_type == 'multi_level':
                # Завершаем текущий плоский список
                if current_flat_list:
                    self._finalize_flat_list(current_flat_list)
                    current_flat_list = None
                
                # Создаем новый раздел
                new_section = self._create_section(line, number)
                
                # Определяем уровень вложенности
                level = new_section.level
                
                # Убираем из стека разделы с уровнем >= текущего
                while hierarchy_stack and hierarchy_stack[-1].level >= level:
                    hierarchy_stack.pop()
                
                # Устанавливаем родителя
                if hierarchy_stack:
                    parent = hierarchy_stack[-1]
                    new_section.parent = parent
                    parent.children.append(new_section)
                
                # Добавляем в общий список
                self.sections.append(new_section)
                
                # Добавляем в стек
                hierarchy_stack.append(new_section)
                
                # Запоминаем последний созданный раздел
                last_section = new_section
                
            elif element_type in ['simple_numbered', 'lettered', 'bulleted']:
                # Плоские списки добавляются к текущему разделу, если он есть
                if hierarchy_stack:
                    # Добавляем к текущему разделу
                    current_section = hierarchy_stack[-1]
                    current_section.content += f"\n{line}"
                elif last_section:
                    # Если стек пустой, но есть последний раздел, добавляем к нему
                    last_section.content += f"\n{line}"
                else:
                    # Если мы на верхнем уровне и нет последнего раздела, создаем раздел для списка
                    if current_flat_list and current_flat_list.list_type == element_type:
                        current_flat_list.items.append(line)
                    else:
                        # Завершаем предыдущий список
                        if current_flat_list:
                            self._finalize_flat_list(current_flat_list)
                        
                        # Создаем новый список
                        current_flat_list = self._create_flat_list(line, element_type)
                    
            else:  # paragraph
                # Завершаем текущий список
                if current_flat_list:
                    self._finalize_flat_list(current_flat_list)
                    current_flat_list = None
                
                # Добавляем к текущему разделу
                if hierarchy_stack:
                    current_section = hierarchy_stack[-1]
                    current_section.content += f"\n{line}"
                else:
                    # Создаем корневой раздел для абзаца без нумерации
                    current_section = SectionNode(
                        number="0",
                        title=line[:50] + "..." if len(line) > 50 else line,
                        level=0,
                        content=line
                    )
                    self.sections.append(current_section)
        
        # Завершаем последний список
        if current_flat_list:
            self._finalize_flat_list(current_flat_list)
        
        return self.sections
    
    def _classify_element(self, text: str) -> Tuple[str, Optional[str]]:
        """
        Классифицирует элемент текста по типу нумерации
        
        Args:
            text: Строка для анализа
            
        Returns:
            Кортеж (тип_элемента, номер)
        """
        for pattern_name, pattern in self.patterns.items():
            match = pattern.match(text)
            if match and self._is_likely_numbering(text, match):
                number = match.group(1)
                return pattern_name, number
        
        return 'paragraph', None
    
    def _is_likely_numbering(self, text: str, match: re.Match) -> bool:
        """
        Определяет, является ли найденный паттерн нумерацией
        
        Args:
            text: Исходный текст
            match: Результат совпадения регулярного выражения
            
        Returns:
            True если это нумерация, False иначе
        """
        number = match.group(1)
        
        # Исключаем годы (19xx, 20xx)
        if re.match(r'^(19|20)\d{2}$', number):
            return False
        
        # Исключаем даты (dd.mm.yy, dd.mm.yyyy)
        if re.match(r'^\d{1,2}\.\d{1,2}\.(\d{2}|\d{4})$', number):
            return False
        
        return True
    
    
    def _create_section(self, line: str, number: str) -> SectionNode:
        """
        Создает узел раздела
        
        Args:
            line: Строка с нумерацией
            number: Номер раздела
            
        Returns:
            Узел раздела
        """
        # Извлекаем заголовок (убираем номер)
        title = self._extract_title(line, number)
        
        # Определяем уровень по количеству точек в номере
        level = number.count('.') + 1
        
        return SectionNode(
            number=number,
            title=title,
            level=level,
            content=title
        )
    
    def _extract_title(self, line: str, number: str) -> str:
        """
        Извлекает заголовок из строки с нумерацией
        
        Args:
            line: Исходная строка
            number: Номер раздела
            
        Returns:
            Заголовок раздела
        """
        # Убираем номер
        title = re.sub(r'^\s*\d+(?:\.\d+)*\.?\s*', '', line)
        
        return title.strip()
    
    def _create_flat_list(self, line: str, list_type: str) -> FlatList:
        """
        Создает плоский список
        
        Args:
            line: Первая строка списка
            list_type: Тип списка
            
        Returns:
            Объект плоского списка
        """
        return FlatList(
            items=[line],
            list_type=list_type,
            prefix_paragraph=None
        )
    
    def _finalize_flat_list(self, flat_list: FlatList) -> None:
        """
        Завершает обработку плоского списка
        
        Args:
            flat_list: Список для завершения
        """
        if flat_list.items:
            self.flat_lists.append(flat_list)
    
    def get_sections_by_level(self, level: int) -> List[SectionNode]:
        """
        Получает все разделы заданного уровня
        
        Args:
            level: Уровень разделов
            
        Returns:
            Список разделов заданного уровня
        """
        return [section for section in self.sections if section.level == level]
