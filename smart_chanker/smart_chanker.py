"""
SmartChanker - класс для обработки текстовых файлов
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

# Импорт инструментов обработки
try:
    from unstructured.partition.auto import partition
    from unstructured.chunking.title import chunk_by_title
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logging.warning("Пакет unstructured не установлен")

try:
    import docx2txt
    DOCX2TXT_AVAILABLE = True
except ImportError:
    DOCX2TXT_AVAILABLE = False
    logging.warning("Пакет docx2txt не установлен")


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
                "save_path": "./output"
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
        Проверка доступности инструментов обработки
        """
        tools_status = {
            "unstructured": UNSTRUCTURED_AVAILABLE,
            "docx2txt": DOCX2TXT_AVAILABLE
        }
        
        for tool, available in tools_status.items():
            if not available:
                self.logger.warning(f"Инструмент {tool} недоступен")
    
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
        Получение списка файлов для обработки
        
        Args:
            folder_path: Путь к папке
            
        Returns:
            Список путей к файлам
        """
        supported_extensions = ['.txt', '.docx', '.doc', '.pdf', '.md']
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
        Обработка одного файла
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат обработки файла
        """
        file_ext = Path(file_path).suffix.lower()
        
        # Определяем инструмент для обработки
        if file_ext == '.docx' and self.config["tools"]["docx2txt"]["enabled"]:
            return self._process_with_docx2txt(file_path)
        elif self.config["tools"]["unstructured"]["enabled"]:
            return self._process_with_unstructured(file_path)
        else:
            raise ValueError(f"Нет доступного инструмента для обработки файла {file_path}")
    
    def _process_with_unstructured(self, file_path: str) -> Dict[str, Any]:
        """
        Обработка файла с помощью unstructured
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат обработки
        """
        if not UNSTRUCTURED_AVAILABLE:
            raise ImportError("Пакет unstructured недоступен")
        
        # Парсинг документа
        elements = partition(file_path)
        
        # Разбивка на чанки
        chunks = chunk_by_title(
            elements,
            max_characters=self.config["tools"]["unstructured"]["max_characters"]
        )
        
        return {
            "file_path": file_path,
            "tool_used": "unstructured",
            "chunks": [str(chunk) for chunk in chunks],
            "chunks_count": len(chunks)
        }
    
    def _process_with_docx2txt(self, file_path: str) -> Dict[str, Any]:
        """
        Обработка файла с помощью docx2txt
        
        Args:
            file_path: Путь к файлу
            
        Returns:
            Результат обработки
        """
        if not DOCX2TXT_AVAILABLE:
            raise ImportError("Пакет docx2txt недоступен")
        
        # Извлечение текста
        text = docx2txt.process(file_path)
        
        # Простая разбивка на абзацы
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        return {
            "file_path": file_path,
            "tool_used": "docx2txt",
            "text": text,
            "paragraphs": paragraphs,
            "paragraphs_count": len(paragraphs)
        }
