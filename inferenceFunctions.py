from baml_py.baml_py import BamlImagePy
from image_processors import ProcessedBookData
from pathlib import Path
import shutil
import asyncio
import random
import string

# TODO : configure the lancedb connnection and make sure that the overwrite mode on
# create table is turned off in real production
from lancedb import connect_async
from lancedb.db import AsyncConnection

from image_processors import ImageProcessors, BookFolderPathData

from baml_client.sync_client import b
from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)

from typing import Any, List, Dict
from pydantic import BaseModel
from prefect import task, flow
from prefect.futures import wait, PrefectFuture
from prefect.cache_policies import NO_CACHE
from prefect_dask import DaskTaskRunner
from prefect.logging import get_run_logger
from dotenv import load_dotenv


@task
def configure_environment() -> None:
    """
    Load environment variables and configure the environment.
    """
    logger = get_run_logger()
    load_dotenv()
    logger.info("Environment configured and variables loaded.")


@task
def setup_output_directory(output_path: Path) -> None:
    """
    Ensure the output directory exists.

    Args:
        output_path: The Path to the output directory.
    """
    output_path.mkdir(parents=True, exist_ok=True)


@task
def _save_to_json(data: BaseModel, output_path: Path) -> None:
    """
    Helper function to save a Pydantic model as a JSON file.

    Args:
        data: The Pydantic model instance.
        output_path: The full Path to the output JSON file.
    """
    with output_path.open("w", encoding="utf-8") as f:
        f.write(data.model_dump_json(indent=4, ensure_ascii=False))


@task
async def initialize_database(uri: str) -> AsyncConnection:
    """
    Initialize the LanceDB connection.

    Args:
        uri: The URI for the LanceDB database.

    Returns:
        AsyncConnection: The connected LanceDB instance.
    """
    logger = get_run_logger()
    db = await connect_async(uri)
    logger.info("Connected to LanceDB at URI: %s", uri)
    return db


@task
def initialize_image_processor() -> ImageProcessors:
    """
    Initialize the ImageProcessors instance.

    Returns:
        ImageProcessors: An instance of ImageProcessors.
    """
    return ImageProcessors()


@task
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
    logger = get_run_logger()
    book_folder = BookFolderPathData(path=folder_path)
    data: ProcessedBookData = processor.process_book_folder(book_folder)
    logger.info(
        "Processed book folder - Book ID: %s, Image Count: %d, Folder Path: %s",
        data.book_id,
        len(data.binary_images),
        folder_path,
    )
    return data


@task
def save_images_locally(processed_data: ProcessedBookData, output_root: Path) -> Path:
    """
    Save binary images to the local file system.

    Creates a subdirectory for the book_id within output_root, clears it,
    and saves the images.

    Args:
        processed_data: The processed book data.
        output_root: The root output directory.

    Returns:
        Path: The Path object for the specific book's output folder.
    """
    logger = get_run_logger()
    book_id: str = processed_data.book_id
    book_output_folder: Path = output_root / book_id

    # Efficiently clear existing images or create folder
    if book_output_folder.exists():
        logger.info("Clearing existing output folder: %s", str(book_output_folder))
        shutil.rmtree(book_output_folder)
    book_output_folder.mkdir(parents=True, exist_ok=True)

    # Write binary images
    for idx, img_data in enumerate(processed_data.binary_images):
        img_file_path: Path = book_output_folder / f"{book_id}_img_{idx + 1:03d}.jpg"
        img_file_path.write_bytes(img_data)

    logger.info(
        "Saved images locally - Book ID: %s, Path: %s, Image Count: %d",
        book_id,
        str(book_output_folder),
        len(processed_data.binary_images),
    )
    return book_output_folder


