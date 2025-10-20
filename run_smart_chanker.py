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
        
        # Полная обработка папки с сохранением только sections/chunks/metadata
        print("Начинаем полную обработку файлов (end-to-end)...")
        result = chunker.run_end_to_end_folder(input_folder, output_folder)
        
        # Выводим краткую статистику
        print(f"\nОбработка завершена!")
        print(f"Всего файлов: {result['summary']['total_files']}")
        print(f"Успешно обработано: {result['summary']['successful']}")
        print(f"Ошибок: {result['summary']['failed']}")
        
        # Показываем информацию о обработанных файлах
        if result['processed_files']:
            print(f"\nОбработанные файлы:")
            for file_info in result['processed_files']:
                print(f"  - {os.path.basename(file_info['file_path'])}")
        
        # Показываем ошибки, если есть
        if result['errors']:
            print(f"\nОшибки:")
            for error in result['errors']:
                print(f"  - {os.path.basename(error['file'])}: {error['error']}")
        
        # Итоговые hierarchical.json файлы уже сохранены по одному на документ
        
        return result
        
    except Exception as e:
        print(f"Ошибка при выполнении: {e}")
        return None

if __name__ == "__main__":
    main()
