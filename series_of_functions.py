from image_processors import ProcessedBookData
import os

import lancedb
from lancedb.db import DBConnection

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
import logfire

from dotenv import load_dotenv


def configure_environment() -> None:
    """
    Load environment variables and configure logfire.
    """
    load_dotenv()
    logfire.configure()


def setup_output_directory(output_path: str) -> None:
    """
    Ensure the output directory exists.

    Args:
        output_path: The path to the output directory.
    """
    os.makedirs(output_path, exist_ok=True)


def initialize_database(uri: str) -> DBConnection:
    """
    Initialize the LanceDB connection.

    Args:
        uri: The URI for the LanceDB database.

    Returns:
        DBConnection: The connected LanceDB instance.
    """
    return lancedb.connect(uri)


def initialize_image_processor() -> ImageProcessors:
    """
    Initialize the ImageProcessors instance.

    Returns:
        ImageProcessors: An instance of ImageProcessors.
    """
    return ImageProcessors()


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
    return processor.process_book_folder(book_folder)


def save_images_locally(processed_data: ProcessedBookData, output_root: str) -> str:
    """
    Save binary images to the local file system.

    Creates a subdirectory for the book_id within output_root, clears it,
    and saves the images.

    Args:
        processed_data: The processed book data.
        output_root: The root output directory.

    Returns:
        str: The path to the specific book's output folder.
    """
    book_id: str = processed_data.book_id
    book_output_folder: str = os.path.join(output_root, book_id)
    os.makedirs(book_output_folder, exist_ok=True)

    # Clear existing images
    for filename in os.listdir(book_output_folder):
        file_path: str = os.path.join(book_output_folder, filename)
        if os.path.isfile(file_path):
            os.unlink(file_path)

    # Write binary images
    for idx, img_data in enumerate(processed_data.binary_images):
        img_file_path: str = os.path.join(
            book_output_folder, f"{book_id}_img_{idx + 1:03d}.jpg"
        )
        with open(img_file_path, "wb") as img_file:
            img_file.write(img_data)

    return book_output_folder


