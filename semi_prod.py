import os

import lancedb

from image_processors import ImageProcessors, BookFolderPathData

from baml_client.sync_client import b
from baml_client.types import BookConditionData

from dotenv import load_dotenv
env_loader: bool = load_dotenv()

sample_book_folder_path =  "sample_data/rak-0018_baris-002_buku-12"

# the data will be saved into this folder path in the form of images, and json files
output_folder_path = "data/output_book_data"
os.makedirs(output_folder_path, exist_ok=True)


# Initialize the local lancedb connection
# uri = "data/lance_db_semi_prod"

lance_db_api_key = os.getenv("LANCEDB_API_KEY_PROD")

db = lancedb.connect(
    uri="db://ambarawa-book-retrieval-x3jev2",
    api_key=lance_db_api_key,
    region="us-east-1"
)

# initialize the image processors so that it have the necessary config initialized
ip = ImageProcessors()
book_folder = BookFolderPathData(path=sample_book_folder_path)
images_data: ProcessedBookData = ip.process_book_folder(book_folder)

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
# Store nested objects with their field labels preserved
book_main_dumped = book_main_data.model_dump()
book_pub_dumped = book_pub_and_dist_details.model_dump()
book_condition_dumped = book_condition_data.model_dump()
book_content_dumped = book_content_hints.model_dump()

data_to_ingest = [{
    # organization metadata
    "book_id": book_id,
    "images_data": binary_images,
    
    # main data of the book - preserving nested structure with field labels
    "book_title": book_main_dumped.get("title", {}),  # Dict with labeled fields
    "isbns": {
        "isbn_10": book_main_dumped.get("isbn_10"),
        "isbn_13": book_main_dumped.get("isbn_13")
    },
    "language_data": {
        "languages": book_main_dumped.get("language", []),
        "scripts": book_main_dumped.get("script", [])
    },
    "authors": book_main_dumped.get("authors", []),  # List of dicts with labeled fields
    "translators": book_main_dumped.get("translator", []),  # List of dicts with labeled fields
    "published_year": book_pub_dumped.get("published_year", None),
    
    ## saved the entire generation data including from the reasoning steps
    "book_main_data": book_main_dumped,  # Dict, not JSON string
    
    # publisher and distribution details - preserving nested structure with field labels
    "publisher_name": book_pub_dumped.get("publisher_name", {}),  # Dict with labeled fields
    "publisher_location": book_pub_dumped.get("publisher_location", {}),  # Dict with labeled fields
    "distributor_name": book_pub_dumped.get("distributor_name", {}),  # Dict with labeled fields
    "distributor_location": book_pub_dumped.get("distributor_location", {}),  # Dict with labeled fields

    ## saved the entire generation data including from the reasoning steps
    "book_pub_and_dist_details": book_pub_dumped,  # Dict, not JSON string
    
    # book condition data
    "book_condition_summary": book_condition_dumped.get("Condition", ""),
    "print_type": book_condition_dumped.get("PrintType", ""),
    
    ## dumping the entire generation data including from the reasoning steps
    "book_condition_data": book_condition_dumped,  # Dict, not JSON string
    
    # book content hints
    "book_blurb_text": book_content_dumped.get("bookBlurbText", ""),
    "bookNERData": book_content_dumped.get("bookNERData", []),
    "isFiction": book_content_dumped.get("isFiction", False),  # Use False as default for bool
    "book_genre": book_content_dumped.get("bookGenre", []),
    
    ## dumping the entire content hints generation data including from the reasoning steps
    "book_content_hints": book_content_dumped,  # Dict, not JSON string
    
    # dumping the raw_analysis from the reasoning process of the book identification
    "raw_analysis": bookRawAnalysis.model_dump(),  # Dict, not JSON string
    
    
    # TODO : add key data columns for easier querying
}]

print("Adding the data to the LanceDB table...")
active_tbl = db.create_table("active_table_lots_columns", data=data_to_ingest, mode = "overwrite")


print("Data ingestion completed.")

print("Fetching and displaying data from the LanceDB table...")
polars_df = active_tbl.to_polars().lazy().collect()
print(polars_df)

# save the polars dataframe to a parquet file for easier viewing
parquet_output_path = os.path.join(book_output_folder, f"{book_id}_lancedb_data.parquet")
polars_df.write_parquet(parquet_output_path)

print(f"Data saved to Parquet file at: {parquet_output_path}")