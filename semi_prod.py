import os

import lancedb
from typing import List, Optional, Any

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

# Initialize the local lancedb connection
uri = "data/lance_db_semi_prod"
db = lancedb.connect(uri)

# Note: Schema will be automatically inferred from the data structure
# No need to manually define PyArrow schema - LanceDB handles nested dicts automatically


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
        
        
## TODO : change the BAML models to use Bahasa Indonesia terms for better localization

# begin the BAML data processings for book condition data
book_condition_data: BookConditionData = b.GetBookConditionData(
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

# Data to be ingested into LanceDB
# Convert Pydantic models to Python dicts - LanceDB will automatically infer nested schema
data_to_ingest = [{
    # organization metadata
    "book_id": book_id,
    "images_data": binary_images,
    
    # main data of the book
    "book_title": book_main_data.model_dump().get("title", []),
    "isbns": book_main_data.model_dump().get("isbns", []), # output ISBN-10 and ISBN-13
    "language_data"
    : {
        "languages": book_main_data.model_dump().get("language", []),
        "scripts": book_main_data.model_dump().get("script", [])
    },
    "authors": book_main_data.model_dump().get("authors", []),
    "translators": book_main_data.model_dump().get("translators", []),
    "published_year": book_pub_and_dist_details.model_dump().get("published_year", None),
    
    ## saved the entire generation data including from the reasoning steps
    "book_main_data": book_main_data.model_dump(),  # Dict, not JSON string
    
    # publisher and distribution details
    "publisher_name" : book_pub_and_dist_details.model_dump().get("publisher_name", []),
    "publisher_location": book_pub_and_dist_details.model_dump().get("publisher_location", []),
    "distributor_name": book_pub_and_dist_details.model_dump().get("distributor_name", []),
    "distributor_location": book_pub_and_dist_details.model_dump().get("distributor_location", []),

    ## saved the entire generation data including from the reasoning steps
    "book_pub_and_dist_details": book_pub_and_dist_details.model_dump(),  # Dict, not JSON string
    
    # book condition data
    "book_condition_summary": book_condition_data.model_dump().get("Condition", ""),
    "print_type": book_condition_data.model_dump().get("PrintType", ""),
    
    ## dumping the entire generation data including from the reasoning steps
    "book_condition_data": book_condition_data.model_dump(),  # Dict, not JSON string
    
    # book content hints
    "book_blurb_text": book_content_hints.model_dump().get("bookBlurbText", ""),
    "bookNERData": book_content_hints.model_dump().get("bookNERData", []),
    "isFiction": book_content_hints.model_dump().get("isFiction", bool),
    "book_genre": book_content_hints.model_dump().get("bookGenre", []),
    
    ## dumping the entire content hints generation data including from the reasoning steps
    "book_content_hints": book_content_hints.model_dump(),  # Dict, not JSON string
    
    # dumping the raw_analysis from the reasoning process of the book identification
    "raw_analysis": bookRawAnalysis.model_dump(),  # Dict, not JSON string
    
    
    # TODO : add key data columns for easier querying
}]

print("Adding the data to the LanceDB table...")
try:
    active_tbl = db.open_table("active_table_lots_columns")
    print("Table 'active_table' opened successfully.")
except Exception as e:
    print("Table 'active_table_lots_columns' does not exist. Creating new table with inferred schema...")
    # Create table with automatic schema inference from data
    active_tbl = db.create_table("active_table_lots_columns", data=data_to_ingest)
    print("Table created successfully!")
else:
    # Table exists, just add data
    active_tbl.add(data_to_ingest)

print("Data ingestion completed.")

polars_df = active_tbl.to_polars().lazy().collect()
print(polars_df)
