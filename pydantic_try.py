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

# Drop the table if it exists
try:
    active_db.drop_table("test_empty_table")
    logger.info("Dropped existing table 'test_empty_table'")
except Exception:
    pass  # Table doesn't exist, which is fine

from ConditionDataSchema import LanceConditionData

    
# create an empty lance db table using the schema
active_db.create_table("test_empty_table", schema = LanceConditionData)
logger.info("Created LanceDB table with LanceConditionData schema.")