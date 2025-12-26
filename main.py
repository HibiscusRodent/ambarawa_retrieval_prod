import inferenceFunctions as inf
import asyncio

book_folder_path = "sample_data\\rak-0018_baris-002_buku-12"
inf.configure_environment()

book_folder_path = "sample_data/rak-0018_baris-002_buku-12"
output_folder_path = "data/output_book_data"
lance_db_uri = "data/test/lance_db_semi_prod"
table_name = "active_table_lots_columns"

asyncio.run(
    inf.process_one_book_flow(
        book_folder_path=book_folder_path,
        output_folder_path=output_folder_path,
        lance_db_uri=lance_db_uri,
        table_name=table_name,
    )
)
