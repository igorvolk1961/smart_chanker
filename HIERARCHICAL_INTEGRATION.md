# Интеграция иерархического чанкинга в SmartChanker

## Обзор

В SmartChanker добавлен новый функционал для иерархического чанкинга документов с многоуровневой нумерацией. Это позволяет создавать семантически корректные чанки по границам разделов.

## Новые методы в SmartChanker

### 1. `parse_hierarchy(text: str) -> List[SectionNode]`
Парсит иерархию из плоского текста с нумерацией.

**Параметры:**
- `text` - плоский текст с нумерацией

**Возвращает:**
- Список корневых узлов иерархии

### 2. `generate_semantic_chunks(text: str, target_level: int = 3, max_chunk_size: int = 1000) -> List[Chunk]`
Генерирует семантические чанки из текста с иерархией.

**Параметры:**
- `text` - плоский текст с нумерацией
- `target_level` - целевой уровень для чанкинга (по умолчанию 3)
- `max_chunk_size` - максимальный размер чанка (по умолчанию 1000)

**Возвращает:**
- Список семантических чанков

### 3. `get_section_context(text: str, section_number: str) -> Dict[str, Any]`
Получает контекст раздела (родитель + дочерние разделы).

**Параметры:**
- `text` - плоский текст с нумерацией
- `section_number` - номер раздела

**Возвращает:**
- Контекст раздела

### 4. `process_with_hierarchical_chunking(text: str, target_level: int = 3, max_chunk_size: int = 1000) -> Dict[str, Any]`
Обрабатывает текст с иерархическим чанкингом.

**Параметры:**
- `text` - плоский текст с нумерацией
- `target_level` - целевой уровень для чанкинга
- `max_chunk_size` - максимальный размер чанка

**Возвращает:**
- Результат обработки с чанками и метаданными

### 5. `get_sections_by_level(text: str, level: int) -> List[SectionNode]`
Получает все разделы заданного уровня.

**Параметры:**
- `text` - плоский текст с нумерацией
- `level` - уровень разделов

**Возвращает:**
- Список разделов заданного уровня

## Конфигурация

В `config.json` добавлена секция `hierarchical_chunking`:

```json
{
  "hierarchical_chunking": {
    "enabled": true,
    "target_level": 3,
    "max_chunk_size": 1000,
    "preserve_lists": true,
    "include_parent_context": true
  }
}
```

**Параметры:**
- `enabled` - включить иерархический чанкинг
- `target_level` - уровень для чанкинга
- `max_chunk_size` - максимальный размер чанка
- `preserve_lists` - сохранять списки целиком
- `include_parent_context` - включать контекст родителя

## Пример использования

```python
from smart_chanker import SmartChanker

# Создаем SmartChanker
chunker = SmartChanker()

# Парсим иерархию
sections = chunker.parse_hierarchy(text)

# Генерируем чанки
chunks = chunker.generate_semantic_chunks(text, target_level=3)

# Получаем контекст раздела
context = chunker.get_section_context(text, "1.1.2")

# Полная обработка
result = chunker.process_with_hierarchical_chunking(text)
```

## Тестирование

Запустите тестовый скрипт:

```bash
python test_smart_chanker_hierarchical.py
```

## Архитектура

Иерархический чанкинг реализован через отдельные модули:
- `hierarchy_parser.py` - парсинг иерархии
- `semantic_chunker.py` - генерация чанков
- `hierarchical_chunker.py` - интеграция

SmartChanker вызывает эти модули через импорты, не содержа их внутри себя.

## Преимущества

1. **Семантическая целостность** - чанки не разрывают смысловые блоки
2. **Контекстная информация** - каждый чанк знает свое место в иерархии
3. **Гибкость** - настраиваемые уровни чанкинга
4. **Интеграция** - работает как часть SmartChanker
5. **RAG-оптимизация** - метаданные для улучшения поиска