def analyze_book_condition(
    baml_images: Any, book_id: str, output_folder: str
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
    data = b.GetBookConditionData(MultiImages=baml_images, bookId=book_id)

    json_path: str = os.path.join(output_folder, f"{book_id}_book_condition_data.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json_file.write(data.model_dump_json(indent=4, ensure_ascii=False))

    return data


def run_raw_analysis(baml_images: Any, book_id: str, output_folder: str) -> RawAnalysis:
    """
    Perform raw visual analysis using BAML and save the result.

    Args:
        baml_images: The BAML-formatted images.
        book_id: The ID of the book.
        output_folder: The folder to save the JSON result.

    Returns:
        RawAnalysis: The analysis result.
    """
    analysis = b.GetBookrawVisual(MultiImages=baml_images, bookId=book_id)

    json_path = os.path.join(output_folder, f"{book_id}_raw_analysis.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json_file.write(analysis.model_dump_json(indent=4, ensure_ascii=False))

    return analysis


def analyze_content_hints(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: str
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
    hints = b.GetBookContentHints(
        MultiImages=baml_images,
        bookId=book_id,
        RawVisualNote=raw_visual_json,
    )

    json_path = os.path.join(output_folder, f"{book_id}_book_content_hints.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json_file.write(hints.model_dump_json(indent=4, ensure_ascii=False))

    return hints


def analyze_main_data(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: str
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
    main_data = b.GetBookMainData(
        MultiImages=baml_images,
        bookId=book_id,
        RawVisualNote=raw_visual_json,
    )

    json_path = os.path.join(output_folder, f"{book_id}_book_main_data.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json_file.write(main_data.model_dump_json(indent=4, ensure_ascii=False))

    return main_data


def analyze_publisher_details(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: str
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
    details = b.GetBookPublisherData(
        MultiImages=baml_images,
        bookId=book_id,
        RawVisualNote=raw_visual_json,
    )

    json_path = os.path.join(output_folder, f"{book_id}_book_pub_and_dist_details.json")
    with open(json_path, "w", encoding="utf-8") as json_file:
        json_file.write(details.model_dump_json(indent=4, ensure_ascii=False))

    return details


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
    book_main_dumped: dict[str, Any] = book_main.model_dump()
    book_pub_dumped: dict[str, Any] = book_pub.model_dump()
    book_condition_dumped: dict[str, Any] = book_condition.model_dump()
    book_content_dumped: dict[str, Any] = book_content.model_dump()

    return [
        {
            # organization metadata
            "book_id": book_id,
            "images_data": binary_images,
            # main data of the book
            "book_title": book_main_dumped.get("title", {}),
            "isbns": {
                "isbn_10": book_main_dumped.get("isbn_10"),
                "isbn_13": book_main_dumped.get("isbn_13"),
            },
            "language_data": {
                "languages": book_main_dumped.get("language", []),
                "scripts": book_main_dumped.get("script", []),
            },
            "authors": book_main_dumped.get("authors", []),
            "translators": book_main_dumped.get("translator", []),
            "published_year": book_pub_dumped.get("published_year", None),
            # saved the entire generation data
            "book_main_data": book_main_dumped,
            # publisher and distribution details
            "publisher_name": book_pub_dumped.get("publisher_name", {}),
            "publisher_location": book_pub_dumped.get("publisher_location", {}),
            "distributor_name": book_pub_dumped.get("distributor_name", {}),
            "distributor_location": book_pub_dumped.get("distributor_location", {}),
            # saved the entire generation data
            "book_pub_and_dist_details": book_pub_dumped,
            # book condition data
            "book_condition_summary": book_condition_dumped.get("Condition", ""),
            "print_type": book_condition_dumped.get("PrintType", ""),
            # dumping the entire generation data
            "book_condition_data": book_condition_dumped,
            # book content hints
            "book_blurb_text": book_content_dumped.get("bookBlurbText", ""),
            "bookNERData": book_content_dumped.get("bookNERData", []),
            "isFiction": book_content_dumped.get("isFiction", False),
            "book_genre": book_content_dumped.get("bookGenre", []),
            # dumping the entire content hints generation data
            "book_content_hints": book_content_dumped,
            # dumping the raw_analysis
            "raw_analysis": raw_analysis.model_dump(),
        }
    ]


def ingest_to_lancedb(
    db: DBConnection,
    table_name: str,
    data: List[Dict[str, Any]],
    mode: str = "overwrite",
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
    print(f"Adding the data to the LanceDB table '{table_name}'...")
    active_tbl = db.create_table(table_name, data=data, mode=mode)
    print("Data ingestion completed.")
    return active_tbl


def main() -> None:
    """
    Main function to orchestrate the book data extraction and ingestion process.
    """
    # Configuration
    sample_book_folder_path = "sample_data/rak-0018_baris-002_buku-12"
    output_folder_path = "data/output_book_data"
    lance_db_uri = "data/test/lance_db_semi_prod"
    table_name = "active_table_lots_columns"

    # 1. Setup
    configure_environment()
    setup_output_directory(output_folder_path)

    # 2. Initialization
    db = initialize_database(lance_db_uri)
    ip = initialize_image_processor()

    # 3. Image Processing
    images_data = process_image_folder(ip, sample_book_folder_path)

    # 4. Save Images Locally
    book_output_folder = save_images_locally(images_data, output_folder_path)

    # 5. BAML Analysis
    book_id = images_data.book_id
    baml_images = images_data.baml_images

    # Step 5a: Book Condition
    book_condition = analyze_book_condition(baml_images, book_id, book_output_folder)

    # Step 5b: Raw Analysis
    raw_analysis = run_raw_analysis(baml_images, book_id, book_output_folder)
    raw_visual_json = raw_analysis.model_dump_json()

    # Step 5c: Content Hints
    content_hints = analyze_content_hints(
        baml_images, book_id, raw_visual_json, book_output_folder
    )

    # Step 5d: Main Data
    main_data = analyze_main_data(
        baml_images, book_id, raw_visual_json, book_output_folder
    )

    # Step 5e: Publisher Details
    pub_details = analyze_publisher_details(
        baml_images, book_id, raw_visual_json, book_output_folder
    )

    # 6. Prepare for Ingestion
    data_to_ingest = prepare_data_for_ingestion(
        book_id=book_id,
        binary_images=images_data.binary_images,
        book_main=main_data,
        book_pub=pub_details,
        book_condition=book_condition,
        book_content=content_hints,
        raw_analysis=raw_analysis,
    )

    # 7. Ingest to LanceDB
    ingest_to_lancedb(db, table_name, data_to_ingest)


if __name__ == "__main__":
    main()