@task
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
    logger = get_run_logger()
    try:
        logger.info("Starting book condition analysis for Book ID: %s", book_id)
        data = b.GetBookConditionData(MultiImages=baml_images, bookId=book_id)
        _save_to_json(data, output_folder / f"{book_id}_book_condition_data.json")

        logger.info(
            "Analyzed book condition - Book ID: %s, Condition: %s, Print Type: %s",
            book_id,
            data.Condition,
            data.PrintType,
        )
        return data
    except Exception as e:
        logger.exception(
            "Failed to analyze book condition - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        return BookConditionData.model_construct(Condition=None, PrintType=None)


@task
def run_raw_analysis(
    baml_images: Any, book_id: str, output_folder: Path
) -> RawAnalysis:
    """
    Perform raw visual analysis using BAML and save the result.

    Args:
        baml_images: The BAML-formatted images.
        book_id: The ID of the book.
        output_folder: The folder to save the JSON result.

    Returns:
        RawAnalysis: The analysis result.
    """
    logger = get_run_logger()
    try:
        logger.info("Starting raw visual analysis for Book ID: %s", book_id)
        analysis = b.GetBookrawVisual(MultiImages=baml_images, bookId=book_id)
        _save_to_json(analysis, output_folder / f"{book_id}_raw_analysis.json")

        logger.info(
            "Completed raw visual analysis - Book ID: %s, Has Cover: %s, Has Back Cover: %s",
            book_id,
            bool(analysis.coverPageDescription),
            bool(analysis.backCoverDescription),
        )
        return analysis
    except Exception as e:
        logger.exception(
            "Failed to run raw analysis - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        return RawAnalysis.model_construct(
            coverPageDescription="",
            backCoverDescription="",
            colophonPageDescription="",
            otherPageDescriptions="",
        )


@task
def analyze_content_hints(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: Path
) -> BookContentHints:
    """
    Generate content hints using BAML and save the result.

    Args:
        baml_images: The BAML-formatted images.
        book_id: The ID of the book.
        raw_visual_json: simple string representation of RawAnalysis.
        output_folder: The folder to save the JSON result.

    Returns:
        BookContentHints: The analysis result.
    """
    logger = get_run_logger()
    try:
        logger.info("Starting content hints analysis for Book ID: %s", book_id)
        hints = b.GetBookContentHints(
            MultiImages=baml_images,
            bookId=book_id,
            RawVisualNote=raw_visual_json,
        )
        _save_to_json(hints, output_folder / f"{book_id}_book_content_hints.json")

        logger.info(
            "Analyzed content hints - Book ID: %s, Is Fiction: %s, Genre Count: %d, NER Count: %d",
            book_id,
            hints.isFiction,
            len(hints.bookGenre) if hints.bookGenre else 0,
            len(hints.bookNERData) if hints.bookNERData else 0,
        )
        return hints
    except Exception as e:
        logger.exception(
            "Failed to analyze content hints - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        return BookContentHints.model_construct(
            bookBlurbText=None, bookNERData=[], isFiction=False, bookGenre=[]
        )


@task
def analyze_main_data(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: Path
) -> BookMainData:
    """
    Extract main book data using BAML and save the result.

    Args:
        baml_images: The BAML-formatted images.
        book_id: The ID of the book.
        raw_visual_json: simple string representation of RawAnalysis.
        output_folder: The folder to save the JSON result.

    Returns:
        BookMainData: The analysis result.
    """
    logger = get_run_logger()
    try:
        logger.info("Starting main data extraction for Book ID: %s", book_id)
        main_data = b.GetBookMainData(
            MultiImages=baml_images,
            bookId=book_id,
            RawVisualNote=raw_visual_json,
        )
        _save_to_json(main_data, output_folder / f"{book_id}_book_main_data.json")

        logger.info(
            "Analyzed main book data - Book ID: %s, Title: %s, ISBN-10: %s, ISBN-13: %s, Author Count: %d",
            book_id,
            main_data.title,
            main_data.isbn_10,
            main_data.isbn_13,
            len(main_data.authors) if main_data.authors else 0,
        )
        return main_data
    except Exception as e:
        logger.exception(
            "Failed to analyze main book data - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        return BookMainData.model_construct(
            title=None,
            isbn_10=None,
            isbn_13=None,
            published_year=None,
            language=[],
            script=[],
            authors=[],
            translator=[],
        )


@task
def analyze_publisher_details(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: Path
) -> BookPubAndDistDetails:
    """
    Extract publisher and distributor details using BAML and save the result.

    Args:
        baml_images: The BAML-formatted images.
        book_id: The ID of the book.
        raw_visual_json: simple string representation of RawAnalysis.
        output_folder: The folder to save the JSON result.

    Returns:
        BookPubAndDistDetails: The analysis result.
    """
    logger = get_run_logger()
    try:
        logger.info("Starting publisher details extraction for Book ID: %s", book_id)
        details: BookPubAndDistDetails = b.GetBookPublisherData(
            MultiImages=baml_images,
            bookId=book_id,
            RawVisualNote=raw_visual_json,
        )

        _save_to_json(
            details, output_folder / f"{book_id}_book_pub_and_dist_details.json"
        )

        logger.info(
            "Analyzed publisher details - Book ID: %s, Publisher: %s, Distributor: %s",
            book_id,
            details.publisher_name,
            details.distributor_name,
        )
        return details
    except Exception as e:
        logger.exception(
            "Failed to analyze publisher details - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        return BookPubAndDistDetails.model_construct(
            publisher_name=None,
            publisher_location=None,
            distributor_name=None,
            distributor_location=None,
        )


@task
def prepare_data_for_ingestion(
    book_id: str,
    binary_images: List[bytes],
    book_main: BookMainData,
    book_pub: BookPubAndDistDetails,
    book_condition: BookConditionData,
    book_content: BookContentHints,
    raw_analysis: RawAnalysis,
) -> List[Dict[str, Any]]:
    """
    Prepare the data dictionary for LanceDB ingestion.

    Args:
        book_id: The book ID.
        binary_images: List of image bytes.
        book_main: The main book data.
        book_pub: Publisher and distributor details.
        book_condition: Book condition data.
        book_content: Book content hints.
        raw_analysis: Raw visual analysis.

    Returns:
        List[Dict[str, Any]]: A list containing the dictionary to be ingested.
    """
    # Streamlined by dumping once
    bm = book_main.model_dump()
    bp = book_pub.model_dump()
    bc = book_condition.model_dump()
    bh = book_content.model_dump()

    return [
        {
            "book_id": book_id,
            "images_data": binary_images,
            "book_title": bm.get("title", {}),
            "isbns": {
                "isbn_10": bm.get("isbn_10"),
                "isbn_13": bm.get("isbn_13"),
            },
            "language_data": {
                "languages": bm.get("language", []),
                "scripts": bm.get("script", []),
            },
            "authors": bm.get("authors", []),
            "translators": bm.get("translator", []),
            "published_year": bp.get("published_year", None),
            "book_main_data": bm,
            "publisher_name": bp.get("publisher_name", {}),
            "publisher_location": bp.get("publisher_location", {}),
            "distributor_name": bp.get("distributor_name", {}),
            "distributor_location": bp.get("distributor_location", {}),
            "book_pub_and_dist_details": bp,
            "book_condition_summary": bc.get("Condition", ""),
            "print_type": bc.get("PrintType", ""),
            "book_condition_data": bc,
            "book_blurb_text": bh.get("bookBlurbText", ""),
            "bookNERData": bh.get("bookNERData", []),
            "isFiction": bh.get("isFiction", False),
            "book_genre": bh.get("bookGenre", []),
            "book_content_hints": bh,
            "raw_analysis": raw_analysis.model_dump(),
        }
    ]


@task(cache_policy=NO_CACHE)
async def ingest_to_lancedb(
    db: AsyncConnection,
    table_name: str,
    data: List[Dict[str, Any]],
) -> Any:
    """
    Ingest data into LanceDB.

    Args:
        db: The LanceDB connection.
        table_name: The name of the table.
        data: The data to ingest.
        mode: The write mode ('overwrite', 'append', etc.).

    Returns:
        Any: The table object.
    """
    logger = get_run_logger()
    logger.info(
        "Starting data ingestion - Base Table Name: %s, Record Count: %d",
        table_name,
        len(data),
    )

    # TODO : in real production, we should not use random table name, instead use one that has been configured
    letters_lower = string.ascii_lowercase
    random_three_letters = "".join(
        random.choices(letters_lower, k=3)
    )  # this returns missing attributes error, but it works

    table_name = f"{table_name}_{random_three_letters}"
    logger.info("Creating table with name: %s", table_name)
    await db.create_table(table_name, data)

    logger.info("Adding data to LanceDB table: %s", table_name)
    # db is already awaited in main_flow
    active_tbl = await db.open_table(table_name)
    await active_tbl.add(data)
    logger.info(
        "Data ingestion completed successfully - Table: %s, Records Added: %d",
        table_name,
        len(data),
    )
    return active_tbl


@flow(task_runner=DaskTaskRunner(cluster_kwargs={"processes": False}))  # type: ignore[call-overload]
async def process_one_book_flow(
    book_folder_path: str,
    output_folder_path: str,
    lance_db_uri: str,
    table_name: str,
) -> None:
    """
    Main function to orchestrate the book data extraction and ingestion process.

    This flow uses DaskTaskRunner to execute BAML inference tasks in parallel where possible.
    The parallelization strategy is:
    - Phase 1: book_condition and raw_analysis run in parallel (no dependencies)
    - Phase 2: content_hints, main_data, and pub_details run in parallel
      (all depend on raw_analysis result)

    Args:
        book_folder_path: Path to the folder containing book images to process.
        output_folder_path: Path to the directory where output data will be saved.
        lance_db_uri: URI for the LanceDB database connection.
        table_name: Name of the table in LanceDB for data ingestion.
    """
    # Configuration using Path
    sample_book_folder_path = Path(book_folder_path)
    output_folder = Path(output_folder_path)

    # 1. Setup
    configure_environment()
    setup_output_directory(output_folder)

    # 2. Initialization
    db: AsyncConnection = await initialize_database(lance_db_uri)
    ip: ImageProcessors = initialize_image_processor()

    # 3. Image Processing
    images_data: ProcessedBookData = process_image_folder(
        ip, str(sample_book_folder_path)
    )

    # 4. Save Images Locally
    book_output_folder: Path = save_images_locally(images_data, output_folder)

    # 5. BAML Analysis with parallel execution
    book_id = images_data.book_id
    baml_images: list[BamlImagePy] = images_data.baml_images

    # Phase 1: Submit independent tasks in parallel
    # book_condition and raw_analysis don't depend on each other
    book_condition_future = analyze_book_condition.submit(
        baml_images, book_id, book_output_folder
    )
    raw_analysis_future = run_raw_analysis.submit(
        baml_images, book_id, book_output_folder
    )

    # Wait for Phase 1 to complete and get results
    phase_1_futures: list[PrefectFuture[Any]] = [
        book_condition_future,
        raw_analysis_future,
    ]
    wait(phase_1_futures)
    book_condition: BookConditionData = book_condition_future.result()
    raw_analysis: RawAnalysis = raw_analysis_future.result()
    raw_visual_json: str = raw_analysis.model_dump_json()

    # Phase 2: Submit dependent tasks in parallel
    # content_hints, main_data, and pub_details all depend on raw_visual_json
    # but are independent of each other
    content_hints_future = analyze_content_hints.submit(
        baml_images, book_id, raw_visual_json, book_output_folder
    )
    main_data_future = analyze_main_data.submit(
        baml_images, book_id, raw_visual_json, book_output_folder
    )
    pub_details_future = analyze_publisher_details.submit(
        baml_images, book_id, raw_visual_json, book_output_folder
    )

    # Wait for Phase 2 to complete and get results
    phase_2_futures: list[PrefectFuture[Any]] = [
        content_hints_future,
        main_data_future,
        pub_details_future,
    ]
    wait(phase_2_futures)
    content_hints: BookContentHints = content_hints_future.result()
    main_data: BookMainData = main_data_future.result()
    pub_details: BookPubAndDistDetails = pub_details_future.result()

    # 6. Prepare for Ingestion
    data_to_ingest: list[dict[str, Any]] = prepare_data_for_ingestion(
        book_id=book_id,
        binary_images=images_data.binary_images,
        book_main=main_data,
        book_pub=pub_details,
        book_condition=book_condition,
        book_content=content_hints,
        raw_analysis=raw_analysis,
    )

    # 7. Ingest to LanceDB
    await ingest_to_lancedb(db, table_name, data_to_ingest)


def main() -> None:
    # Default configuration parameters
    book_folder_path = "sample_data/rak-0018_baris-002_buku-12"
    output_folder_path = "data/output_book_data"
    lance_db_uri = "data/test/lance_db_semi_prod"
    table_name = "active_table_lots_columns"

    asyncio.run(
        process_one_book_flow(
            book_folder_path=book_folder_path,
            output_folder_path=output_folder_path,
            lance_db_uri=lance_db_uri,
            table_name=table_name,
        )
    )
    return None


if __name__ == "__main__":
    main()
