from polars.selectors import binary
import lancedb
from Pathlib import Path
import pydantic as pydantic
from pydantic_to_pyarrow import get_pyarrow_schema
from image_processors import ImageProcessors, BookFolderPathData

from baml_client.sync_client import b
from baml_client.types import BookConditionData, BookContentHints, BookMainData, BookPubAndDistDetails, RawAnalysis

sample_book_folder_path =  "sample_data/rak-0003_baris-005_buku-30"

uri = "data/lance_db_semi_prod"
db = lancedb.connect(uri)

# initialize the necessary configs for lancedb's tables

## initialize the full data model
class fullDataModel(pydantic.BaseModel):
    book_id: str
    images_data: list[bytes]
    raw_analysis: RawAnalysis
    book_condition_data: BookConditionData
    book_content_hints: BookContentHints
    book_main_data: BookMainData
    book_pub_and_dist_details: BookPubAndDistDetails
    
## turn the pydantic data model into an arrow schema
full_data_model_pa_schema = get_pyarrow_schema(fullDataModel)



# initialize the image processors so that it have the necessary config initialized
ip = ImageProcessors()
book_folder = BookFolderPathData(path=sample_book_folder_path)
images_data = ip.process_book_folder(book_folder)

# store the images data in various formats into variables
book_id = images_data.book_id
baml_images = images_data.baml_images
binary_images = images_data.binary_images

# begin the BAML data processings
book_condition_data = b.GetBookConditionData(
    MultiImages=baml_images,
    bookId=book_id
)

