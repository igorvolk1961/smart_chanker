"""
Основной скрипт для генерации синтетического набора данных RAGAS
"""

import argparse
import sys
from pathlib import Path
from dataset_builder import RagasDatasetBuilder


def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(
        description="Генерация синтетического набора данных для RAGAS"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Путь к файлу конфигурации (по умолчанию: config.json)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Путь для сохранения датасета (опционально)"
    )
    parser.add_argument(
        "--testset-size",
        type=int,
        default=None,
        help="Размер тестового набора (переопределяет config)"
    )
    
    args = parser.parse_args()
    
    try:
        # Создаем билдер
        builder = RagasDatasetBuilder(args.config)
        
        # Переопределяем размер тестового набора, если указан
        if args.testset_size:
            builder.config["ragas"]["testset_size"] = args.testset_size
        
        # Генерируем и сохраняем датасет
        output_path = builder.build_and_save(args.output)
        
        print("\n" + "="*50)
        print("Генерация завершена успешно!")
        print(f"Датасет сохранен: {output_path}")
        print("="*50)
        
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

