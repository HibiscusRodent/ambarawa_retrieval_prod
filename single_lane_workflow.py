import baml_client.types as baml_types
from baml_client.sync_client import b
import types_utils.pydantic_to_lance_schema as pyd_to_lance

import lancedb
from pathlib import Path

from image_processors import ImageProcessors
from typing import Any
from logger import logger
import pprint
from dotenv import load_dotenv

load_dotenv()



# get some basic folder paths
book_folder_path = Path("sample_data/rak-0003_baris-005_buku-30")
output_folder_path = Path("data/output_book_data/pydantic_try")
lance_db_uri = Path("data/test/single_lane_experiment")
table_name = "run_single_lane"

# connect to lance db
active_db = lancedb.connect(lance_db_uri.as_posix())

# initialize the schema, and convert it to lance schema
bookConditionDataLance = pyd_to_lance.pydantic_to_arrow_schema(baml_types.BookConditionData)

# create an empty table using the schema
# TODO please change the overwrite mode later, this is just for testing
active_table = active_db.create_table(table_name, schema=bookConditionDataLance, mode="overwrite")
logger.info(f"Created LanceDB table '{table_name}' at '{lance_db_uri.as_posix()}' with BookConditionData schema.")

# NOW to add real data to the table


def analyze_book_condition(
    baml_images: Any, book_id: str, output_folder: Path
) -> baml_types.BookConditionData:
    """
    Analyze the book condition using BAML and save the result.

    Args:
        baml_images: The BAML-formatted images.
        book_id: The ID of the book.
        output_folder: The folder to save the JSON result.

    Returns:
        BookConditionData: The analysis result.
    """
    try:
        logger.info("Starting book condition analysis for Book ID: %s", book_id)
        BookConditionInferedData = b.GetBookConditionData(MultiImages=baml_images, bookId=book_id)
        pprint.pprint(BookConditionInferedData.model_dump())
        return BookConditionInferedData
    except Exception as e:
        logger.exception(
            "Failed to analyze book condition - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        return baml_types.BookConditionData.model_construct(Condition=None, PrintType=None)
    

# generate data to be inserted
## first activate the image processor
img_proc = ImageProcessors()
logger.info("Initialized ImageProcessors.")

# process the book folder to get images data and book id
processed_data = img_proc.process_book_folder(book_folder_path)
baml_images = processed_data["baml_images"] # TODO remember, this is how to get the images from a typed dict
book_id = processed_data["book_id"]

# get baml inference data
logger.info ("Analyzing book condition for Book ID: %s", book_id)
inference_data = analyze_book_condition(baml_images, book_id, output_folder_path)

# open the lance db table, the same table from the creation step
active_table = active_db.open_table(table_name)
logger.info(f"Opened LanceDB table '{table_name}' for data insertion.")

# insert the inference data into the lance db table
active_table = active_table.add(inference_data)
logger.info(f"Inserted inference data for Book ID: {book_id} into LanceDB table '{table_name}'.")