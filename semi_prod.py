import os

import lancedb
import pydantic as pydantic
from pydantic_to_pyarrow import get_pyarrow_schema
from image_processors import ImageProcessors, BookFolderPathData

from baml_client.sync_client import b
from baml_client.types import BookConditionData, BookContentHints, BookMainData, BookPubAndDistDetails, RawAnalysis

sample_book_folder_path =  "sample_data/rak-0003_baris-005_buku-30"

# the data will be saved into this folder path in the form of images, and json files
output_folder_path = "data/output_book_data"
os.makedirs(output_folder_path, exist_ok=True)




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

## initialized the local lancedb connection
uri = "data/lance_db_semi_prod" # or the remote instances hosted by the lancedb cloud
db = lancedb.connect(uri)
active_tbl = db.create_table("active_table", schema=full_data_model_pa_schema) # make sure that the overwrite mode is off to avoid data loss


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

