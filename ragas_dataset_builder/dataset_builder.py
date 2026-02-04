"""
Модуль для генерации синтетического набора данных RAGAS
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Добавляем путь к родительскому проекту для импорта smart_chanker
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

try:
    from ragas.testset import TestsetGenerator
except ImportError:
    raise ImportError(
        "RAGAS не установлен. Установите: pip install ragas"
    )

from langchain_core.documents import Document

try:
    from smart_chanker.ragas_converter import RagasConverter
except ImportError:
    raise ImportError(
        "Не удалось импортировать RagasConverter. "
        "Убедитесь, что smart_chanker установлен или находится в родительской директории."
    )

from llm_providers import LLMProvider, EmbeddingProvider


class RagasDatasetBuilder:
    """Класс для генерации синтетического набора данных RAGAS"""
    
    def __init__(self, config_path: str = "config.json"):
        """
        Инициализация билдера
        
        Args:
            config_path: Путь к файлу конфигурации
        """
        self.config = self._load_config(config_path)
        self.converter = RagasConverter()
        
        # Инициализируем LLM и embeddings
        self.llm = LLMProvider.create_llm(self.config["llm"])
        self.embeddings = EmbeddingProvider.create_embeddings(self.config["embeddings"])
        
        # Создаем генератор тестового набора
        self.generator = TestsetGenerator(
            generator_llm=self.llm,
            critic_llm=self.llm,
            embeddings=self.embeddings,
        )
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Загружает конфигурацию из файла
        
        Args:
            config_path: Путь к файлу конфигурации
            
        Returns:
            Словарь с конфигурацией
        """
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Файл конфигурации не найден: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def load_documents(self) -> List[Document]:
        """
        Загружает документы из выходных файлов SmartChanker
        
        Returns:
            Список LangChain Document объектов
        """
        input_config = self.config.get("input", {})
        output_dir = input_config.get("output_dir", "../data/output")
        base_name = input_config.get("base_name", "План short")
        include_tables = input_config.get("include_tables", True)
        include_toc = input_config.get("include_toc", False)
        
        # Находим файлы
        hierarchical_json_path, toc_txt_path = RagasConverter.find_files(
            base_name, output_dir
        )
        
        if not hierarchical_json_path:
            raise FileNotFoundError(
                f"Не найден файл hierarchical.json для '{base_name}' в '{output_dir}'"
            )
        
        # Конвертируем в документы
        documents = self.converter.convert(
            hierarchical_json_path=hierarchical_json_path,
            toc_txt_path=toc_txt_path if include_toc else None,
            include_tables=include_tables,
            include_toc=include_toc
        )
        
        print(f"Загружено документов: {len(documents)}")
        return documents
    
    def build(self) -> Any:
        """
        Генерирует синтетический тестовый набор данных
        
        Returns:
            RAGAS Dataset объект
        """
        # Загружаем документы
        documents = self.load_documents()
        
        if not documents:
            raise ValueError("Не найдено документов для генерации датасета")
        
        # Параметры генерации
        ragas_config = self.config.get("ragas", {})
        testset_size = ragas_config.get("testset_size", 50)
        num_workers = ragas_config.get("num_workers", 4)
        distribution = ragas_config.get("distribution", None)
        
        print(f"Генерация тестового набора данных...")
        print(f"Размер набора: {testset_size}")
        print(f"Количество воркеров: {num_workers}")
        
        # Генерируем тестовый набор
        if distribution:
            dataset = self.generator.generate_with_langchain_docs(
                documents,
                testset_size=testset_size,
                num_workers=num_workers,
                distribution=distribution,
            )
        else:
            dataset = self.generator.generate_with_langchain_docs(
                documents,
                testset_size=testset_size,
                num_workers=num_workers,
            )
        
        print(f"Сгенерировано примеров: {len(dataset)}")
        return dataset
    
    def save(self, dataset: Any, output_path: Optional[str] = None) -> str:
        """
        Сохраняет датасет в файл
        
        Args:
            dataset: RAGAS Dataset объект
            output_path: Путь для сохранения (опционально)
            
        Returns:
            Путь к сохраненному файлу
        """
        output_config = self.config.get("output", {})
        
        if not output_path:
            dataset_path = output_config.get("dataset_path", "./datasets")
            os.makedirs(dataset_path, exist_ok=True)
            
            # Формируем имя файла с временной меткой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = self.config.get("input", {}).get("base_name", "dataset")
            output_format = output_config.get("format", "json")
            
            output_path = os.path.join(
                dataset_path,
                f"{base_name}_ragas_dataset_{timestamp}.{output_format}"
            )
        
        # Сохраняем в зависимости от формата
        if output_path.endswith('.json'):
            dataset.to_pandas().to_json(output_path, orient='records', force_ascii=False, indent=2)
        elif output_path.endswith('.csv'):
            dataset.to_pandas().to_csv(output_path, index=False, encoding='utf-8')
        elif output_path.endswith('.parquet'):
            dataset.to_pandas().to_parquet(output_path, index=False)
        else:
            # По умолчанию JSON
            output_path = output_path + '.json'
            dataset.to_pandas().to_json(output_path, orient='records', force_ascii=False, indent=2)
        
        print(f"Датасет сохранен: {output_path}")
        return output_path
    
    def build_and_save(self, output_path: Optional[str] = None) -> str:
        """
        Генерирует и сохраняет датасет
        
        Args:
            output_path: Путь для сохранения (опционально)
            
        Returns:
            Путь к сохраненному файлу
        """
        dataset = self.build()
        return self.save(dataset, output_path)

