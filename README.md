# SmartChanker

Интеллектуальный инструмент для обработки и чанкинга документов с поддержкой многоуровневой иерархии.

## Описание

SmartChanker - это Python-библиотека для извлечения текста из различных форматов документов (DOCX, PDF, TXT) и создания структурированных чанков с сохранением иерархической структуры документа. Особенно эффективен для работы с техническими документами, содержащими многоуровневую нумерацию.

## Основные возможности

- **Множественные источники данных**: Поддержка DOCX, PDF и TXT файлов
- **Восстановление нумерации**: Автоматическое восстановление многоуровневой нумерации из Word документов
- **Иерархический чанкинг**: Создание чанков с сохранением структуры документа
- **Чанкинг таблиц**: Создание чанков простых таблиц, преобразованных из HTML-представления в JSON
- **Гибкая конфигурация**: Настройка параметров через JSON конфигурацию
- **Логирование**: Подробное логирование процесса обработки

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd smart_chanker
```

2. Создайте виртуальное окружение:
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Требования

- Python 3.8+
- docx2python
- unstructured
- PyPDF2 (опционально)

## Использование

### Базовое использование

```python
from smart_chanker.smart_chanker import SmartChanker

# Инициализация с конфигурацией
chunker = SmartChanker("config.json")

# Обработка одного файла
result = chunker.run_end_to_end("input/document.docx", "output/")

# Обработка папки
result = chunker.run_end_to_end_folder("data/input", "data/output")
```

### Запуск из командной строки

```bash
python run_smart_chanker.py
```

## Конфигурация

Создайте файл `config.json` для настройки параметров:

```json
{
  "table_processing": {
    "max_paragraphs_after_table": 3
  },
  "output": {
    "save_docx2python_text": true,
    "docx2python_text_suffix": "_docx2python.txt"
  },
  "hierarchical_chunking": {
    "enabled": true,
    "target_level": 3,
    "max_chunk_size": 1000
  }
}
```

### Параметры конфигурации

#### `hierarchical_chunking`

- **`enabled`** (bool): Включить иерархический чанкинг
- **`target_level`** (int): Целевой уровень иерархии для создания чанков (по умолчанию: 3)
- **`max_chunk_size`** (int): Максимальный размер чанка в символах (по умолчанию: 1000)

#### `output`

- **`save_docx2python_text`** (bool): Сохранять ли извлеченный текст в отдельный файл
- **`docx2python_text_suffix`** (str): Суффикс для файлов с извлеченным текстом

#### `table_processing`

- **`max_paragraphs_after_table`** (int): Максимальное количество абзацев после таблицы для объединения

## Структура проекта

```
smart_chanker/
├── smart_chanker/
│   ├── __init__.py
│   ├── smart_chanker.py      # Основной класс
│   └── hierarchy_parser.py   # Парсер иерархии
├── data/
│   ├── input/               # Входные файлы
│   └── output/              # Результаты (игнорируется git)
├── config.json              # Конфигурация
├── run_smart_chanker.py     # Скрипт запуска
├── requirements.txt         # Зависимости
└── README.md               # Документация
```

## Особенности работы с нумерацией

SmartChanker автоматически восстанавливает многоуровневую нумерацию из Word документов:

- **Входной формат**: `1)`, `2)`, `3)` с отступами
- **Выходной формат**: `1.`, `1.1.`, `1.1.1.` с правильной иерархией
- **Поддержка табов**: Корректная обработка отступов с табами и пробелами

## Примеры использования

### Обработка технического документа

```python
# Обработка документа с многоуровневой нумерацией
chunker = SmartChanker("config.json")
result = chunker.run_end_to_end(
    "data/input/technical_doc.docx", 
    "data/output/"
)

# Результат: структурированные чанки с сохранением иерархии
```

### Массовая обработка

```python
# Обработка всех документов в папке
chunker = SmartChanker("config.json")
results = chunker.run_end_to_end_folder(
    "data/input/", 
    "data/output/"
)
```

## Логирование

SmartChanker поддерживает детальное логирование:

- **INFO**: Основные этапы обработки
- **DEBUG**: Детальная информация о восстановлении нумерации
- **WARNING**: Предупреждения об ошибках
- **ERROR**: Критические ошибки

## Разработка

### Запуск тестов

```bash
python -m pytest tests/
```

### Форматирование кода

```bash
black smart_chanker/
isort smart_chanker/
```

## Лицензия

[Укажите лицензию проекта]

## Вклад в проект

1. Форкните репозиторий
2. Создайте ветку для новой функции (`git checkout -b feature/amazing-feature`)
3. Зафиксируйте изменения (`git commit -m 'Add amazing feature'`)
4. Отправьте в ветку (`git push origin feature/amazing-feature`)
5. Откройте Pull Request

## Поддержка

Если у вас возникли вопросы или проблемы, создайте issue в репозитории.

## Changelog

### v1.0.0
- Базовая функциональность извлечения текста
- Поддержка DOCX, PDF, TXT
- Восстановление многоуровневой нумерации
- Иерархический чанкинг
- Конфигурируемые параметры
