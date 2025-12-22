import os

import lancedb
import pydantic as pydantic
import pyarrow as pa
from typing import List, Optional, Any
from pydantic import BaseModel

from image_processors import ImageProcessors, BookFolderPathData

from baml_client.sync_client import b
from baml_client.types import BookConditionData, BookContentHints, BookMainData, BookPubAndDistDetails, RawAnalysis

from dotenv import load_dotenv
env_loader: bool = load_dotenv()

sample_book_folder_path =  "sample_data/rak-0018_baris-002_buku-12"

# the data will be saved into this folder path in the form of images, and json files
output_folder_path = "data/output_book_data"
os.makedirs(output_folder_path, exist_ok=True)

# Rebuild models to resolve forward references
BookConditionData.model_rebuild()
BookMainData.model_rebuild()
BookPubAndDistDetails.model_rebuild()

# Define schema for LanceDB using PyArrow
# Store complex nested structures as JSON strings for simplicity
full_data_model_pa_schema = pa.schema([
    ("book_id", pa.string()),
    ("images_data", pa.list_(pa.binary())),
    ("raw_analysis", pa.string()),  # JSON string
    ("book_condition_data", pa.string()),  # JSON string
    ("book_content_hints", pa.string()),  # JSON string
    ("book_main_data", pa.string()),  # JSON string
    ("book_pub_and_dist_details", pa.string())  # JSON string
])

# initialized the local lancedb connection
uri = "data/lance_db_semi_prod" # or the remote instances hosted by the lancedb cloud
db = lancedb.connect(uri)

# make sure that the overwrite mode is off to avoid data loss
# if the table has not been created yet, uncomment the following line to create it
# active_tbl = db.create_table("active_table", schema=full_data_model_pa_schema)


# initialize the image processors so that it have the necessary config initialized
ip = ImageProcessors()
book_folder = BookFolderPathData(path=sample_book_folder_path)
images_data = ip.process_book_folder(book_folder)

# store the images data in various formats into variables
book_id = images_data.book_id
baml_images = images_data.baml_images
binary_images = images_data.binary_images

# file write operations
## creating a folder for the specific book id
book_output_folder = os.path.join(output_folder_path, book_id)
os.makedirs(book_output_folder, exist_ok=True)

## save the binary images into the output folder path
### first, clear existing images in the folder to ensure overwrite
for filename in os.listdir(book_output_folder):
    file_path = os.path.join(book_output_folder, filename)
    if os.path.isfile(file_path):
        os.unlink(file_path)
        
### write the binary images into the folder
for idx, img_data in enumerate(binary_images):
    img_file_path = os.path.join(book_output_folder, f"{book_id}_img_{idx+1:03d}.jpg")
    with open(img_file_path, "wb") as img_file:
        img_file.write(img_data)

# begin the BAML data processings for book condition data
book_condition_data = b.GetBookConditionData(
    MultiImages=baml_images,
    bookId=book_id
)

# save the BookConditionData as json
book_condition_data_json_path = os.path.join(book_output_folder, f"{book_id}_book_condition_data.json")
with open(book_condition_data_json_path, "w", encoding="utf-8") as json_file:
    json_file.write(book_condition_data.model_dump_json(indent=4, ensure_ascii=False))

bookRawAnalysis = b.GetBookrawVisual(
    MultiImages=baml_images,
    bookId=book_id
)

# save the RawAnalysis as json
raw_analysis_json_path = os.path.join(book_output_folder, f"{book_id}_raw_analysis.json")
with open(raw_analysis_json_path, "w", encoding="utf-8") as json_file:
    json_file.write(bookRawAnalysis.model_dump_json(indent=4, ensure_ascii=False))
    

# get bookContentHints
book_content_hints = b.GetBookContentHints(
    MultiImages=baml_images,
    bookId=book_id,
    RawVisualNote=bookRawAnalysis.model_dump_json()
)

## save the BookContentHints as json
book_content_hints_json_path = os.path.join(book_output_folder, f"{book_id}_book_content_hints.json")
with open(book_content_hints_json_path, "w", encoding="utf-8") as json_file:
    json_file.write(book_content_hints.model_dump_json(indent=4, ensure_ascii=False))


# get bookMainData
book_main_data = b.GetBookMainData(
    MultiImages=baml_images,
    bookId=book_id,
    RawVisualNote=bookRawAnalysis.model_dump_json()
)

# save the BookMainData as json
book_main_data_json_path = os.path.join(book_output_folder, f"{book_id}_book_main_data.json")
with open(book_main_data_json_path, "w", encoding="utf-8") as json_file:
    json_file.write(book_main_data.model_dump_json(indent=4, ensure_ascii=False))
    
    
# get bookPubAndDistDetails
book_pub_and_dist_details = b.GetBookPublisherData(
    MultiImages=baml_images,
    bookId=book_id,
    RawVisualNote=bookRawAnalysis.model_dump_json()
)

## save the BookPubAndDistDetails as json
book_pub_and_dist_details_json_path = os.path.join(book_output_folder, f"{book_id}_book_pub_and_dist_details.json")
with open(book_pub_and_dist_details_json_path, "w", encoding="utf-8") as json_file:
    json_file.write(book_pub_and_dist_details.model_dump_json(indent=4, ensure_ascii=False))

# data to be ingested into the lance db
# Store complex nested models as JSON strings
data_to_ingest = [{
    "book_id": book_id,
    "images_data": binary_images,
    "raw_analysis": bookRawAnalysis.model_dump_json(),
    "book_condition_data": book_condition_data.model_dump_json(),
    "book_content_hints": book_content_hints.model_dump_json(),
    "book_main_data": book_main_data.model_dump_json(),
    "book_pub_and_dist_details": book_pub_and_dist_details.model_dump_json()
}]

print("Adding the data to the LanceDB table...")
active_tbl = db.open_table("active_table")
active_tbl.add(data_to_ingest)

print("Data ingestion completed.")

polars_df = active_tbl.to_polars().lazy().collect()
print(polars_df)
