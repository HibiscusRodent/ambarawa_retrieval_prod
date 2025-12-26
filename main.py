import inferenceFunctions as inf
import asyncio
from prefect import task, flow


book_folder_paths = ["sample_data/rak-0018_baris-002_buku-12", "sample_data/rak-0003_baris-005_buku-30"]
output_folder_path = "data/output_book_data"
lance_db_uri = "data/test/lance_db_semi_prod"
table_name = "active_table_lots_columns"


def run_single_inference(
    book_folder_path: str,
    output_folder_path: str,
    lance_db_uri: str,
    table_name: str,
    ) -> None:
    """
    Run inference on a single book and store results in LanceDB.
    """
    
    inf.configure_environment()
    asyncio.run(
        inf.process_one_book_flow(
            book_folder_path=book_folder_path,
            output_folder_path=output_folder_path,
            lance_db_uri=lance_db_uri,
            table_name=table_name,
            )
        )
    return None

def main_inference_multiple_books(
    book_folder_paths: list[str],
    output_folder_path: str,
    lance_db_uri: str,
    table_name: str,
    ) -> None:
    """
    Run inference on multiple books and store results in LanceDB.
    """
    for book_folder_path in book_folder_paths:
        run_single_inference(
            book_folder_path=book_folder_path,
            output_folder_path=output_folder_path,
            lance_db_uri=lance_db_uri,
            table_name=table_name,
            )
    return None

main_inference_multiple_books(
    book_folder_paths=book_folder_paths,
    output_folder_path=output_folder_path,
    lance_db_uri=lance_db_uri,
    table_name=table_name,
)

