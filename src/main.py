import single_book_flow as single_inf
from prefect import task, flow
from pathlib import Path


book_folder_paths = ["sample_data/rak-0018_baris-002_buku-12", "sample_data/rak-0003_baris-005_buku-30"]
output_folder_path = "data/output_book_data"
lance_db_uri = Path("data/test/lance_db_semi_prod")
table_name = "pararel_test_new"

setup_instance = single_inf.setup_phase_flow(lance_db_uri, table_name)


@task
def run_single_inference(
    setup_instance,
    book_folder_path: str,
    ) -> None:
    """
    Run inference on a single book and store results in LanceDB.
    """
    single_inf.single_book_flow(setup_instance, book_folder_path, output_folder_path) 
    return None 

@flow
def main_inference_multiple_books(
    book_folder_paths: list[str],
    output_folder_path: str,
    lance_db_uri: Path,
    table_name: str,
    ) -> None:
    """
    Run inference on multiple books and store results in LanceDB.
    """
    for book_folder_path in book_folder_paths:
        run_single_inference(
            setup_instance = setup_instance,
            book_folder_path = book_folder_path,
            output_folder_path = output_folder_path
            )
    return None

main_inference_multiple_books(
    book_folder_paths=book_folder_paths,
    output_folder_path=output_folder_path
)

