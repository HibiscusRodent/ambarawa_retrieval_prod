import lancedb
from pathlib import Path

from image_processors import ImageProcessors, BookFolderPathData
from baml_client.sync_client import b
from baml_client.types import BookConditionData


uri = "lance_db_test"
db = lancedb.connect(uri)

# data paths
book_folder_path = r"sample_data/rak-0003_baris-005_buku-30"

ip = ImageProcessors()
folder_data = BookFolderPathData(path=Path(book_folder_path))
images_data = ip.process_book_folder(folder_data=folder_data)
baml_images = images_data.baml_images


bookConditionData = b.GetBookConditionData(
    MultiImages = baml_images,
    bookId = images_data.book_id
)

