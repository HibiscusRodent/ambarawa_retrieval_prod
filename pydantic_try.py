from image_processors import ProcessedBookData
from lancedb.pydantic import LanceModel
from pathlib import Path
from typing import Any
import pprint

from loguru import logger


# TODO : configure the lancedb connnection and make sure that the overwrite mode on
# create table is turned off in real production
from lancedb import connect

from image_processors import ImageProcessors, BookFolderPathData

from baml_client.sync_client import b
from baml_client.types import (
    BookConditionData,
)

# Import the LanceModel schema
# from ConditionDataSchema import LanceConditionData
from bamlToLanceSchema import LanceBookConditionData
from pydantic_to_lance_db_schema import pydantic_to_arrow_schema


def process_image_folder(
    processor: ImageProcessors, folder_path: str
) -> ProcessedBookData:
    """
    Process the images in the specified book folder.

    Args:
        processor: The ImageProcessors instance.
        folder_path: The path to the book folder.

    Returns:
        ProcessedBookData: The processed data containing book ID and images.
    """
    book_folder = BookFolderPathData(path=Path(folder_path))
    data: ProcessedBookData = processor.process_book_folder(book_folder)
    logger.info(
        "Processed book folder - Book ID: %s, Image Count: %d, Folder Path: %s",
        data.book_id,
        len(data.binary_images),
        folder_path,
    )
    return data


def analyze_book_condition(
    baml_images: Any, book_id: str, output_folder: Path
) -> BookConditionData:
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
        data = b.GetBookConditionData(MultiImages=baml_images, bookId=book_id)
        pprint.pprint(data.model_dump())
        return data
    except Exception as e:
        logger.exception(
            "Failed to analyze book condition - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        return BookConditionData.model_construct(Condition=None, PrintType=None)


# ---- begin trial code ----#

book_folder_path = "sample_data/rak-0018_baris-002_buku-12"
output_folder_path = "data/output_book_data/pydantic_try"
lance_db_uri = "data/test/pydantic_simple_try"
table_name = "single_inference_results"

# setup lance db connection
active_db = connect(lance_db_uri)
logger.info("Connected to LanceDB at URI: %s", lance_db_uri)

# initialize image processor
processor = ImageProcessors()
logger.info("Initialized ImageProcessors.")

from ConditionDataSchema import LanceConditionData

    
# create an empty lance db table using the schema
# the schema here is not imported directly from the BAML client types,
# but rather wrapped in a LanceModel for LanceDB compatibility
active_db.create_table("test_empty_table", schema = LanceConditionData, mode="overwrite")
logger.info("Created LanceDB table with LanceConditionData schema.")


# this one use the baml client type directly wrapped in LanceModel
baml_direct_schema = pydantic_to_arrow_schema(BookConditionData)
logger.info("Generated Arrow schema from BookConditionData: %s", baml_direct_schema)
# if this fails, it means there is something wrong with the pydantic_to_arrow_schema function
# that makes it unable to handle the BAML client types directly

active_db.create_table("table_with_baml_direct_schema", schema = baml_direct_schema, mode="overwrite")
logger.info("Created LanceDB table with BookConditionData schema directly.")
# if this fails, it means LanceDB has problem handling the schema generated
# from the BAML client types directly
# and we need to modify the pydantic_to_arrow_schema function to make it compatible