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
    from unstructured.partition.auto import partition
    from unstructured.chunking.title import chunk_by_title
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logging.warning("Пакет unstructured не установлен")

try:
    from docx2python import docx2python
    DOCX2PYTHON_AVAILABLE = True
except ImportError:
    DOCX2PYTHON_AVAILABLE = False
    logging.warning("Пакет docx2python не установлен")


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
                "docx2python_text_suffix": "_docx2python.txt"
            },
            "hierarchical_chunking": {
                "enabled": False,
                "target_level": 3,
                "max_chunk_size": 1000,
                "preserve_lists": True,
                "include_parent_context": True
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
        if not UNSTRUCTURED_AVAILABLE:
            self.logger.warning("Пакет unstructured недоступен")
        if not DOCX2PYTHON_AVAILABLE:
            self.logger.warning("Пакет docx2python недоступен")
        
        if not UNSTRUCTURED_AVAILABLE or not DOCX2PYTHON_AVAILABLE:
            self.logger.error("Для работы требуется оба пакета: unstructured и docx2python")
    
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
        Комбинированная обработка файла с использованием обоих инструментов
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат обработки
        """
        if not UNSTRUCTURED_AVAILABLE or not DOCX2PYTHON_AVAILABLE:
            raise ImportError("Для комбинированного подхода требуются оба пакета: unstructured и docx2python")
        
        self.logger.info(f"Используем комбинированный подход для файла: {file_path}")
        
        # Обрабатываем с помощью unstructured - получаем элементы
        unstructured_elements = partition(file_path)
        
        # Обрабатываем с помощью docx2python - получаем текст с восстановлением нумерации
        docx2python_text = self._extract_text_with_docx2python(file_path)
        
        # Заменяем таблицы на HTML представление
        combined_text = self._replace_tables_with_html(docx2python_text, unstructured_elements)
        
        # Создаем абзацы из объединенного текста
        combined_paragraphs = [p.strip() for p in combined_text.split('\n\n') if p.strip()]
        
        return {
            "file_path": file_path,
            "tool_used": "combined_approach",
            "original_docx2python_text": docx2python_text,
            "combined_text": combined_text,
            "paragraphs": combined_paragraphs,
            "paragraphs_count": len(combined_paragraphs),
            "table_replacements_count": len(self._find_table_paragraphs_docx2python(docx2python_text))
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
            restored_text = self._restore_numbering_in_paragraphs(all_paragraphs)
            
            doc.close()
            return restored_text
            
        except Exception as e:
            self.logger.error(f"Ошибка при извлечении текста с docx2python: {e}")
            return ""
    
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
    
    def _find_table_paragraphs_unstructured(self, elements: List) -> List[Dict]:
        """
        Поиск абзацев, начинающихся со слова "Таблица" в элементах unstructured
        
        Args:
            elements: Список элементов из unstructured
            
        Returns:
            Список словарей с информацией об абзацах "Таблица"
        """
        table_paragraphs = []
        
        for i, element in enumerate(elements):
            if hasattr(element, 'text') and element.text:
                text = element.text.strip()
                if text.lower().startswith('таблица'):
                    table_paragraphs.append({
                        'index': i,
                        'text': text,
                        'element': element,
                        'category': element.category
                    })
        
        return table_paragraphs
    
    def _find_table_after_paragraph(self, elements: List, start_index: int, max_paragraphs: int = 3, table_paragraphs: List = None) -> Dict:
        """
        Поиск таблицы после абзаца "Таблица" в unstructured
        
        Args:
            elements: Список элементов из unstructured
            start_index: Индекс абзаца "Таблица"
            max_paragraphs: Максимальное количество абзацев для поиска
            
        Returns:
            Словарь с информацией о найденной таблице
        """
        table_found = None
        text_after_table = ""
        paragraph_start_after_table = None
        
        # Ищем таблицу в следующих элементах
        for i in range(start_index + 1, min(start_index + max_paragraphs + 1, len(elements))):
            element = elements[i]
            
            # Останавливаем поиск, если наткнулись на следующий параграф "Таблица"
            if table_paragraphs:
                is_table_paragraph = False
                for table_para in table_paragraphs:
                    if table_para['index'] == i:
                        is_table_paragraph = True
                        break
                
                if is_table_paragraph:
                    # Если это параграф "Таблица", прерываем поиск
                    break
            
            if element.category == 'Table':
                table_found = element
                # Ищем текст после таблицы
                for j in range(i + 1, len(elements)):
                    next_element = elements[j]
                    if hasattr(next_element, 'text') and next_element.text.strip():
                        text_after_table = next_element.text.strip()
                        paragraph_start_after_table = j
                        break
                break
        
        return {
            'table_found': table_found,
            'text_after_table': text_after_table,
            'paragraph_start_after_table': paragraph_start_after_table
        }
    
    def _replace_tables_with_html(self, docx2python_text: str, unstructured_elements: List) -> str:
        """
        Замена таблиц в тексте docx2python на HTML представление из unstructured
        
        Args:
            docx2python_text: Текст из docx2python
            unstructured_elements: Элементы из unstructured
            
        Returns:
            Текст с замененными таблицами
        """
        # Разбиваем текст на параграфы один раз
        docx_paragraphs = docx2python_text.split('\n')
        
        # Находим абзацы "Таблица" в обоих источниках
        docx_table_paragraphs = self._find_table_paragraphs_docx2python(docx_paragraphs)
        unstructured_table_paragraphs = self._find_table_paragraphs_unstructured(unstructured_elements)
        
        if len(docx_table_paragraphs) != len(unstructured_table_paragraphs):
            self.logger.warning(f"Количество абзацев 'Таблица' не совпадает: "
                              f"docx2python={len(docx_table_paragraphs)}, "
                              f"unstructured={len(unstructured_table_paragraphs)}")
        
        # Сопоставляем по порядку и выполняем замены
        for i, (docx_para, unstructured_para) in enumerate(zip(docx_table_paragraphs, unstructured_table_paragraphs)):
            # Находим таблицу после абзаца в unstructured
            table_data = self._find_table_after_paragraph(
                unstructured_elements, 
                unstructured_para['index'],
                self.config.get("tools", {}).get("combined_approach", {}).get("max_paragraphs_after_table", 3),
                unstructured_table_paragraphs
            )
            
            if table_data['table_found']:
                # Создаем JSON таблицу
                json_table = self._convert_table_to_json(table_data['table_found'])
                
                # Определяем конец заменяемого участка
                start_index = docx_para['index']
                
                # Если есть текст после таблицы, ищем соответствующий параграф в docx
                if table_data['text_after_table']:
                    end_index = start_index + 1  # По умолчанию заменяем только параграф "Таблица"
                    for j in range(start_index + 1, len(docx_paragraphs)):
                        if table_data['text_after_table'] in docx_paragraphs[j]:
                            end_index = j
                            break
                else:
                    # Если текста после таблицы нет - заменяем все до конца файла
                    end_index = len(docx_paragraphs)
                
                # Заменяем все параграфы между start_index и end_index на JSON таблицу
                docx_paragraphs[start_index + 1:end_index] = [json_table]
                
                # Обновляем индексы в оставшихся docx_table_paragraphs
                removed_count = end_index - start_index - 2  # Количество удаленных параграфов
                for j in range(i + 1, len(docx_table_paragraphs)):
                    docx_table_paragraphs[j]['index'] -= removed_count - 1 # один параграф добавлен
        
        return '\n'.join(docx_paragraphs)
    
    def _convert_table_to_json(self, table_element) -> str:
        """
        Конвертация элемента таблицы в JSON формат для лучшего понимания LLM
        
        Args:
            table_element: Элемент таблицы из unstructured
            
        Returns:
            JSON представление таблицы
        """
        import json
        
        if hasattr(table_element, 'metadata') and hasattr(table_element.metadata, 'text_as_html'):
            # Парсим HTML и конвертируем в JSON
            return self._html_to_json(table_element.metadata.text_as_html)
        else:
            # Создаем простую JSON структуру
            table_data = {
                "type": "table",
                "content": table_element.text,
                "structure": {
                    "headers": [],
                    "rows": [{"cells": [{"text": table_element.text}]}]
                }
            }
            json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
            return f"```json\n{json_str}\n```"
    
    def _html_to_json(self, html_content: str) -> str:
        """
        Конвертация HTML таблицы в JSON структуру
        
        Args:
            html_content: HTML содержимое таблицы
            
        Returns:
            JSON строка с описанием таблицы
        """
        import json
        from bs4 import BeautifulSoup
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            table = soup.find('table')
            
            if not table:
                return json.dumps({"type": "table", "error": "Не удалось найти таблицу"}, ensure_ascii=False)
            
            # Извлекаем заголовки
            headers = []
            thead = table.find('thead')
            if thead:
                for th in thead.find_all(['th', 'td']):
                    colspan = int(th.get('colspan', 1))
                    header = {"text": th.get_text(strip=True)}
                    if colspan > 1:
                        header["colspan"] = colspan
                    headers.append(header)
            else:
                # Если нет thead, берем первую строку
                first_row = table.find('tr')
                if first_row:
                    for cell in first_row.find_all(['th', 'td']):
                        colspan = int(cell.get('colspan', 1))
                        header = {"text": cell.get_text(strip=True)}
                        if colspan > 1:
                            header["colspan"] = colspan
                        headers.append(header)
            
            # Извлекаем строки данных
            rows = []
            tbody = table.find('tbody') or table
            for tr in tbody.find_all('tr'):
                if tr == first_row and not thead:
                    continue  # Пропускаем первую строку, если она уже в заголовках
                
                cells = []
                for cell in tr.find_all(['td', 'th']):
                    colspan = int(cell.get('colspan', 1))
                    rowspan = int(cell.get('rowspan', 1))
                    cell_data = {"text": cell.get_text(strip=True)}
                    if colspan > 1:
                        cell_data["colspan"] = colspan
                    if rowspan > 1:
                        cell_data["rowspan"] = rowspan
                    cells.append(cell_data)
                
                if cells:  # Добавляем только непустые строки
                    rows.append({"cells": cells})
            
            table_data = {
                "type": "table",
                "structure": {
                    "headers": headers,
                    "rows": rows
                }
            }
            
            json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
            return f"```json\n{json_str}\n```"
            
        except Exception as e:
            # В случае ошибки возвращаем простую структуру
            json_str = json.dumps({
                "type": "table",
                "error": f"Ошибка парсинга: {str(e)}",
                "content": html_content
            }, ensure_ascii=False, indent=2)
            return f"```json\n{json_str}\n```"
    
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
            'preserve_lists': True,
            'include_parent_context': True
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
            'preserve_lists': True,
            'include_parent_context': True
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
                suffix = out_cfg.get("docx2python_text_suffix", "_docx2python.txt")
                out_file = os.path.join(output_dir, f"{base_name}{suffix}")
                with open(out_file, "w", encoding="utf-8") as f:
                    f.write(extracted_text or "")
            except Exception as e:
                self.logger.warning(f"Не удалось сохранить docx2python текст: {e}")

        # 2) Иерархический чанкинг
        hconf = self.config.get("hierarchical_chunking", {})
        target_level = hconf.get("target_level", 3)
        max_chunk_size = hconf.get("max_chunk_size", 1000)
        process_result = self.process_with_hierarchical_chunking(
            combined_text,
            target_level=target_level,
            max_chunk_size=max_chunk_size,
        )

        # 3) Сформировать итоговый результат
        return {
            "file_path": input_path,
            "sections": process_result.get("sections", []),
            "chunks": process_result.get("chunks", []),
            "metadata": {
                **{k: v for k, v in process_result.get("metadata", {}).items()},
                "created_at": datetime.utcnow().isoformat() + "Z",
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