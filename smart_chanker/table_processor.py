"""
Модуль для обработки таблиц из DOCX файлов
"""

import os
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from zipfile import ZipFile

from lxml import etree

WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
NSMAP = {"w": WORD_NAMESPACE}


@dataclass
class DocxTableCell:
    text: str
    row: int
    col: int
    rowspan: int
    colspan: int


@dataclass
class ParsedDocxTable:
    grid: List[List[Optional[DocxTableCell]]]
    rows: int
    cols: int


class TableProcessorError(Exception):
    """Базовое исключение для ошибок обработки таблиц"""
    pass


class TableExtractionError(TableProcessorError):
    """Ошибка при извлечении таблиц из DOCX"""
    pass


class TableParsingError(TableProcessorError):
    """Ошибка при парсинге таблицы"""
    pass


class TableConversionError(TableProcessorError):
    """Ошибка при конвертации таблицы в JSON"""
    pass


class TableProcessor:
    """Класс для обработки таблиц из DOCX файлов"""
    
    def extract_docx_tables(self, file_path: str) -> List[ParsedDocxTable]:
        """
        Извлекает таблицы напрямую из DOCX с сохранением структуры объединений
        
        Args:
            file_path: Путь к DOCX файлу
            
        Returns:
            Список распарсенных таблиц
            
        Raises:
            TableExtractionError: Если не удалось извлечь таблицы
        """
        if not os.path.exists(file_path):
            raise TableExtractionError(f"Файл не найден: {file_path}")
        
        try:
            with ZipFile(file_path) as docx_zip:
                document_bytes = docx_zip.read("word/document.xml")
            root = etree.fromstring(document_bytes)
        except Exception as exc:
            raise TableExtractionError(f"Не удалось извлечь таблицы из DOCX: {exc}") from exc

        tables: List[ParsedDocxTable] = []
        for tbl in root.findall(".//w:tbl", namespaces=NSMAP):
            parsed = self.parse_docx_table(tbl)
            if parsed:
                tables.append(parsed)
        
        return tables

    def parse_docx_table(self, table_element) -> Optional[ParsedDocxTable]:
        """
        Преобразует XML-таблицу в сетку ячеек с учетом объединений
        
        Args:
            table_element: XML элемент таблицы (w:tbl)
            
        Returns:
            Распарсенная таблица или None, если таблица пустая
        """
        rows_raw: List[List[Dict[str, Any]]] = []
        column_map: List[Dict[int, Dict[str, Any]]] = []
        max_cols = 0

        for row_idx, tr in enumerate(table_element.findall("w:tr", namespaces=NSMAP)):
            row_cells: List[Dict[str, Any]] = []
            cell_index_map: Dict[int, Dict[str, Any]] = {}
            current_col = 0

            for tc in tr.findall("w:tc", namespaces=NSMAP):
                text = self.get_table_cell_text(tc)
                tc_props = tc.find("w:tcPr", namespaces=NSMAP)
                colspan = 1
                if tc_props is not None:
                    grid_span = tc_props.find("w:gridSpan", namespaces=NSMAP)
                    if grid_span is not None:
                        val = grid_span.get(f"{{{WORD_NAMESPACE}}}val")
                        if val and val.isdigit():
                            colspan = int(val)
                vmerge_state = None
                if tc_props is not None:
                    vmerge = tc_props.find("w:vMerge", namespaces=NSMAP)
                    if vmerge is not None:
                        merge_val = vmerge.get(f"{{{WORD_NAMESPACE}}}val")
                        vmerge_state = "restart" if merge_val == "restart" else "continue"

                cell_info = {
                    "text": text.strip(),
                    "colspan": colspan,
                    "vmerge": vmerge_state,
                    "start_col": current_col,
                }
                row_cells.append(cell_info)
                cell_index_map[current_col] = cell_info
                current_col += colspan

            max_cols = max(max_cols, current_col)
            rows_raw.append(row_cells)
            column_map.append(cell_index_map)

        if max_cols == 0 or not rows_raw:
            return None

        row_count = len(rows_raw)
        grid: List[List[Optional[DocxTableCell]]] = [
            [None for _ in range(max_cols)] for _ in range(row_count)
        ]

        for row_idx, row in enumerate(rows_raw):
            for cell in row:
                start_col = cell["start_col"]
                colspan = cell["colspan"]
                if cell.get("vmerge") == "continue":
                    continue

                rowspan = 1
                next_row = row_idx + 1
                while next_row < row_count:
                    next_cell = column_map[next_row].get(start_col)
                    if next_cell and next_cell.get("vmerge") == "continue":
                        rowspan += 1
                        next_row += 1
                    else:
                        break

                table_cell = DocxTableCell(
                    text=cell["text"],
                    row=row_idx,
                    col=start_col,
                    rowspan=rowspan,
                    colspan=colspan,
                )

                for r in range(row_idx, row_idx + rowspan):
                    for c in range(start_col, start_col + colspan):
                        grid[r][c] = table_cell

        return ParsedDocxTable(grid=grid, rows=row_count, cols=max_cols)

    def get_table_cell_text(self, cell_element) -> str:
        """
        Извлекает текст из ячейки DOCX-таблицы
        
        Args:
            cell_element: XML элемент ячейки (w:tc)
            
        Returns:
            Текст ячейки
        """
        texts = cell_element.findall(".//w:t", namespaces=NSMAP)
        if not texts:
            return ""
        return "".join(t.text or "" for t in texts)
    
    def docx_table_to_json(self, docx_table: ParsedDocxTable, table_name: str) -> str:
        """
        Конвертация таблицы, извлеченной из DOCX, в JSON структуру фактов
        
        Args:
            docx_table: Распарсенная таблица
            table_name: Название таблицы
            
        Returns:
            JSON строка с описанием таблицы
            
        Raises:
            TableConversionError: Если не удалось конвертировать таблицу
        """
        import json
        
        if not docx_table:
            raise TableConversionError("Таблица не может быть None")
        
        grid = docx_table.grid
        if not grid:
            raise TableConversionError("Сетка таблицы пуста")

        try:
            analysis = self.analyze_docx_table_structure(docx_table)
            row_attribute_rows = analysis["row_attribute_rows"]
            column_attribute_columns = analysis["column_attribute_columns"]
            global_attrs_by_row = analysis["global_attrs_by_row"]

            # Группируем факты по строкам (items)
            items: List[Dict[str, Any]] = []
            
            for row_idx in range(docx_table.rows):
                if row_idx in row_attribute_rows:
                    continue
                
                # Собираем факты для текущей строки
                row_facts: List[Dict[str, Any]] = []
                item_name: Optional[str] = None
                
                # Определяем item_name из колонки-атрибута строки
                # Ищем в колонках-атрибутах строки (column_attribute_columns) справа налево
                # item_name обычно находится в последней колонке-атрибуте строки
                for col_idx in sorted(column_attribute_columns, reverse=True):
                    cell = grid[row_idx][col_idx]
                    if cell and cell.text and cell.text.strip():
                        item_name = cell.text.strip()
                        break
                
                # Если не нашли в колонках-атрибутах, ищем в первой колонке данных строки
                # (для случаев, когда нет колонок-атрибутов)
                if not item_name:
                    for col_idx in range(docx_table.cols):
                        if col_idx in column_attribute_columns:
                            continue
                        cell = grid[row_idx][col_idx]
                        if cell and cell.row == row_idx and cell.col == col_idx:
                            if cell.text and cell.text.strip():
                                item_name = cell.text.strip()
                                break
                        if item_name:
                            break
                
                # Если item_name не найден, пропускаем строку
                if not item_name:
                    continue
                
                # Собираем факты для всех колонок данных этой строки
                for col_idx in range(docx_table.cols):
                    if col_idx in column_attribute_columns:
                        continue
                    cell = grid[row_idx][col_idx]
                    if not cell or cell.row != row_idx or cell.col != col_idx:
                        continue
                    
                    # Пропускаем ячейки-атрибуты (объединенные ячейки)
                    if cell.rowspan > 1 or cell.colspan > 1:
                        continue
                    
                    cell_text = cell.text.strip()

                    # Собираем атрибуты (без item_name)
                    attributes: List[str] = []
                    attributes.extend(global_attrs_by_row.get(row_idx, []))
                    attributes.extend(
                        self.collect_column_header_chain(
                            grid, row_idx, col_idx, row_attribute_rows
                        )
                    )
                    # Собираем заголовки строк из колонок-атрибутов (но исключаем item_name)
                    row_header_chain = self.collect_row_header_chain(
                        grid, row_idx, col_idx, column_attribute_columns
                    )
                    # Исключаем item_name из цепочки заголовков строк
                    for attr in row_header_chain:
                        if attr != item_name:
                            attributes.append(attr)
                    
                    attributes.extend(
                        self.collect_attribute_row_values(
                            grid, row_idx, col_idx, row_attribute_rows
                        )
                    )
                    attributes.extend(
                        self.collect_attribute_column_values(
                            grid, row_idx, col_idx, column_attribute_columns
                        )
                    )

                    # Удаляем дубликаты и пустые значения
                    deduped: List[str] = []
                    seen = set()
                    for attr in attributes:
                        if attr and attr not in seen and attr != item_name:
                            seen.add(attr)
                            deduped.append(attr)

                    # Создаем факт в формате table2.json: attributes, value, col
                    row_facts.append({
                        "attributes": deduped,
                        "value": cell_text,
                        "col": col_idx + 1  # col начинается с 1 (как в table2.json)
                    })
                
                # Добавляем item только если есть факты
                if row_facts:
                    items.append({
                        "item_name": item_name,
                        "row": row_idx + 1,  # row начинается с 1 (как в table2.json)
                        "facts": row_facts
                    })

            if not table_name:
                raise TableConversionError("Название таблицы не может быть пустым")

            table_data = {
                "table_name": table_name,
                "items": items,
            }
            json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
            return f"```json\n{json_str}\n```"
        except Exception as e:
            raise TableConversionError(f"Ошибка конвертации таблицы: {e}") from e
    
    def docx_table_to_chunks(
        self, 
        docx_table: ParsedDocxTable, 
        table_name: str, 
        max_chunk_size: int = 1000
    ) -> List[str]:
        """
        Конвертация таблицы в список чанков с группировкой по items
        В чанк попадает целое число элементов items, кроме случаев, когда длина одного item превышает размер чанка
        
        Args:
            docx_table: Распарсенная таблица
            table_name: Название таблицы
            max_chunk_size: Максимальный размер чанка в символах
            
        Returns:
            Список JSON строк с чанками таблицы в формате table2.json
            
        Raises:
            TableConversionError: Если не удалось конвертировать таблицу
        """
        import json
        
        if not docx_table:
            raise TableConversionError("Таблица не может быть None")
        
        grid = docx_table.grid
        if not grid:
            raise TableConversionError("Сетка таблицы пуста")

        try:
            analysis = self.analyze_docx_table_structure(docx_table)
            row_attribute_rows = analysis["row_attribute_rows"]
            column_attribute_columns = analysis["column_attribute_columns"]
            global_attrs_by_row = analysis["global_attrs_by_row"]

            # Группируем факты по строкам (items) - используем ту же логику, что и в docx_table_to_json
            items: List[Dict[str, Any]] = []
            
            for row_idx in range(docx_table.rows):
                if row_idx in row_attribute_rows:
                    continue
                
                # Собираем факты для текущей строки
                row_facts: List[Dict[str, Any]] = []
                item_name: Optional[str] = None
                
                # Определяем item_name из колонки-атрибута строки
                # Ищем в колонках-атрибутах строки (column_attribute_columns) справа налево
                # item_name обычно находится в последней колонке-атрибуте строки
                for col_idx in sorted(column_attribute_columns, reverse=True):
                    cell = grid[row_idx][col_idx]
                    if cell and cell.text and cell.text.strip():
                        item_name = cell.text.strip()
                        break
                
                # Если не нашли в колонках-атрибутах, ищем в первой колонке данных строки
                # (для случаев, когда нет колонок-атрибутов)
                if not item_name:
                    for col_idx in range(docx_table.cols):
                        if col_idx in column_attribute_columns:
                            continue
                        cell = grid[row_idx][col_idx]
                        if cell and cell.row == row_idx and cell.col == col_idx:
                            if cell.text and cell.text.strip():
                                item_name = cell.text.strip()
                                break
                        if item_name:
                            break
                
                # Если item_name не найден, пропускаем строку
                if not item_name:
                    continue
                
                # Собираем факты для всех колонок данных этой строки
                for col_idx in range(docx_table.cols):
                    if col_idx in column_attribute_columns:
                        continue
                    cell = grid[row_idx][col_idx]
                    if not cell or cell.row != row_idx or cell.col != col_idx:
                        continue
                    
                    # Пропускаем ячейки-атрибуты (объединенные ячейки)
                    if cell.rowspan > 1 or cell.colspan > 1:
                        continue
                    
                    cell_text = cell.text.strip()

                    # Собираем атрибуты (без item_name)
                    attributes: List[str] = []
                    attributes.extend(global_attrs_by_row.get(row_idx, []))
                    attributes.extend(
                        self.collect_column_header_chain(
                            grid, row_idx, col_idx, row_attribute_rows
                        )
                    )
                    # Собираем заголовки строк из колонок-атрибутов (но исключаем item_name)
                    row_header_chain = self.collect_row_header_chain(
                        grid, row_idx, col_idx, column_attribute_columns
                    )
                    # Исключаем item_name из цепочки заголовков строк
                    for attr in row_header_chain:
                        if attr != item_name:
                            attributes.append(attr)
                    
                    attributes.extend(
                        self.collect_attribute_row_values(
                            grid, row_idx, col_idx, row_attribute_rows
                        )
                    )
                    attributes.extend(
                        self.collect_attribute_column_values(
                            grid, row_idx, col_idx, column_attribute_columns
                        )
                    )

                    # Удаляем дубликаты и пустые значения
                    deduped: List[str] = []
                    seen = set()
                    for attr in attributes:
                        if attr and attr not in seen and attr != item_name:
                            seen.add(attr)
                            deduped.append(attr)

                    # Создаем факт в формате table2.json: attributes, value, col
                    row_facts.append({
                        "attributes": deduped,
                        "value": cell_text,
                        "col": col_idx + 1  # col начинается с 1 (как в table2.json)
                    })
                
                # Добавляем item только если есть факты
                if row_facts:
                    items.append({
                        "item_name": item_name,
                        "row": row_idx + 1,  # row начинается с 1 (как в table2.json)
                        "facts": row_facts
                    })

            if not table_name:
                raise TableConversionError("Название таблицы не может быть пустым")

            # Чанкуем items целиком
            chunks = self._chunk_table_items(items, table_name, max_chunk_size)
            return chunks
        except Exception as e:
            raise TableConversionError(f"Ошибка конвертации таблицы: {e}") from e
    
    def _chunk_table_items(
        self, 
        items: List[Dict[str, Any]], 
        table_name: str, 
        max_chunk_size: int
    ) -> List[str]:
        """
        Разбивает items таблицы на чанки с учетом максимального размера
        В чанк попадает целое число элементов items, кроме случаев, когда длина одного item превышает размер чанка
        
        Args:
            items: Список items таблицы (в формате table2.json)
            table_name: Название таблицы
            max_chunk_size: Максимальный размер чанка в символах
            
        Returns:
            Список JSON строк с чанками в формате table2.json
        """
        import json
        
        if not items:
            # Если items нет, возвращаем один чанк с пустым списком
            table_data = {
                "table_name": table_name,
                "items": [],
            }
            json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
            return [f"```json\n{json_str}\n```"]
        
        chunks: List[str] = []
        current_chunk_items: List[Dict[str, Any]] = []
        current_size = 0
        
        # Размер названия таблицы (включая структуру JSON)
        table_name_overhead = len(f'{{"table_name": "{table_name}", "items": []}}')
        
        for item in items:
            # Оцениваем размер item в JSON
            item_json = json.dumps(item, ensure_ascii=False)
            item_size = len(item_json) + 2  # +2 для запятой и переноса строки
            
            # Если размер одного item превышает max_chunk_size, он все равно попадает в чанк
            # (единственный item в чанке)
            if item_size + table_name_overhead > max_chunk_size:
                # Сохраняем текущий чанк, если есть items
                if current_chunk_items:
                    table_data = {
                        "table_name": table_name,
                        "items": current_chunk_items,
                    }
                    json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
                    chunks.append(f"```json\n{json_str}\n```")
                    current_chunk_items = []
                    current_size = 0
                
                # Добавляем большой item в отдельный чанк
                table_data = {
                    "table_name": table_name,
                    "items": [item],
                }
                json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
                chunks.append(f"```json\n{json_str}\n```")
                continue
            
            # Если добавление item превысит лимит, сохраняем текущий чанк
            if current_chunk_items and current_size + item_size + table_name_overhead > max_chunk_size:
                table_data = {
                    "table_name": table_name,
                    "items": current_chunk_items,
                }
                json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
                chunks.append(f"```json\n{json_str}\n```")
                current_chunk_items = []
                current_size = 0
            
            # Добавляем item в текущий чанк
            current_chunk_items.append(item)
            current_size += item_size
        
        # Добавляем последний чанк, если есть items
        if current_chunk_items:
            table_data = {
                "table_name": table_name,
                "items": current_chunk_items,
            }
            json_str = json.dumps(table_data, ensure_ascii=False, indent=2)
            chunks.append(f"```json\n{json_str}\n```")
        
        return chunks

    def analyze_docx_table_structure(self, table: ParsedDocxTable) -> Dict[str, Any]:
        """
        Анализ таблицы для определения строк/колонок, содержащих атрибуты
        
        Args:
            table: Распарсенная таблица
            
        Returns:
            Словарь с информацией о структуре таблицы
        """
        row_attribute_rows: set[int] = set()
        column_attribute_columns: set[int] = set()
        global_attrs_by_row: Dict[int, List[str]] = {}
        active_global_attrs: List[str] = []

        for row_idx in range(table.rows):
            unique_cells = self.unique_row_cells(table.grid[row_idx])
            non_empty = [c for c in unique_cells if c.text]

            full_row_merge = any(
                c.col == 0 and c.colspan >= table.cols and c.text for c in unique_cells
            )

            only_left_nonempty = False
            if non_empty:
                first = min(non_empty, key=lambda c: c.col)
                if first.col == 0:
                    others = any(c.text for c in non_empty if c is not first)
                    only_left_nonempty = not others

            if only_left_nonempty:
                active_global_attrs = [non_empty[0].text] if non_empty else []
            elif full_row_merge and non_empty:
                active_global_attrs = [non_empty[0].text]

            global_attrs_by_row[row_idx] = list(active_global_attrs)

            has_partial_merge = any(
                c.colspan > 1 and c.colspan < table.cols for c in unique_cells
            )
            if has_partial_merge and not full_row_merge and row_idx + 1 < table.rows:
                row_attribute_rows.add(row_idx + 1)

        for col_idx in range(table.cols - 1):
            for row_idx in range(table.rows):
                cell = table.grid[row_idx][col_idx]
                if (
                    cell
                    and cell.col == col_idx
                    and cell.row == row_idx
                    and cell.rowspan > 1
                ):
                    column_attribute_columns.add(col_idx + 1)
                    break

        return {
            "row_attribute_rows": row_attribute_rows,
            "column_attribute_columns": column_attribute_columns,
            "global_attrs_by_row": global_attrs_by_row,
        }

    def collect_column_header_chain(
        self,
        grid: List[List[Optional[DocxTableCell]]],
        row_idx: int,
        col_idx: int,
        row_attribute_rows: set[int],
    ) -> List[str]:
        """
        Собирает цепочку заголовков столбцов сверху вниз
        Собирает только ячейки-атрибуты (объединенные по горизонтали или в строках-атрибутах)
        
        Args:
            grid: Сетка ячеек таблицы
            row_idx: Индекс строки
            col_idx: Индекс колонки
            row_attribute_rows: Множество индексов строк-атрибутов
            
        Returns:
            Список атрибутов столбцов
        """
        attributes: List[str] = []
        seen: set[tuple[int, int]] = set()
        for r in range(row_idx - 1, -1, -1):
            cell = grid[r][col_idx]
            if not cell or not cell.text:
                continue
            # Собираем только ячейки-атрибуты:
            # - объединенные по горизонтали (colspan > 1)
            # - или находящиеся в строках-атрибутах
            # НЕ собираем обычные ячейки-значения
            if cell.colspan == 1 and r not in row_attribute_rows:
                continue
            key = (cell.row, cell.col)
            if key in seen:
                continue
            attributes.insert(0, cell.text)
            seen.add(key)
        return attributes

    def collect_row_header_chain(
        self,
        grid: List[List[Optional[DocxTableCell]]],
        row_idx: int,
        col_idx: int,
        column_attribute_columns: set[int],
    ) -> List[str]:
        """
        Собирает цепочку заголовков строк слева направо
        Собирает только ячейки-атрибуты (объединенные по вертикали или в колонках-атрибутах)
        
        Args:
            grid: Сетка ячеек таблицы
            row_idx: Индекс строки
            col_idx: Индекс колонки
            column_attribute_columns: Множество индексов колонок-атрибутов
            
        Returns:
            Список атрибутов строк
        """
        attributes: List[str] = []
        seen: set[tuple[int, int]] = set()
        for c in range(col_idx - 1, -1, -1):
            cell = grid[row_idx][c]
            if not cell or not cell.text:
                continue
            # Собираем только ячейки-атрибуты:
            # - объединенные по вертикали (rowspan > 1)
            # - или находящиеся в колонках-атрибутах
            # НЕ собираем обычные ячейки-значения
            if cell.rowspan == 1 and c not in column_attribute_columns:
                continue
            key = (cell.row, cell.col)
            if key not in seen:
                attributes.append(cell.text)
                seen.add(key)
        return attributes

    def collect_attribute_row_values(
        self,
        grid: List[List[Optional[DocxTableCell]]],
        row_idx: int,
        col_idx: int,
        attribute_rows: set[int],
    ) -> List[str]:
        """
        Собирает значения из строк-атрибутов
        
        Args:
            grid: Сетка ячеек таблицы
            row_idx: Индекс строки
            col_idx: Индекс колонки
            attribute_rows: Множество индексов строк-атрибутов
            
        Returns:
            Список значений атрибутов из строк
        """
        for r in range(row_idx - 1, -1, -1):
            if r in attribute_rows:
                cell = grid[r][col_idx]
                if cell and cell.text:
                    return [cell.text]
                break
        return []

    def collect_attribute_column_values(
        self,
        grid: List[List[Optional[DocxTableCell]]],
        row_idx: int,
        col_idx: int,
        attribute_columns: set[int],
    ) -> List[str]:
        """
        Собирает значения из колонок-атрибутов
        
        Args:
            grid: Сетка ячеек таблицы
            row_idx: Индекс строки
            col_idx: Индекс колонки
            attribute_columns: Множество индексов колонок-атрибутов
            
        Returns:
            Список значений атрибутов из колонок
        """
        for c in range(col_idx - 1, -1, -1):
            if c in attribute_columns:
                cell = grid[row_idx][c]
                if cell and cell.text:
                    return [cell.text]
                break
        return []

    def unique_row_cells(self, row: List[Optional[DocxTableCell]]) -> List[DocxTableCell]:
        """
        Возвращает уникальные ячейки строки (без дублей от объединений)
        
        Args:
            row: Строка ячеек
            
        Returns:
            Список уникальных ячеек, отсортированных по колонке
        """
        unique_cells: List[DocxTableCell] = []
        seen: set[tuple[int, int]] = set()
        for cell in row:
            if cell is None:
                continue
            key = (cell.row, cell.col)
            if key in seen:
                continue
            seen.add(key)
            unique_cells.append(cell)
        unique_cells.sort(key=lambda c: c.col)
        return unique_cells

