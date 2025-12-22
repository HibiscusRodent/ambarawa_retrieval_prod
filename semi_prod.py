import os

import lancedb
import pydantic as pydantic
import pyarrow as pa

from pydantic_to_pyarrow import get_pyarrow_schema
from image_processors import ImageProcessors, BookFolderPathData

from baml_client.sync_client import b
from baml_client.types import BookConditionData, BookContentHints, BookMainData, BookPubAndDistDetails, RawAnalysis

from dotenv import load_dotenv
env_loader = load_dotenv()

sample_book_folder_path =  "sample_data/rak-0003_baris-005_buku-30"

# the data will be saved into this folder path in the form of images, and json files
output_folder_path = "data/output_book_data"
os.makedirs(output_folder_path, exist_ok=True)

# Rebuild models to resolve forward references before converting to PyArrow schemas
BookConditionData.model_rebuild()
BookMainData.model_rebuild()
BookPubAndDistDetails.model_rebuild()

# initialize the necessary configs for lancedb's tables
## turn each of the individual data models into arrow schemas
raw_analysis_pa_schema = get_pyarrow_schema(RawAnalysis)
book_condition_data_pa_schema = get_pyarrow_schema(BookConditionData)
book_content_hints_pa_schema = get_pyarrow_schema(BookContentHints)
book_main_data_pa_schema = get_pyarrow_schema(BookMainData)
book_pub_and_dist_details_pa_schema = get_pyarrow_schema(BookPubAndDistDetails)

## convert schemas to struct types for nesting
raw_analysis_struct = pa.struct([(field.name, field.type) for field in raw_analysis_pa_schema])
book_condition_data_struct = pa.struct([(field.name, field.type) for field in book_condition_data_pa_schema])
book_content_hints_struct = pa.struct([(field.name, field.type) for field in book_content_hints_pa_schema])
book_main_data_struct = pa.struct([(field.name, field.type) for field in book_main_data_pa_schema])
book_pub_and_dist_details_struct = pa.struct([(field.name, field.type) for field in book_pub_and_dist_details_pa_schema])

## compile them into a full arrow schema
full_data_model_pa_schema = pa.schema([
    ("book_id", pa.string()),
    ("images_data", pa.list_(pa.binary())),
    ("raw_analysis", raw_analysis_struct),
    ("book_condition_data", book_condition_data_struct),
    ("book_content_hints", book_content_hints_struct),
    ("book_main_data", book_main_data_struct),
    ("book_pub_and_dist_details", book_pub_and_dist_details_struct)
])

## initialized the local lancedb connection
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

# data to be ingested into the lance db
data_to_ingest = {
    "book_id": book_id,
    "images_data": binary_images,
    "raw_analysis": bookRawAnalysis.model_dump(),
    "book_condition_data": book_condition_data.model_dump(),
    "book_main_data": book_main_data.model_dump()
}

