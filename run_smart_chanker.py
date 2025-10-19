"""
Скрипт для запуска SmartChanker с записью результата в файл
"""

import json
import os
from datetime import datetime
from smart_chanker.smart_chanker import SmartChanker

def main():
    """Основная функция запуска SmartChanker"""
    
    # Настройки
    input_folder = "data/input"
    output_folder = "data/output"
    config_file = "config.json"
    
    # Создаем папку для вывода, если её нет
    os.makedirs(output_folder, exist_ok=True)
    
    print(f"Запуск SmartChanker...")
    print(f"Входная папка: {input_folder}")
    print(f"Выходная папка: {output_folder}")
    print(f"Конфигурация: {config_file}")
    print("-" * 50)
    
    try:
        # Инициализируем SmartChanker
        chunker = SmartChanker(config_file)
        
        # Обрабатываем папку
        print("Начинаем обработку файлов...")
        result = chunker.process_folder(input_folder)
        
        # Выводим краткую статистику
        print(f"\nОбработка завершена!")
        print(f"Всего файлов: {result['summary']['total_files']}")
        print(f"Успешно обработано: {result['summary']['successful']}")
        print(f"Ошибок: {result['summary']['failed']}")
        
        # Показываем информацию о обработанных файлах
        if result['processed_files']:
            print(f"\nОбработанные файлы:")
            for file_info in result['processed_files']:
                print(f"  - {os.path.basename(file_info['file_path'])}: {file_info['paragraphs_count']} параграфов")
        
        # Показываем ошибки, если есть
        if result['errors']:
            print(f"\nОшибки:")
            for error in result['errors']:
                print(f"  - {os.path.basename(error['file'])}: {error['error']}")
        
        # Сохраняем результат в JSON файл
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = os.path.join(output_folder, f"processing_result_{timestamp}.json")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        print(f"\nРезультат сохранен в файл: {output_file}")
        
        # Сохраняем обработанный текст для каждого файла
        for file_info in result['processed_files']:
            if 'combined_text' in file_info:
                # Создаем имя файла для текста
                base_name = os.path.splitext(os.path.basename(file_info['file_path']))[0]
                text_file = os.path.join(output_folder, f"{base_name}_processed.txt")
                
                with open(text_file, 'w', encoding='utf-8') as f:
                    f.write(file_info['combined_text'])
                
                print(f"Обработанный текст сохранен: {text_file}")
        
        return result
        
    except Exception as e:
        print(f"Ошибка при выполнении: {e}")
        return None

if __name__ == "__main__":
    main()
