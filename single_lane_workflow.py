import baml_client.types as baml_types
from baml_client.sync_client import b
import types_utils.pydantic_to_lance_schema as pyd_to_lance

import lancedb
from pathlib import Path

from image_processors import ImageProcessors, BookFolderPathData, ProcessedBookData
from typing import Any
from logger import logger
import pprint



# get some basic folder paths
book_folder_path = Path("sample_data/rak-0018_baris-002_buku-12")
output_folder_path = Path("data/output_book_data/pydantic_try")
lance_db_uri = Path("data/test/single_lane_experiment")
table_name = "run_single_lane"

# connect to lance db
active_db = lancedb.connect(lance_db_uri.as_posix())

# initialize the schema, and convert it to lance schema
bookConditionDataLance = pyd_to_lance.pydantic_to_arrow_schema(baml_types.BookConditionData)

# create an empty table using the schema
# TODO please change the overwrite mode later, this is just for testing
active_db.create_table(table_name, schema=bookConditionDataLance, mode="overwrite")
logger.info(f"Created LanceDB table '{table_name}' at '{lance_db_uri.as_posix()}' with BookConditionData schema.")

# NOW to add real data to the table
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
        return baml_types.BookConditionData.model_construct(Condition=None, PrintType=None)