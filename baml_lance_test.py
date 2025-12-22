import lancedb
from lancedb.pydantic import LanceModel
from pathlib import Path

import pyarrow as pa
from pydantic import BaseModel, PlainSerializer
from pydantic_to_pyarrow import get_pyarrow_schema

from image_processors import ImageProcessors, BookFolderPathData
from baml_client.sync_client import b
from baml_client.types import PhysicalObservation, ConditionAnalysis, PrintTypeAnalysis, BookConditionEnum, BookPrintTypeEnum, BookConditionData

from dotenv import load_dotenv
env_loader = load_dotenv()


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
    
bookConditionData_pa_schema = get_pyarrow_schema(BookConditionData)

# assuming that theb "BookConditionData" table already exists in the database
# if not, you can create it using db.create_table method

table = db.open_table("BookConditionData")
print(table.schema)

table.add(bookConditionData)
    
