"""
SmartChanker - класс для обработки текстовых файлов
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

# Импорт инструментов обработки
try:
    from docx2python import docx2python
    DOCX2PYTHON_AVAILABLE = True
except ImportError:
    DOCX2PYTHON_AVAILABLE = False
    logging.warning("Пакет docx2python не установлен")

from zipfile import ZipFile
from lxml import etree

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": WORD_NAMESPACE}

# Импорт внутренних модулей
from .numbering_restorer import NumberingRestorer
from .table_processor import TableProcessor, ParsedDocxTable, TableExtractionError, TableConversionError


class SmartChanker:
    """
    Класс для обработки текстовых файлов с использованием различных инструментов
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Инициализация SmartChanker
        
        Args:
            config_path: Путь к конфигурационному файлу
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logger()
        self.numbering_restorer = NumberingRestorer(self.logger)
        self.table_processor = TableProcessor()
        
        # Проверка доступности инструментов
        self._check_tools_availability()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Загрузка конфигурации из файла
        
        Returns:
            Словарь с конфигурацией
        """
        default_config = {
            "tools": {
                "unstructured": {
                    "enabled": True,
                    "chunking_strategy": "title",
                    "max_characters": 1000
                },
                "docx2txt": {
                    "enabled": True
                }
            },
            "output": {
                "format": "json",
                "save_path": "./output",
                "save_docx2python_text": False,
                "save_list_positions": False
            },
            "hierarchical_chunking": {
                "enabled": False,
                "target_level": 3,
                "max_chunk_size": 1000,
            },
            "table_processing": {
                "max_chunk_size": 1000,
            }
        }
        
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # Объединяем с конфигурацией по умолчанию
                    default_config.update(user_config)
            except Exception as e:
                self.logger.warning(f"Ошибка загрузки конфигурации: {e}")
        
        return default_config
    
    def _setup_logger(self) -> logging.Logger:
        """
        Настройка логгера
        
        Returns:
            Настроенный логгер
        """
        logger = logging.getLogger('SmartChanker')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        
        return logger
    
    def _check_tools_availability(self):
        """
        Проверка доступности инструментов для комбинированного подхода
        """
        if not DOCX2PYTHON_AVAILABLE:
            self.logger.warning("Пакет docx2python недоступен")
            self.logger.error("Для работы требуется пакет docx2python")
    
    def process_folder(self, folder_path: str) -> Dict[str, Any]:
        """
        Основной цикл обработки файлов в папке
        
        Args:
            folder_path: Путь к папке с файлами для обработки
            
        Returns:
            Словарь с результатами обработки
        """
        if not os.path.exists(folder_path):
            raise ValueError(f"Папка {folder_path} не существует")
        
        self.logger.info(f"Начинаем обработку папки: {folder_path}")
        
        results = {
            "processed_files": [],
            "errors": [],
            "summary": {
                "total_files": 0,
                "successful": 0,
                "failed": 0
            }
        }
        
        # Получаем список файлов для обработки
        files_to_process = self._get_files_to_process(folder_path)
        results["summary"]["total_files"] = len(files_to_process)
        
        # Обрабатываем каждый файл
        for file_path in files_to_process:
            try:
                self.logger.info(f"Обрабатываем файл: {file_path}")
                file_result = self._process_single_file(file_path)
                results["processed_files"].append(file_result)
                results["summary"]["successful"] += 1
                
            except Exception as e:
                error_info = {
                    "file": file_path,
                    "error": str(e)
                }
                results["errors"].append(error_info)
                results["summary"]["failed"] += 1
                self.logger.error(f"Ошибка обработки файла {file_path}: {e}")
        
        self.logger.info(f"Обработка завершена. Успешно: {results['summary']['successful']}, "
                        f"Ошибок: {results['summary']['failed']}")
        
        return results
    
    def _get_files_to_process(self, folder_path: str) -> List[str]:
        """
        Получение списка файлов для обработки (только DOCX/DOC)
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Список путей к файлам
        """
        supported_extensions = ['.docx', '.doc']
        files = []
        
        for root, dirs, filenames in os.walk(folder_path):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                file_ext = Path(file_path).suffix.lower()
                
                if file_ext in supported_extensions:
                    files.append(file_path)
        
        return files
    
    def _process_single_file(self, file_path: str) -> Dict[str, Any]:
        """
        Обработка одного файла с использованием комбинированного подхода
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат обработки файла
        """
        file_ext = Path(file_path).suffix.lower()
        
        # Проверяем поддержку формата
        if file_ext not in ['.docx', '.doc']:
            raise ValueError(f"Неподдерживаемый формат файла: {file_ext}. Поддерживаются только .docx и .doc")
        
        # Используем комбинированный подход
        return self._process_with_combined_approach(file_path)
    
    def _process_with_combined_approach(self, file_path: str) -> Dict[str, Any]:
        """
        Комбинированная обработка файла с использованием двух инструментов: unstructured и docx2python
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат обработки
        """
        if not DOCX2PYTHON_AVAILABLE:
            raise ImportError("Для комбинированного подхода требуется пакет docx2python")
        
        self.logger.info(f"Используем комбинированный подход для файла: {file_path}")
        
        # Обрабатываем с помощью docx2python - получаем текст с восстановлением нумерации
        docx2python_text = self._extract_text_with_docx2python(file_path)
        docx_tables = self.table_processor.extract_docx_tables(file_path)
        
        # Извлекаем информацию о таблицах из DOCX XML
        table_info = self._extract_table_info_from_docx(file_path)
        
        # Удаляем таблицы из текста и получаем информацию о них отдельно
        text_without_tables, tables_data = self._remove_tables_from_text(
            docx2python_text,
            table_info,
            docx_tables,
        )
        
        # Создаем абзацы из текста без таблиц
        combined_paragraphs = [p.strip() for p in text_without_tables.split('\n\n') if p.strip()]
        
        return {
            "file_path": file_path,
            "tool_used": "combined_approach",
            "original_docx2python_text": docx2python_text,
            "combined_text": text_without_tables,
            "paragraphs": combined_paragraphs,
            "paragraphs_count": len(combined_paragraphs),
            "tables_data": tables_data,  # Информация о таблицах с позициями
            "table_replacements_count": len(self._find_table_paragraphs_docx2python(docx2python_text)),
            "docx_tables_count": len(docx_tables),
        }
    
    def _extract_text_with_docx2python(self, file_path: str) -> str:
        """
        Извлекает текст из DOCX файла с помощью docx2python с восстановлением нумерации
        
        Args:
            file_path: путь к DOCX файлу
            
        Returns:
            str: извлеченный текст с восстановленной нумерацией
        """
        if not DOCX2PYTHON_AVAILABLE:
            raise ImportError("Пакет docx2python недоступен")
        
        try:
            doc = docx2python(file_path)
            
            # Извлекаем все параграфы из вложенной структуры
            all_paragraphs = self._extract_all_paragraphs(doc.document_pars)
            
            # Восстанавливаем нумерацию
            restored_text = self.numbering_restorer.restore_numbering_in_paragraphs(all_paragraphs)
            
            doc.close()
            return restored_text
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении текста с docx2python: {e}")
            return ""
    
    def _extract_table_of_contents(self, file_path: str) -> str:
        """
        Извлекает оглавление документа из номеров и заголовков разделов и таблиц
        с использованием восстановленной нумерации
        
        Args:
            file_path: Путь к DOCX файлу
            
        Returns:
            Текст оглавления с восстановленной нумерацией
        """
        if not DOCX2PYTHON_AVAILABLE:
            raise ImportError("Пакет docx2python недоступен")
        
        try:
            doc = docx2python(file_path)
            
            # Извлекаем все параграфы
            all_paragraphs = self._extract_all_paragraphs(doc.document_pars)
            
            # Восстанавливаем нумерацию для всех параграфов
            restored_paragraphs = self.numbering_restorer.restore_numbering_in_paragraphs(all_paragraphs)
            
            # Разбиваем на строки для обработки
            lines = restored_paragraphs.split('\n')
            
            toc_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Проверяем, является ли это заголовком раздела с восстановленной нумерацией
                if self._is_section_header_restored(line):
                    toc_lines.append(line)
                # Проверяем, является ли это таблицей
                elif self._is_table_reference(line):
                    toc_lines.append(line)
            
            doc.close()
            return "\n".join(toc_lines)
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении оглавления: {e}")
            return ""
    
    def _is_section_header(self, text: str) -> bool:
        """
        Проверяет, является ли текст заголовком раздела
        
        Args:
            text: Текст для проверки
            
        Returns:
            True если это заголовок раздела
        """
        import re
        
        # Паттерны для заголовков разделов
        patterns = [
            r'^\s*\d+(?:\.\d+)*\.\s+',  # 1., 1.1., 1.1.1.
            r'^\s*\d+\)\s+',            # 1), 2), 3)
            r'^\s*[IVX]+\.\s+',         # I., II., III.
            r'^\s*[ivx]+\.\s+',         # i., ii., iii.
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_section_header_restored(self, text: str) -> bool:
        """
        Проверяет, является ли текст заголовком раздела с восстановленной нумерацией
        
        Args:
            text: Текст для проверки
            
        Returns:
            True если это заголовок раздела с восстановленной нумерацией
        """
        import re
        
        # Паттерны для заголовков разделов с восстановленной нумерацией
        patterns = [
            r'^\s*\d+(?:\.\d+)*\.\s+',  # 1., 1.1., 1.1.1. (восстановленная нумерация)
            r'^\s*\d+\)\s+',            # 1), 2), 3)
            r'^\s*[IVX]+\.\s+',         # I., II., III.
            r'^\s*[ivx]+\.\s+',         # i., ii., iii.
        ]
        
        for pattern in patterns:
            if re.match(pattern, text):
                return True
        
        return False
    
    def _is_table_reference(self, text: str) -> bool:
        """
        Проверяет, является ли текст ссылкой на таблицу
        
        Args:
            text: Текст для проверки
            
        Returns:
            True если это ссылка на таблицу
        """
        import re
        
        # Паттерны для ссылок на таблицы
        patterns = [
            r'Таблица\s+\d+',
            r'таблица\s+\d+',
            r'ТАБЛИЦА\s+\d+',
            r'Table\s+\d+',
            r'table\s+\d+',
        ]
        
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def _chunk_table_of_contents(self, toc_text: str, max_chunk_size: int) -> List[Dict[str, Any]]:
        """
        Создает чанки из оглавления, не разбивая заголовки между чанками
        
        Args:
            toc_text: Текст оглавления
            max_chunk_size: Максимальный размер чанка
            
        Returns:
            Список чанков оглавления
        """
        import uuid
        
        chunks = []
        lines = [line.strip() for line in toc_text.split('\n') if line.strip()]
        
        current_chunk_lines = []
        current_size = 0
        chunk_number = 1
        
        for line in lines:
            line_size = len(line) + 1  # +1 для символа новой строки
            
            # Если добавление этой строки превысит лимит и у нас уже есть строки
            if current_size + line_size > max_chunk_size and current_chunk_lines:
                # Создаем чанк из накопленных строк
                chunk_content = '\n'.join(current_chunk_lines)
                chunk_id = str(uuid.uuid4())
                
                metadata = {
                    'chunk_id': chunk_id,
                    'chunk_number': chunk_number,
                    'section_path': ['Table of Contents'],
                    'parent_section': 'Root',
                    'section_level': 0,
                    'children': [],
                    'word_count': len(chunk_content.split()),
                    'char_count': len(chunk_content),
                    'contains_lists': False,
                    'table_id': None,
                    'is_complete_section': True,
                    'start_pos': 0,
                    'end_pos': len(chunk_content)
                }
                
                chunks.append({
                    'content': chunk_content,
                    'metadata': metadata
                })
                
                # Начинаем новый чанк
                current_chunk_lines = []
                current_size = 0
                chunk_number += 1
            
            # Добавляем строку к текущему чанку
            current_chunk_lines.append(line)
            current_size += line_size
        
        # Создаем последний чанк, если есть накопленные строки
        if current_chunk_lines:
            chunk_content = '\n'.join(current_chunk_lines)
            chunk_id = str(uuid.uuid4())
            
            metadata = {
                'chunk_id': chunk_id,
                'chunk_number': chunk_number,
                'section_path': ['Table of Contents'],
                'parent_section': 'Root',
                'section_level': 0,
                'children': [],
                'word_count': len(chunk_content.split()),
                'char_count': len(chunk_content),
                'contains_lists': False,
                'table_id': None,
                'is_complete_section': True,
                'start_pos': 0,
                'end_pos': len(chunk_content)
            }
            
            chunks.append({
                'content': chunk_content,
                'metadata': metadata
            })
        
        return chunks
    
    def _extract_all_paragraphs(self, data, level=0):
        """
        Рекурсивно извлекает все объекты Par из вложенной структуры docx2python
        
        Args:
            data: данные из docx2python (может быть списком или объектом Par)
            level: уровень вложенности для отладки
        
        Returns:
            list: список всех найденных объектов Par
        """
        paragraphs = []
        
        if isinstance(data, list):
            for i, item in enumerate(data):
                if hasattr(item, 'runs'):  # Это объект Par
                    paragraphs.append(item)
                else:
                    # Рекурсивно обходим вложенные структуры
                    nested_paragraphs = self._extract_all_paragraphs(item, level + 1)
                    paragraphs.extend(nested_paragraphs)
        elif hasattr(data, 'runs'):  # Это объект Par
            paragraphs.append(data)
        
        return paragraphs
    
    def _restore_numbering_in_paragraphs(self, paragraphs):
        """
        Восстанавливает нумерацию в параграфах с полной иерархией
        
        Args:
            paragraphs: список параграфов из docx2python
        
        Returns:
            str: текст с восстановленной нумерацией
        """
        import re
        
        restored_paragraphs = []
        hierarchy_tracker = {}  # Отслеживаем текущие номера для каждого уровня
        current_section_path: List[int] = []  # Текущая секция из заголовков 1., 1.2., 1.2.3.
        child_counters: Dict[tuple, int] = {}  # Счетчик дочерних заголовков для каждого пути
        last_root: Optional[int] = None       # Последний зафиксированный корневой номер (верхний уровень)
        
        # Стек для отслеживания текущей иерархии
        hierarchy_stack = []
        # Счетчики для каждого уровня
        level_counters = {}
        
        for i, paragraph in enumerate(paragraphs):
            # Проверяем, что это объект Par
            if not hasattr(paragraph, 'runs'):
                continue
                
            # Извлекаем текст параграфа
            paragraph_text = ""
            list_position = None
            action_log = "keep"  # чем закончилась обработка параграфа
            
            # Получаем текст и list_position из runs
            for run in paragraph.runs:
                paragraph_text += run.text
            
            # Получаем list_position
            if hasattr(paragraph, 'list_position'):
                list_position = paragraph.list_position

            # Логируем только важную информацию для диагностики
            if list_position and len(list_position) >= 2 and list_position[1]:
                self.logger.debug(f"[docx2python:num] idx={i} list_position={list_position} text='{paragraph_text[:50]}...'")
            
            # Обнаружение явного заголовка раздела вида "1.", "1.2.", "1.2.3."
            explicit_header = re.match(r'^\s*(\d+(?:\.\d+)*)\.(\s*)(.*)$', paragraph_text)
            if explicit_header:
                heading_style = getattr(paragraph, 'style', '')
                header_num_str = explicit_header.group(1)
                after_space = explicit_header.group(2)
                after_text = explicit_header.group(3)
                try:
                    header_path = [int(x) for x in header_num_str.split('.')]
                except Exception:
                    header_path = []

                # Если это повтор заголовка на том же пути — нумеруем как дочерний (без зависимости от стиля)
                if header_path and current_section_path and header_path == current_section_path:
                    key = tuple(current_section_path)
                    next_idx = child_counters.get(key, 0) + 1
                    child_counters[key] = next_idx
                    new_path = current_section_path + [next_idx]
                    new_num = '.'.join(str(x) for x in new_path) + '.'
                    restored_paragraphs.append(f"{new_num}{after_space}{after_text}")
                    action_log = f"replace: explicit->child {new_num}"
                    continue

                # Иначе считаем это установкой текущего пути секции
                if header_path:
                    current_section_path = header_path
                    # Зафиксируем текущий корневой номер
                    try:
                        last_root = header_path[0]
                    except Exception:
                        pass
                    # Инициализируем счетчик для этого пути
                    child_counters.setdefault(tuple(current_section_path), 0)
                restored_paragraphs.append(paragraph_text)
                action_log = "keep: explicit header"
                continue

            # Восстанавливаем нумерацию на основе list_position
            if list_position and len(list_position) >= 2 and list_position[1]:
                numbering_levels = list_position[1]
                
                # Проверяем, что это пронумерованный список
                simple_list_match = re.match(r'^(\s*)(\d+)\)\s*(.*)$', paragraph_text)
                if simple_list_match:
                    indent = simple_list_match.group(1)
                    n_local = int(simple_list_match.group(2))
                    rest = simple_list_match.group(3)
                    
                    try:
                        # Определяем уровень иерархии по отступам (табы и пробелы)
                        # Считаем табы как 4 пробела каждый
                        tab_count = indent.count('\t')
                        space_count = len(indent) - tab_count
                        level = tab_count + (space_count // 4)
                        
                        # Обновляем счетчики для текущего уровня
                        if level not in level_counters:
                            level_counters[level] = 0
                        level_counters[level] = n_local
                        
                        # Обрезаем стек до текущего уровня
                        hierarchy_stack = hierarchy_stack[:level]
                        
                        # Строим номер на основе текущей иерархии
                        if level == 0:
                            # Корневой уровень
                            new_num = f"{n_local}."
                            hierarchy_stack = [n_local]
                        else:
                            # Подчиненный уровень
                            if hierarchy_stack:
                                # Добавляем к родительскому пути
                                parent_path = hierarchy_stack.copy()
                                parent_path.append(n_local)
                                new_num = '.'.join(str(x) for x in parent_path) + '.'
                                hierarchy_stack = parent_path
                            else:
                                # Если нет родителя, создаем новый корень
                                new_num = f"{n_local}."
                                hierarchy_stack = [n_local]
                        
                        restored_paragraphs.append(f"{indent}{new_num} {rest}")
                        action_log = f"replace: level {level} -> {new_num}"
                        continue
                            
                    except Exception as e:
                        self.logger.warning(f"Ошибка при обработке нумерации: {e}")
                        restored_paragraphs.append(paragraph_text)
                        action_log = "keep: error"
                        continue
                else:
                    # Если это не пронумерованный список, оставляем как есть
                    restored_paragraphs.append(paragraph_text)
                    action_log = "keep: not numbered"
            else:
                # Если нет list_position, проверяем на маркеры списков
                if paragraph_text.strip().startswith('--'):
                    # Заменяем -- на • для маркеров списков
                    new_text = paragraph_text.replace('--', '•', 1)
                    restored_paragraphs.append(new_text)
                    action_log = "replace: bullet -> •"
                else:
                    # Оставляем как есть
                    restored_paragraphs.append(paragraph_text)
                    action_log = "keep: plain"

            # Итог по абзацу (только для отладки)
            if action_log.startswith("replace"):
                self.logger.debug(f"[num-debug] idx={i} action={action_log}")
        
        return "\n".join(restored_paragraphs)
    
    def _build_hierarchical_numbering(self, list_position, hierarchy_tracker):
        """
        Строит полную иерархическую нумерацию на основе list_position
        
        Args:
            list_position: кортеж (style_id, numbering_levels) из docx2python
            hierarchy_tracker: словарь для отслеживания текущих номеров по уровням
        
        Returns:
            str: полная иерархическая нумерация (например, "1.1.2.")
        """
        style_id, numbering_levels = list_position
        
        
        # Определяем уровень иерархии по style_id
        # Поддерживаем произвольную глубину иерархии
        if style_id and style_id.isdigit():
            style_id_num = int(style_id)
            
            # Для style_id >= 32 - это уровни иерархии (32=1, 33=2, 34=3, 35=4, и т.д.)
            if style_id_num >= 32:
                hierarchy_level = style_id_num - 31
            else:
                # Для style_id < 32 - это не уровни иерархии, а маркеры списков
                if numbering_levels:
                    return str(numbering_levels[0]) + "."
                else:
                    return "1."
        else:
            # Если style_id не число, возвращаем простую нумерацию
            if numbering_levels:
                return str(numbering_levels[0]) + "."
            else:
                return "1."
        
        # Инициализируем трекер для всех уровней до текущего
        for level in range(1, hierarchy_level + 1):
            if level not in hierarchy_tracker:
                hierarchy_tracker[level] = 0
        
        # Сбрасываем счетчики для более глубоких уровней
        for level in range(hierarchy_level + 1, max(hierarchy_tracker.keys(), default=0) + 1):
            hierarchy_tracker[level] = 0
        
        # Устанавливаем номер для текущего уровня из numbering_levels
        if numbering_levels:
            hierarchy_tracker[hierarchy_level] = numbering_levels[0]
        
        # Строим полную нумерацию
        full_numbering_parts = []
        for level in range(1, hierarchy_level + 1):
            full_numbering_parts.append(str(hierarchy_tracker[level]))
        
        return ".".join(full_numbering_parts) + "."
    
    def _find_table_paragraphs_docx2python(self, paragraphs: List[str]) -> List[Dict]:
        """
        Поиск абзацев, начинающихся со слова "Таблица" в списке параграфов
        
        Args:
            paragraphs: Список параграфов документа
            
        Returns:
            Список словарей с информацией об абзацах "Таблица"
        """
        table_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs):
            paragraph = paragraph.strip()
            if paragraph.lower().startswith('таблица'):
                table_paragraphs.append({
                    'index': i,
                    'text': paragraph
                })
        
        return table_paragraphs
    
    def _extract_table_info_from_docx(self, file_path: str) -> List[Dict]:
        """
        Извлекает информацию о таблицах из DOCX XML (параграфы "Таблица" и их названия)
        
        Args:
            file_path: Путь к DOCX файлу
            
        Returns:
            Список словарей с информацией о таблицах: индекс параграфа, текст, название
        """
        table_info = []
        
        try:
            with ZipFile(file_path) as docx_zip:
                document_bytes = docx_zip.read("word/document.xml")
            root = etree.fromstring(document_bytes)
        except Exception as exc:
            self.logger.error(f"Не удалось извлечь информацию о таблицах из DOCX: {exc}")
            return table_info
        
        # Находим body документа
        body = root.find("w:body", namespaces=NSMAP)
        if body is None:
            return table_info
        
        # Получаем все элементы body в порядке их появления
        all_elements = list(body)
        
        # Находим все параграфы для сопоставления индексов
        paragraphs = root.findall(".//w:p", namespaces=NSMAP)
        
        # Создаем словарь для быстрого поиска позиции параграфа в body
        para_positions = {}
        for pos, elem in enumerate(all_elements):
            if elem.tag == f"{{{WORD_NAMESPACE}}}p":
                para_id = id(elem)
                if para_id not in para_positions:
                    para_positions[para_id] = pos
        
        # Находим параграфы "Таблица"
        for para_idx, para in enumerate(paragraphs):
            # Извлекаем текст из параграфа
            texts = para.findall(".//w:t", namespaces=NSMAP)
            if not texts:
                continue
            
            para_text = "".join(t.text or "" for t in texts).strip()
            
            # Проверяем, начинается ли параграф со слова "Таблица"
            if para_text.lower().startswith('таблица'):
                # Извлекаем название из "Таблица N. Название" или "Таблица N Название"
                import re
                match = re.match(r'Таблица\s+\d+[.\s]+(.+)', para_text, re.IGNORECASE)
                table_name = match.group(1).strip() if match else ""
                
                # Ищем название в следующем параграфе, если не найдено в текущем
                if not table_name and para_idx + 1 < len(paragraphs):
                    next_para = paragraphs[para_idx + 1]
                    next_texts = next_para.findall(".//w:t", namespaces=NSMAP)
                    if next_texts:
                        next_text = "".join(t.text or "" for t in next_texts).strip()
                        # Проверяем, что следующий параграф не является таблицей
                        if next_text and not next_text.lower().startswith('таблица'):
                            # Проверяем, что следующий элемент не содержит таблицу
                            if next_para.find(".//w:tbl", namespaces=NSMAP) is None:
                                table_name = next_text
                
                # Ищем текст после таблицы
                text_after_table = ""
                para_id = id(para)
                para_position = para_positions.get(para_id)
                
                if para_position is not None:
                    # Ищем следующую таблицу после этого параграфа
                    for pos in range(para_position + 1, len(all_elements)):
                        elem = all_elements[pos]
                        # Проверяем, является ли элемент таблицей
                        if elem.tag == f"{{{WORD_NAMESPACE}}}tbl":
                            # Нашли таблицу, теперь ищем первый параграф с текстом после неё
                            for pos2 in range(pos + 1, min(pos + 20, len(all_elements))):
                                elem2 = all_elements[pos2]
                                # Проверяем, не является ли это следующей таблицей
                                if elem2.tag == f"{{{WORD_NAMESPACE}}}tbl":
                                    break
                                # Проверяем, является ли это параграфом
                                if elem2.tag == f"{{{WORD_NAMESPACE}}}p":
                                    texts2 = elem2.findall(".//w:t", namespaces=NSMAP)
                                    if texts2:
                                        text2 = "".join(t.text or "" for t in texts2).strip()
                                        # Проверяем, не является ли это следующим параграфом "Таблица"
                                        if text2.lower().startswith('таблица'):
                                            break
                                        if text2:
                                            text_after_table = text2
                                            break
                            break
                
                table_info.append({
                    'index': para_idx,
                    'text': para_text,
                    'table_name': table_name,
                    'text_after_table': text_after_table
                })
        
        return table_info

    def _remove_tables_from_text(
        self,
        docx2python_text: str,
        table_info: List[Dict],
        docx_tables: List[ParsedDocxTable],
    ) -> tuple[str, List[Dict]]:
        """
        Удаляет содержимое таблиц из текста, оставляя только "Таблица N. Название"
        
        Args:
            docx2python_text: Текст из docx2python
            table_info: Информация о таблицах из DOCX XML
            docx_tables: Список таблиц, извлеченных напрямую из DOCX
            
        Returns:
            Кортеж: (текст без содержимого таблиц, список данных о таблицах с позициями)
        """
        # Разбиваем текст на параграфы один раз
        docx_paragraphs = docx2python_text.split('\n')
        
        # Находим абзацы "Таблица" в тексте docx2python
        docx_table_paragraphs = self._find_table_paragraphs_docx2python(docx_paragraphs)
        
        if len(docx_table_paragraphs) != len(table_info):
            self.logger.warning(f"Количество абзацев 'Таблица' не совпадает: "
                              f"docx2python={len(docx_table_paragraphs)}, "
                              f"docx_xml={len(table_info)}")
        if docx_tables and len(docx_tables) != len(docx_table_paragraphs):
            self.logger.warning(
                f"Число таблиц в DOCX ({len(docx_tables)}) не совпадает с числом ссылок 'Таблица' ({len(docx_table_paragraphs)})"
            )
        
        # Собираем информацию о таблицах и удаляем содержимое таблиц
        tables_data: List[Dict] = []
        indices_to_remove = set()
        
        # Обрабатываем таблицы в обратном порядке, чтобы индексы не сдвигались
        for i in range(len(docx_table_paragraphs) - 1, -1, -1):
            docx_para = docx_table_paragraphs[i]
            
            if i >= len(docx_tables):
                raise ValueError(f"Таблица {i+1} не найдена в DOCX файле")
            
            docx_table = docx_tables[i]
            
            # Получаем название таблицы из table_info, если доступно
            table_name = ""
            if i < len(table_info):
                table_name = table_info[i].get('table_name', '')
            
            # Если название не найдено в table_info, пытаемся извлечь из параграфа
            para_text = docx_para.get('text', '')
            import re
            if not table_name:
                match = re.match(r'Таблица\s+\d+[.\s]+(.+)', para_text, re.IGNORECASE)
                if match:
                    table_name = match.group(1).strip()
            
            if not table_name:
                raise ValueError(f"Название таблицы {i+1} не найдено")
            
            # Определяем позицию таблицы в исходном тексте
            start_index = docx_para['index']
            
            # Если есть текст после таблицы, ищем соответствующий параграф в docx
            text_after_table = ""
            if i < len(table_info):
                text_after_table = table_info[i].get('text_after_table', '')
            
            # Определяем end_index - конец содержимого таблицы
            end_index = start_index + 1  # По умолчанию удаляем только параграф "Таблица"
            
            if text_after_table:
                # Ищем текст после таблицы
                for j in range(start_index + 1, len(docx_paragraphs)):
                    if text_after_table in docx_paragraphs[j]:
                        end_index = j
                        break
                # Если не нашли text_after_table, ищем следующую таблицу
                if end_index == start_index + 1:
                    # Ищем следующий параграф "Таблица"
                    for j in range(start_index + 1, len(docx_paragraphs)):
                        if docx_paragraphs[j].strip().lower().startswith('таблица'):
                            end_index = j
                            break
                    # Если следующей таблицы нет, удаляем до конца
                    if end_index == start_index + 1:
                        end_index = len(docx_paragraphs)
            else:
                # Если текста после таблицы нет - ищем следующую таблицу или конец файла
                for j in range(start_index + 1, len(docx_paragraphs)):
                    if docx_paragraphs[j].strip().lower().startswith('таблица'):
                        end_index = j
                        break
                # Если следующей таблицы нет, удаляем до конца
                if end_index == start_index + 1:
                    end_index = len(docx_paragraphs)
            
            # Вычисляем позицию в исходном тексте (до удаления)
            text_before = '\n'.join(docx_paragraphs[:start_index])
            position_in_text = len(text_before)
            
            # Сохраняем информацию о таблице
            tables_data.append({
                'table_name': table_name,
                'table_index': i,
                'position_in_text': position_in_text,
                'start_paragraph_index': start_index,
                'end_paragraph_index': end_index,
                'docx_table': docx_table,
                'table_paragraph_text': para_text,  # Сохраняем текст параграфа "Таблица N. Название"
            })
            
            # Помечаем параграфы для удаления (включая сам параграф "Таблица")
            # Удаляем полностью параграф "Таблица N" и всё содержимое таблицы
            for idx in range(start_index, end_index):
                indices_to_remove.add(idx)
        
        # Удаляем помеченные параграфы (параграфы "Таблица" и их содержимое)
        text_without_table_content = '\n'.join(
            para for idx, para in enumerate(docx_paragraphs) 
            if idx not in indices_to_remove
        )
        
        return text_without_table_content, tables_data
    
    # ===== ИЕРАРХИЧЕСКИЙ ЧАНКИНГ =====
    
    def parse_hierarchy(self, text: str) -> List[Any]:
        """
        Парсит иерархию из плоского текста с нумерацией
        
        Args:
            text: Плоский текст с нумерацией
            
        Returns:
            Список корневых узлов иерархии
        """
        from .hierarchy_parser import HierarchyParser
        
        parser = HierarchyParser()
        return parser.parse_hierarchy(text)
    
    def generate_semantic_chunks(self, text: str, target_level: int = 3, 
                                max_chunk_size: int = 1000) -> List[Any]:
        """
        Генерирует семантические чанки из текста с иерархией
        
        Args:
            text: Плоский текст с нумерацией
            target_level: Целевой уровень для чанкинга
            max_chunk_size: Максимальный размер чанка
            
        Returns:
            Список семантических чанков
        """
        from .hierarchical_chunker import HierarchicalChunker
        
        # Создаем конфигурацию для иерархического чанкера
        chunker_config = {
            'target_level': target_level,
            'max_chunk_size': max_chunk_size,
        }
        
        chunker = HierarchicalChunker(chunker_config)
        result = chunker.process_text(text)
        return result['chunks']
    
    def get_section_context(self, text: str, section_number: str) -> Dict[str, Any]:
        """
        Получает контекст раздела (родитель + дочерние разделы)
        
        Args:
            text: Плоский текст с нумерацией
            section_number: Номер раздела
            
        Returns:
            Контекст раздела
        """
        from .hierarchical_chunker import HierarchicalChunker
        
        chunker = HierarchicalChunker(self.config)
        return chunker.get_section_context(text, section_number)
    
    def process_with_hierarchical_chunking(self, text: str, 
                                         target_level: int = 3,
                                         max_chunk_size: int = 1000) -> Dict[str, Any]:
        """
        Обрабатывает текст с иерархическим чанкингом
        
        Args:
            text: Плоский текст с нумерацией
            target_level: Целевой уровень для чанкинга
            max_chunk_size: Максимальный размер чанка
            
        Returns:
            Результат обработки с чанками и метаданными
        """
        from .hierarchical_chunker import HierarchicalChunker
        
        # Создаем конфигурацию для иерархического чанкера
        chunker_config = {
            'target_level': target_level,
            'max_chunk_size': max_chunk_size,
        }
        
        chunker = HierarchicalChunker(chunker_config)
        return chunker.process_text(text)
    
    def get_sections_by_level(self, text: str, level: int) -> List[Any]:
        """
        Получает все разделы заданного уровня
        
        Args:
            text: Плоский текст с нумерацией
            level: Уровень разделов
            
        Returns:
            Список разделов заданного уровня
        """
        from .hierarchy_parser import HierarchyParser
        
        parser = HierarchyParser()
        sections = parser.parse_hierarchy(text)
        return parser.get_sections_by_level(level)

    # ===== END-TO-END PIPELINE =====
    def run_end_to_end(self, input_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Полная обработка одного исходного файла: DOC/DOCX -> плоский текст -> иерархический чанкинг
        Возвращает только итоговую структуру с sections/chunks/metadata без промежуточных полей.
        """
        # 1) Извлечь плоский текст комбинированным методом
        combined_result = self._process_with_combined_approach(input_path)
        combined_text = combined_result.get("combined_text", "")
        extracted_text = combined_result.get("original_docx2python_text", "")

        # Опционально сохраняем текст из _extract_text_with_docx2python
        out_cfg = self.config.get("output", {})
        if out_cfg.get("save_docx2python_text") and output_dir:
            try:
                base_name = Path(input_path).stem
                out_file = os.path.join(output_dir, f"{base_name}_docx2python.txt")
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(extracted_text or "")
            except Exception as e:
                self.logger.warning(f"Не удалось сохранить docx2python текст: {e}")

        # 1.5) Извлекаем оглавление документа
        toc_text = ""
        if input_path.lower().endswith('.docx'):
            try:
                toc_text = self._extract_table_of_contents(input_path)
                if output_dir and toc_text:
                    base_name = Path(input_path).stem
                    toc_file = os.path.join(output_dir, f"{base_name}_toc.txt")
                    with open(toc_file, "w", encoding="utf-8") as f:
                        f.write(toc_text)
            except Exception as e:
                self.logger.warning(f"Не удалось извлечь оглавление: {e}")

        # 1.6) Сохраняем параграфы с list_position (опционально)
        out_cfg = self.config.get("output", {})
        if (input_path.lower().endswith('.docx') and output_dir and 
            out_cfg.get("save_list_positions", False)):
            try:
                list_position_paragraphs = self._extract_list_position_paragraphs(input_path)
                if list_position_paragraphs:
                    base_name = Path(input_path).stem
                    list_pos_file = os.path.join(output_dir, f"{base_name}_list_positions.json")
                    with open(list_pos_file, "w", encoding="utf-8") as f:
                        json.dump(list_position_paragraphs, f, ensure_ascii=False, indent=2)
            except Exception as e:
                self.logger.warning(f"Не удалось извлечь list_position: {e}")

        # 2) Иерархический чанкинг основного текста
        hconf = self.config.get("hierarchical_chunking", {})
        target_level = hconf.get("target_level", 3)
        max_chunk_size = hconf.get("max_chunk_size", 1000)
        process_result = self.process_with_hierarchical_chunking(
            combined_text,
            target_level=target_level,
            max_chunk_size=max_chunk_size,
        )

        # 2.5) Чанкинг оглавления
        toc_chunks = []
        if toc_text:
            try:
                toc_chunks = self._chunk_table_of_contents(toc_text, max_chunk_size)
            except Exception as e:
                self.logger.warning(f"Не удалось обработать оглавление: {e}")

        # 2.6) Создаем подразделы для таблиц в иерархии
        tables_data = combined_result.get("tables_data", [])
        if tables_data:
            try:
                process_result = self._create_table_subsections(
                    tables_data,
                    extracted_text,  # Исходный текст для определения позиций
                    process_result,
                )
            except Exception as e:
                self.logger.warning(f"Не удалось создать подразделы для таблиц: {e}")

        # 2.7) Обработка таблиц отдельно с созданием чанков
        table_chunks = []
        if tables_data:
            try:
                table_chunks = self._process_tables_with_sections(
                    tables_data,
                    process_result.get("sections", []),
                    max_chunk_size,
                )
            except Exception as e:
                self.logger.warning(f"Не удалось обработать таблицы: {e}")

        # 2.8) Обновляем чанки разделов, добавляя в children идентификаторы чанков таблиц
        if table_chunks:
            process_result["chunks"] = self._update_chunks_with_table_children(
                process_result.get("chunks", []),
                table_chunks,
                process_result,
            )

        # 3) Сформировать итоговый результат
        return {
            "file_path": input_path,
            "sections": process_result.get("sections", []),
            "chunks": process_result.get("chunks", []),
            "toc_chunks": toc_chunks,  # Чанки оглавления
            "table_chunks": table_chunks,  # Чанки таблиц
            "metadata": {
                **{k: v for k, v in process_result.get("metadata", {}).items()},
                "created_at": datetime.utcnow().isoformat() + "Z",
                "has_toc": bool(toc_text),
                "tables_count": len(tables_data),
            },
        }

    def run_end_to_end_folder(self, folder_path: str, output_dir: str) -> Dict[str, Any]:
        """
        Полная обработка всех файлов в папке. Сохраняет в output_dir по файлу на каждый входной документ
        только sections/chunks/metadata.
        """
        os.makedirs(output_dir, exist_ok=True)
        files = self._get_files_to_process(folder_path)
        summary = {"total_files": len(files), "successful": 0, "failed": 0}
        results: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []

        for file_path in files:
            try:
                result = self.run_end_to_end(file_path, output_dir)
                results.append({"file_path": file_path})
                summary["successful"] += 1

                base_name = Path(file_path).stem
                out_file = os.path.join(output_dir, f"{base_name}_hierarchical.json")
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
            except Exception as e:
                errors.append({"file": file_path, "error": str(e)})
                summary["failed"] += 1

        return {"processed_files": results, "errors": errors, "summary": summary}
    
    def _extract_list_position_paragraphs(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Извлекает параграфы с непустым list_position
        
        Args:
            file_path: Путь к DOCX файлу
            
        Returns:
            Список параграфов с list_position и text
        """
        if not DOCX2PYTHON_AVAILABLE:
            raise ImportError("Пакет docx2python недоступен")
        
        try:
            doc = docx2python(file_path)
            
            # Извлекаем все параграфы
            all_paragraphs = self._extract_all_paragraphs(doc.document_pars)
            
            # Используем NumberingRestorer для извлечения list_position
            list_position_paragraphs = self.numbering_restorer.extract_list_position_paragraphs(all_paragraphs)
            
            doc.close()
            return list_position_paragraphs
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении list_position: {e}")
            return []
    
    def _create_table_subsections(
        self,
        tables_data: List[Dict],
        original_text: str,
        process_result: Dict,
    ) -> Dict:
        """
        Создает подразделы для таблиц в иерархии
        
        Args:
            tables_data: Данные о таблицах с позициями
            original_text: Исходный текст для определения родительских разделов
            process_result: Результат обработки с разделами
            
        Returns:
            Обновленный process_result с подразделами таблиц
        """
        from .hierarchy_parser import HierarchyParser, SectionNode
        from typing import Optional
        
        # Парсим иерархию для получения структуры разделов
        parser = HierarchyParser()
        section_nodes = parser.parse_hierarchy(original_text)
        
        # Строим карту позиций разделов
        section_positions = self._build_section_position_map(original_text, process_result.get("sections", []))
        
        # Создаем подразделы для таблиц
        for table_data in tables_data:
            table_name = table_data['table_name']
            position = table_data['position_in_text']
            table_index = table_data['table_index']
            table_paragraph_text = table_data.get('table_paragraph_text', f'Таблица {table_index + 1}. {table_name}')
            
            # Определяем родительский раздел для таблицы по позиции
            section_info = self._find_section_for_position(position, section_positions, process_result.get("sections", []))
            
            # Находим соответствующий SectionNode
            parent_node = self._find_section_node_by_path(section_info.get('section_path', []), section_nodes)
            
            if parent_node:
                # Создаем подраздел для таблицы
                table_section_number = f"{parent_node.number}.T{table_index + 1}"
                table_section = SectionNode(
                    number=table_section_number,
                    title=table_paragraph_text,
                    level=parent_node.level + 1,
                    content=table_paragraph_text,  # Только "Таблица N. Название"
                    parent=parent_node
                )
                parent_node.children.append(table_section)
                parent_node.tables.append(table_section_number)
                section_nodes.append(table_section)
                
                # Сохраняем номер подраздела в данных таблицы
                table_data['table_subsection_number'] = table_section_number
        
        # Обновляем sections в process_result
        from .hierarchical_chunker import HierarchicalChunker
        chunker = HierarchicalChunker()
        process_result["sections"] = chunker._serialize_sections(section_nodes)
        
        # Перегенерируем чанки, чтобы включить подразделы таблиц
        hconf = self.config.get("hierarchical_chunking", {})
        target_level = hconf.get("target_level", 3)
        max_chunk_size = hconf.get("max_chunk_size", 1000)
        
        from .semantic_chunker import SemanticChunker
        semantic_chunker = SemanticChunker(max_chunk_size=max_chunk_size)
        updated_chunks = semantic_chunker.generate_chunks(section_nodes, target_level=target_level)
        
        # Сериализуем обновленные чанки
        process_result["chunks"] = chunker._serialize_chunks(updated_chunks)
        
        return process_result
    
    def _find_section_node_by_path(
        self,
        section_path: List[str],
        section_nodes: List,
    ):
        """
        Находит SectionNode по пути из заголовков
        
        Args:
            section_path: Путь из заголовков разделов
            section_nodes: Список разделов
            
        Returns:
            SectionNode или None
        """
        from .hierarchy_parser import SectionNode
        from typing import Optional
        
        if not section_path:
            return None
        
        # Ищем раздел по заголовку
        for node in section_nodes:
            if node.title == section_path[-1]:
                # Проверяем путь
                current = node
                path_idx = len(section_path) - 1
                while current and path_idx >= 0:
                    if current.title != section_path[path_idx]:
                        break
                    current = current.parent
                    path_idx -= 1
                
                if path_idx < 0:
                    return node
        
        return None
    
    def _process_tables_with_sections(
        self,
        tables_data: List[Dict],
        sections: List[Dict],
        max_chunk_size: int,
    ) -> List[Dict]:
        """
        Обрабатывает таблицы и создает чанки с метаданными
        
        Args:
            tables_data: Данные о таблицах с позициями и номерами подразделов
            sections: Список разделов из иерархического парсинга
            max_chunk_size: Максимальный размер чанка
            
        Returns:
            Список чанков таблиц с метаданными
        """
        import uuid
        from .hierarchy_parser import ChunkMetadata
        
        table_chunks = []
        
        for table_data in tables_data:
            table_name = table_data['table_name']
            docx_table = table_data['docx_table']
            table_index = table_data['table_index']
            table_subsection_number = table_data.get('table_subsection_number', f'Table_{table_index + 1}')
            
            # Чанкуем таблицу
            table_chunk_contents = self.table_processor.docx_table_to_chunks(
                docx_table, table_name, max_chunk_size
            )
            
            # Создаем чанки с метаданными
            for chunk_idx, chunk_content in enumerate(table_chunk_contents):
                chunk_id = str(uuid.uuid4())
                
                # Создаем метаданные для чанка таблицы
                metadata = ChunkMetadata(
                    chunk_id=chunk_id,
                    chunk_number=chunk_idx + 1,
                    section_path=[],  # Убираем section_path
                    parent_section=table_subsection_number,  # Используем номер подраздела
                    section_level=0,
                    children=[],
                    word_count=len(chunk_content.split()),
                    char_count=len(chunk_content),
                    contains_lists=False,
                    is_complete_section=False,
                    start_pos=0,
                    end_pos=len(chunk_content),
                    table_id=f"Table_{table_index + 1}",
                )
                
                table_chunks.append({
                    'content': chunk_content,
                    'metadata': {
                        'chunk_id': metadata.chunk_id,
                        'chunk_number': metadata.chunk_number,
                        'parent_section': metadata.parent_section,
                        'section_level': metadata.section_level,
                        'children': metadata.children,
                        'word_count': metadata.word_count,
                        'char_count': metadata.char_count,
                        'contains_lists': metadata.contains_lists,
                        'table_id': metadata.table_id,
                        'is_complete_section': metadata.is_complete_section,
                        'start_pos': metadata.start_pos,
                        'end_pos': metadata.end_pos,
                        'table_name': table_name,
                        'table_index': table_index,
                    }
                })
        
        return table_chunks
    
    def _build_section_position_map(
        self,
        text: str,
        sections: List[Dict],
    ) -> List[Dict]:
        """
        Строит карту позиций разделов в тексте
        
        Args:
            text: Исходный текст
            sections: Список разделов
            
        Returns:
            Список словарей с информацией о позициях разделов
        """
        from .hierarchy_parser import HierarchyParser
        
        # Парсим иерархию для получения полной структуры с позициями
        parser = HierarchyParser()
        section_nodes = parser.parse_hierarchy(text)
        
        # Строим карту позиций
        position_map = []
        current_pos = 0
        
        def process_section(node, parent_path: List[str] = []):
            nonlocal current_pos
            
            # Находим позицию начала раздела в тексте
            section_path = parent_path + [node.number]
            
            # Ищем заголовок раздела в тексте
            section_start = text.find(node.title, current_pos)
            if section_start == -1:
                # Если не нашли по заголовку, используем текущую позицию
                section_start = current_pos
            else:
                current_pos = section_start
            
            position_map.append({
                'section_number': node.number,
                'section_title': node.title,
                'section_level': node.level,
                'section_path': section_path,
                'parent_section': node.parent.number if node.parent else 'Root',
                'children': [child.number for child in node.children],
                'start_position': section_start,
                'content': node.content,
            })
            
            # Обрабатываем дочерние разделы
            for child in node.children:
                process_section(child, section_path)
        
        # Обрабатываем все корневые разделы
        for node in section_nodes:
            process_section(node)
        
        return position_map
    
    def _find_section_for_position(
        self,
        position: int,
        section_positions: List[Dict],
        sections: List[Dict],
    ) -> Dict:
        """
        Находит раздел для заданной позиции в тексте
        
        Args:
            position: Позиция в тексте
            section_positions: Карта позиций разделов
            sections: Список разделов
            
        Returns:
            Информация о разделе
        """
        # Находим самый глубокий раздел, который содержит эту позицию
        best_match = None
        best_level = -1
        
        for section_pos in section_positions:
            start = section_pos['start_position']
            content = section_pos.get('content', '')
            end = start + len(content) if content else start + 1000  # Примерная оценка
            
            if start <= position <= end:
                if section_pos['section_level'] > best_level:
                    best_level = section_pos['section_level']
                    best_match = section_pos
        
        if best_match:
            # Строим section_path из заголовков разделов, как в чанках
            section_path = self._build_section_path_from_sections(
                best_match['section_path'], sections
            )
            
            # Находим parent_section из заголовка, а не из номера
            parent_section_title = self._find_section_title_by_number(
                best_match['parent_section'], sections
            )
            
            return {
                'section_path': section_path,
                'parent_section': parent_section_title if parent_section_title else 'Root',
                'section_level': best_match['section_level'],
                'children': best_match['children'],
            }
        
        # Если не нашли, возвращаем корневой раздел
        return {
            'section_path': ['Root'],
            'parent_section': 'Root',
            'section_level': 0,
            'children': [],
        }
    
    def _build_section_path_from_sections(
        self,
        section_number_path: List[str],
        sections: List[Dict],
    ) -> List[str]:
        """
        Строит section_path из заголовков разделов по пути из номеров
        
        Args:
            section_number_path: Путь из номеров разделов (например, ["0", "1.1"])
            sections: Список разделов
            
        Returns:
            Путь из заголовков разделов (например, ["Пример сложной таблицы", "Подраздел"])
        """
        section_path = []
        
        # Создаем словарь номер -> раздел для быстрого поиска
        sections_by_number = {s['number']: s for s in sections}
        
        # Строим путь из заголовков
        for number in section_number_path:
            if number in sections_by_number:
                section_path.append(sections_by_number[number]['title'])
            else:
                # Если не нашли, используем номер
                section_path.append(number)
        
        return section_path if section_path else ['Root']
    
    def _find_section_title_by_number(
        self,
        section_number: str,
        sections: List[Dict],
    ) -> Optional[str]:
        """
        Находит заголовок раздела по его номеру
        
        Args:
            section_number: Номер раздела
            sections: Список разделов
            
        Returns:
            Заголовок раздела или None
        """
        for section in sections:
            if section['number'] == section_number:
                return section['title']
        return None
    
    def _update_chunks_with_table_children(
        self,
        section_chunks: List[Dict],
        table_chunks: List[Dict],
        process_result: Dict,
    ) -> List[Dict]:
        """
        Обновляет чанки разделов, добавляя в children идентификаторы чанков таблиц
        
        Args:
            section_chunks: Чанки разделов
            table_chunks: Чанки таблиц
            
        Returns:
            Обновленные чанки разделов
        """
        # Группируем чанки таблиц по parent_section (номеру подраздела таблицы)
        table_chunks_by_subsection: Dict[str, List[str]] = {}
        
        for table_chunk in table_chunks:
            table_parent_section = table_chunk['metadata'].get('parent_section', '')
            table_chunk_id = table_chunk['metadata']['chunk_id']
            
            if table_parent_section:
                if table_parent_section not in table_chunks_by_subsection:
                    table_chunks_by_subsection[table_parent_section] = []
                table_chunks_by_subsection[table_parent_section].append(table_chunk_id)
        
        # Обновляем чанки разделов (включая подразделы таблиц)
        # Сначала находим номера разделов для каждого чанка
        chunk_numbers_by_chunk_id = {}
        for chunk in section_chunks:
            chunk_id = chunk['metadata'].get('chunk_id', '')
            # Получаем номер раздела из section_path или из parent_section для подразделов таблиц
            section_path = chunk['metadata'].get('section_path', [])
            if section_path:
                # Находим номер раздела из sections
                chunk_number = self._find_section_number_by_path(section_path, process_result.get("sections", []))
                if chunk_number:
                    chunk_numbers_by_chunk_id[chunk_id] = chunk_number
        
        updated_chunks = []
        for chunk in section_chunks:
            chunk_id = chunk['metadata'].get('chunk_id', '')
            chunk_number = chunk_numbers_by_chunk_id.get(chunk_id, '')
            
            # Получаем идентификаторы чанков таблиц для этого раздела/подраздела
            table_chunk_ids = []
            # Если это подраздел таблицы (номер содержит .T), добавляем его чанки
            if '.T' in chunk_number:
                table_chunk_ids = table_chunks_by_subsection.get(chunk_number, [])
            # Если это обычный раздел, ищем чанки таблиц по номеру раздела
            elif chunk_number:
                # Ищем подразделы таблиц, которые являются детьми этого раздела
                for subsection_number, chunk_ids in table_chunks_by_subsection.items():
                    # Проверяем, является ли подраздел таблицы дочерним для этого раздела
                    if subsection_number.startswith(chunk_number + '.'):
                        table_chunk_ids.extend(chunk_ids)
            
            # Обновляем children, добавляя идентификаторы чанков таблиц
            original_children = chunk['metadata'].get('children', [])
            updated_children = original_children + table_chunk_ids
            
            # Создаем обновленный чанк
            updated_chunk = chunk.copy()
            updated_chunk['metadata'] = chunk['metadata'].copy()
            updated_chunk['metadata']['children'] = updated_children
            
            updated_chunks.append(updated_chunk)
        
        return updated_chunks
    
    def _find_section_number_by_path(
        self,
        section_path: List[str],
        sections: List[Dict],
    ) -> Optional[str]:
        """
        Находит номер раздела по пути из заголовков
        
        Args:
            section_path: Путь из заголовков разделов
            sections: Список разделов
            
        Returns:
            Номер раздела или None
        """
        if not section_path:
            return None
        
        # Ищем раздел по последнему заголовку в пути
        last_title = section_path[-1]
        for section in sections:
            if section.get('title') == last_title:
                return section.get('number', '')
        
        return None