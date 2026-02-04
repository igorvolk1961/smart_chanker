"""
Пример использования RAGAS Dataset Builder
"""

from dataset_builder import RagasDatasetBuilder


def main():
    """Пример генерации датасета"""
    
    # Создаем билдер с конфигурацией
    builder = RagasDatasetBuilder("config.json")
    
    # Генерируем и сохраняем датасет
    output_path = builder.build_and_save()
    
    print(f"\nДатасет успешно создан: {output_path}")
    
    # Можно также работать с датасетом напрямую
    # dataset = builder.build()
    # df = dataset.to_pandas()
    # print(f"\nСтатистика датасета:")
    # print(f"Всего примеров: {len(df)}")
    # print(f"\nПервые 3 примера:")
    # print(df.head(3))


if __name__ == "__main__":
    main()

