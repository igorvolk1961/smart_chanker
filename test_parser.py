"""
Скрипт для тестирования парсинга DOCX файла с unstructured
"""

import os
import json
from pathlib import Path
from unstructured.partition.auto import partition
from unstructured.chunking.title import chunk_by_title

def parse_docx_with_unstructured(file_path):
    """
    Парсинг DOCX файла с помощью unstructured и вывод всех метаданных
    """
    print(f"Парсинг файла: {file_path}")
    
    # Парсинг документа
    elements = partition(file_path)
    
    # Собираем все данные
    parsed_data = {
        "file_path": file_path,
        "total_elements": len(elements),
        "elements": []
    }
    
    # Обрабатываем каждый элемент
    for i, element in enumerate(elements):
        # Обрабатываем метаданные для JSON сериализации
        metadata_dict = {}
        if hasattr(element.metadata, '__dict__'):
            for key, value in element.metadata.__dict__.items():
                if isinstance(value, (str, int, float, bool, list, dict, type(None))):
                    metadata_dict[key] = value
                else:
                    metadata_dict[key] = str(value)
        else:
            metadata_dict = str(element.metadata)
        
        element_data = {
            "index": i,
            "category": element.category,
            "text": element.text,
            "metadata": metadata_dict,
            "element_id": getattr(element, 'element_id', None),
            "coordinates": getattr(element, 'coordinates', None)
        }
        parsed_data["elements"].append(element_data)
    
    # Разбивка на чанки
    chunks = chunk_by_title(elements, max_characters=1000)
    
    parsed_data["chunks"] = []
    for i, chunk in enumerate(chunks):
        chunk_data = {
            "chunk_index": i,
            "text": str(chunk),
            "length": len(str(chunk))
        }
        parsed_data["chunks"].append(chunk_data)
    
    parsed_data["total_chunks"] = len(chunks)
    
    return parsed_data

def main():
    """
    Основная функция
    """
    input_file = "data/input/План строительства.docx"
    output_dir = "data/output"
    
    # Проверяем наличие файла
    if not os.path.exists(input_file):
        print(f"Файл {input_file} не существует")
        return
    
    try:
        # Парсинг файла
        result = parse_docx_with_unstructured(input_file)
        
        # Сохраняем результат в JSON
        output_filename = "parsed_plan_stroitelstva.json"
        output_path = os.path.join(output_dir, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"Результат сохранен в: {output_path}")
        print(f"Найдено элементов: {result['total_elements']}")
        print(f"Создано чанков: {result['total_chunks']}")
        
        # Выводим краткую информацию о найденных элементах
        print("\nТипы найденных элементов:")
        categories = {}
        for element in result['elements']:
            cat = element['category']
            categories[cat] = categories.get(cat, 0) + 1
        
        for cat, count in categories.items():
            print(f"  {cat}: {count}")
        
    except Exception as e:
        print(f"Ошибка при обработке файла: {e}")

if __name__ == "__main__":
    main()
