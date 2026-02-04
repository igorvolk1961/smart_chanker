# RAGAS Dataset Builder

Проект для генерации синтетического набора данных для оценки RAG систем с использованием RAGAS.

## Описание

Этот проект использует выходные файлы SmartChanker (`xxx_hierarchical.json` и `xxx_toc.txt`) для создания синтетического тестового набора данных с помощью RAGAS TestsetGenerator.

## Возможности

- Конвертация JSON файлов SmartChanker в LangChain Document объекты
- Генерация синтетических вопросов и ответов с помощью LLM (DeepSeek/Qwen/GLM)
- Создание тестового набора данных для оценки RAG систем
- Экспорт результатов в различные форматы

## Требования

- Python 3.8+
- LLM API ключи (DeepSeek/Qwen/GLM)
- Embedding модель (опционально, для семантического поиска)

## Установка

```bash
pip install -r requirements.txt
```

## Конфигурация

Скопируйте `config.example.json` в `config.json` и заполните необходимые параметры:

```json
{
  "llm": {
    "provider": "deepseek",
    "api_key": "your-api-key",
    "base_url": "https://api.deepseek.com",
    "model": "deepseek-chat"
  },
  "embeddings": {
    "provider": "openai",
    "api_key": "your-api-key"
  },
  "ragas": {
    "testset_size": 50,
    "num_workers": 4
  },
  "input": {
    "output_dir": "../data/output",
    "base_name": "План short"
  },
  "output": {
    "dataset_path": "./datasets",
    "format": "json"
  }
}
```

## Использование

### Базовое использование

```python
from dataset_builder import RagasDatasetBuilder

builder = RagasDatasetBuilder("config.json")
dataset = builder.build()
dataset.save("my_dataset.json")
```

### Из командной строки

```bash
python main.py --config config.json
```

## Структура проекта

```
ragas_dataset_builder/
├── README.md
├── requirements.txt
├── config.example.json
├── main.py
├── dataset_builder.py
├── llm_providers.py
└── datasets/
    └── (сгенерированные датасеты)
```

## Поддерживаемые LLM провайдеры

- **DeepSeek** - DeepSeek API (OpenAI-совместимый)
- **Qwen** - Alibaba Cloud Qwen через OpenAI-совместимый API DashScope
- **GLM** - ZhipuAI GLM API (два режима: официальный SDK или OpenAI-совместимый API)

### Конфигурация для Qwen

Qwen работает через OpenAI-совместимый API. В `config.json` укажите:

```json
{
  "llm": {
    "provider": "qwen",
    "api_key": "your-dashscope-api-key",
    "base_url": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "model": "qwen-turbo"
  }
}
```

**Доступные endpoints:**
- Сингапур: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- Китай (Пекин): `https://dashscope.aliyuncs.com/compatible-mode/v1`

**Доступные модели:** `qwen-max`, `qwen-plus`, `qwen-turbo`, и другие

### Конфигурация для GLM

GLM поддерживает два режима работы:

#### Режим 1: Официальный ZhipuAI API (через SDK)

```json
{
  "llm": {
    "provider": "glm",
    "api_key": "your-zhipuai-api-key",
    "model": "glm-4",
    "temperature": 0.7
  }
}
```

**Требования:** `pip install zhipuai`

#### Режим 2: OpenAI-совместимый API (через сторонние платформы)

```json
{
  "llm": {
    "provider": "glm",
    "api_key": "your-api-key",
    "base_url": "https://api.novita.ai/openai",
    "model": "zai-org/glm-4.7",
    "temperature": 0.7
  }
}
```

**Доступные платформы:**
- Novita AI: `https://api.novita.ai/openai` (модель: `zai-org/glm-4.7`)
- ElkAPI: `https://api.elkapi.com/v1` (модель: `glm-4.5`)

## Лицензия

[Укажите лицензию]

