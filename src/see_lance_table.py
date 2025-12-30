import lancedb
from pathlib import Path
import polars as pl
import pandas as pd


lance_db_path = Path("data/lance_db_test")
lance_table_name = "books_test_table"
print(f"Opened LanceDB table '{lance_table_name}' from database at '{lance_db_path}'")

open_table = lancedb.connect(lance_db_path).open_table(lance_table_name)
print(f"Table name: {open_table.name}")
print("Columns:")
print(open_table.schema)

print(open_table.count_rows())
print(open_table)

pandas_table = open_table.to_pandas()
print(pandas_table.head())