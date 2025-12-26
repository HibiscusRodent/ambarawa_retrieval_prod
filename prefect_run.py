from image_processors import ImageProcessors
import inferenceFunctions as inf
from prefect import flow , task
from pathlib import Path

# Configuration using Path
sample_book_folder_path = Path("sample_data/rak-0018_baris-002_buku-12")
output_folder_path = Path("data/output_book_data")
lance_db_uri = "data/test/lance_db_semi_prod"
table_name = "active_table_lots_columns"

@task
def setup_and_initialize(lance_db_uri: str, sample_book_folder_path: Path):
    inf.configure_environment()
    inf.setup_output_directory(output_folder_path)
    inf.initialize_database(lance_db_uri)
    ip = inf.initialize_image_processor()
    return ip

@task
def image_processing(ip: ImageProcessors, book_folder_path: Path):
    images_data = inf.process_image_folder(ip, str(book_folder_path))
    return images_data

@task
def save_images_locally(images_data, output_root: Path) -> Path:
    return inf.save_images_locally(images_data, output_root)

@flow
def workflow():
    ip = setup_and_initialize(lance_db_uri, sample_book_folder_path)
    images_data = image_processing(ip, sample_book_folder_path)
    save_images_locally(images_data, output_folder_path)
    return None


if __name__ == "__main__":
    workflow()
