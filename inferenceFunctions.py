from PIL.ImagePalette import random
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
from prefect.cache_policies import NO_CACHE
from dotenv import load_dotenv

# TODO: Remove the logfire logging since we are using prefect logging now
import logfire

@task
def configure_environment() -> None:
    """
    Load environment variables and configure logfire.
    """
    load_dotenv()
    logfire.configure()
    logfire.info("Environment configured and Logfire initialized.")

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
@task
async def initialize_database(uri: str) -> AsyncConnection:
    """
    Initialize the LanceDB connection.

    Args:
        uri: The URI for the LanceDB database.

    Returns:
        AsyncConnection: The connected LanceDB instance.
    """
    db = await connect_async(uri)
    logfire.info("Connected to LanceDB", uri=uri)
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
@logfire.instrument
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
    book_folder = BookFolderPathData(path=folder_path)
    data: ProcessedBookData = processor.process_book_folder(book_folder)
    logfire.info(
        "Processed book folder",
        book_id=data.book_id,
        image_count=len(data.binary_images),
    )
    return data

@task
@logfire.instrument
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
    book_id: str = processed_data.book_id
    book_output_folder: Path = output_root / book_id

    # Efficiently clear existing images or create folder
    if book_output_folder.exists():
        shutil.rmtree(book_output_folder)
    book_output_folder.mkdir(parents=True, exist_ok=True)

    # Write binary images
    for idx, img_data in enumerate(processed_data.binary_images):
        img_file_path: Path = book_output_folder / f"{book_id}_img_{idx + 1:03d}.jpg"
        img_file_path.write_bytes(img_data)

    logfire.info(
        "Saved images locally",
        path=str(book_output_folder),
        count=len(processed_data.binary_images),
    )
    return book_output_folder


@task
@logfire.instrument
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
        data = b.GetBookConditionData(MultiImages=baml_images, bookId=book_id)
        _save_to_json(data, output_folder / f"{book_id}_book_condition_data.json")

        logfire.info("Analyzed book condition", book_id=book_id)
        return data
    except Exception as e:
        logfire.exception(
            "Failed to analyze book condition", book_id=book_id, error=str(e)
        )
        return BookConditionData.model_construct(Condition=None, PrintType=None)


@task
@logfire.instrument
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
    try:
        analysis = b.GetBookrawVisual(MultiImages=baml_images, bookId=book_id)
        _save_to_json(analysis, output_folder / f"{book_id}_raw_analysis.json")

        logfire.info("Completed raw visual analysis", book_id=book_id)
        return analysis
    except Exception as e:
        logfire.exception("Failed to run raw analysis", book_id=book_id, error=str(e))
        return RawAnalysis.model_construct(
            coverPageDescription="",
            backCoverDescription="",
            colophonPageDescription="",
            otherPageDescriptions="",
        )


@task
@logfire.instrument
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
    try:
        hints = b.GetBookContentHints(
            MultiImages=baml_images,
            bookId=book_id,
            RawVisualNote=raw_visual_json,
        )
        _save_to_json(hints, output_folder / f"{book_id}_book_content_hints.json")

        logfire.info("Analyzed content hints", book_id=book_id)
        return hints
    except Exception as e:
        logfire.exception(
            "Failed to analyze content hints", book_id=book_id, error=str(e)
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
    try:
        main_data = b.GetBookMainData(
            MultiImages=baml_images,
            bookId=book_id,
            RawVisualNote=raw_visual_json,
        )
        _save_to_json(main_data, output_folder / f"{book_id}_book_main_data.json")

        logfire.info("Analyzed main book data", book_id=book_id)
        return main_data
    except Exception as e:
        logfire.exception(
            "Failed to analyze main book data", book_id=book_id, error=str(e)
        )
        return BookMainData.model_construct(
            title=None,
            isbn_10=None,
            isbn_13=None,
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
    try:
        details = b.GetBookPublisherData(
            MultiImages=baml_images,
            bookId=book_id,
            RawVisualNote=raw_visual_json,
        )

        _save_to_json(
            details, output_folder / f"{book_id}_book_pub_and_dist_details.json"
        )

        logfire.info("Analyzed publisher details", book_id=book_id)
        return details
    except Exception as e:
        logfire.exception(
            "Failed to analyze publisher details", book_id=book_id, error=str(e)
        )
        return BookPubAndDistDetails.model_construct(
            published_year=None,
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
    logfire.info(
        "Starting data ingestion", table_name=table_name, record_count=len(data)
    )
    
    # TODO : in real production, we should not use random table name, instead use one that has been configured
    letters_lower = string.ascii_lowercase
    random_three_letters = ''.join(random.choices(letters_lower, k=3)) # this returns missing attributes error, but it works
    
    table_name = f"{table_name}_{random_three_letters}"
    await db.create_table(table_name, data)
    
    print(f"Adding the data to the LanceDB table '{table_name}'...")
    # db is already awaited in main_flow
    active_tbl = await db.open_table(table_name)
    await active_tbl.add(data)
    print("Data ingestion completed.")
    logfire.info("Data ingestion completed")
    return active_tbl


@flow
async def process_one_book_flow() -> None:
    """
    Main function to orchestrate the book data extraction and ingestion process.
    """
    # Configuration using Path
    sample_book_folder_path = Path("sample_data/rak-0018_baris-002_buku-12")
    output_folder_path = Path("data/output_book_data")
    lance_db_uri = "data/test/lance_db_semi_prod"
    table_name = "active_table_lots_columns"

    # 1. Setup
    configure_environment()
    setup_output_directory(output_folder_path)

    # 2. Initialization
    db: AsyncConnection = await initialize_database(lance_db_uri)
    ip: ImageProcessors = initialize_image_processor()

    # 3. Image Processing
    images_data: ProcessedBookData = process_image_folder(ip, str(sample_book_folder_path))

    # 4. Save Images Locally
    book_output_folder: Path = save_images_locally(images_data, output_folder_path)

    # 5. BAML Analysis
    book_id = images_data.book_id
    baml_images: list[BamlImagePy] = images_data.baml_images

    # Step 5a: Book Condition
    book_condition: BookConditionData = analyze_book_condition(baml_images, book_id, book_output_folder)

    # Step 5b: Raw Analysis
    raw_analysis: RawAnalysis = run_raw_analysis(baml_images, book_id, book_output_folder)
    raw_visual_json: str = raw_analysis.model_dump_json()

    # Step 5c: Content Hints
    content_hints: BookContentHints = analyze_content_hints(
        baml_images, book_id, raw_visual_json, book_output_folder
    )

    # Step 5d: Main Data
    main_data: BookMainData = analyze_main_data(
        baml_images, book_id, raw_visual_json, book_output_folder
    )

    # Step 5e: Publisher Details
    pub_details: BookPubAndDistDetails = analyze_publisher_details(
        baml_images, book_id, raw_visual_json, book_output_folder
    )

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


if __name__ == "__main__":
    asyncio.run(process_one_book_flow())
