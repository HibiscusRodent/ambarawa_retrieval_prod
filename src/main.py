import single_book_flow as single_inf
from single_book_flow import InitializedEnvironment
from prefect import task, flow
from prefect.cache_policies import NO_CACHE
from pathlib import Path




book_folder = Path("sample_data")
# retrieve all subfolders in the book_folder
book_folder_paths = [str(folder) for folder in book_folder.iterdir() if folder.is_dir()]
print(f"Found {len(book_folder_paths)} book folders for inference.")

output_folder_path = "data/output_book_data"
lance_db_uri = Path("data/test/lance_db_semi_prod")
table_name = "pararel_test_new"

setup_instance = single_inf.setup_phase_flow(lance_db_uri, table_name)


@task(cache_policy=NO_CACHE)
def run_single_inference(
    setup_instance: InitializedEnvironment,
    book_folder_path: str,
    output_folder_path: str,
) -> None:
    """
    Run inference on a single book and store results in LanceDB.

    Args:
        setup_instance: Initialized environment containing image processors and LanceDB connection.
        book_folder_path: Path to the folder containing book images.
        output_folder_path: Path where output data will be saved.
    """
    single_inf.single_book_flow(setup_instance, book_folder_path, output_folder_path)
    return None


@flow
def main_inference_multiple_books(
    book_folder_paths: list[str],
    output_folder_path: str,
    batch_size: int = 5,
) -> None:
    """
    Run inference on multiple books in parallel batches and store results in LanceDB.
    
    Args:
        book_folder_paths: List of paths to book folders.
        output_folder_path: Path where output data will be saved.
        batch_size: Number of books to process in parallel at once (default: 5).
    """
    # Process books in batches to limit concurrent executions
    for i in range(0, len(book_folder_paths), batch_size):
        batch = book_folder_paths[i:i + batch_size]
        futures = []
        
        # Submit all tasks in the batch for parallel execution
        for book_folder_path in batch:
            future = run_single_inference.submit(
                setup_instance=setup_instance,
                book_folder_path=book_folder_path,
                output_folder_path=output_folder_path,
            )
            futures.append(future)
        
        # Wait for all tasks in the current batch to complete before starting the next batch
        for future in futures:
            future.wait()
    
    return None


main_inference_multiple_books(
    book_folder_paths=book_folder_paths, output_folder_path=output_folder_path
)
