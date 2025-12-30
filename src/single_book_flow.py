# ---- importing modules ----
from image_processings import ImageProcessors
from types_definition import (
    ProcessedBookImageData,
    AggregatedtoLanceOutput,
    construct_aggregated_lance_output,
)
from types_utils import pydantic_to_arrow_schema
from baml_client.sync_client import b
from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)

# --- lanceDB modules
from lancedb import connect
import pyarrow as pa

# ---- import modules for the prefect functionalities
from prefect import flow, task
from prefect.logging import get_run_logger
from prefect.cache_policies import NO_CACHE

# ---- misc modules
from dotenv import load_dotenv
from rich.traceback import install
from pathlib import Path
from typing import Any, NamedTuple
import shutil


class InitializedEnvironment(NamedTuple):
    """Container for initialized environment components."""

    image_processors: ImageProcessors
    active_lance_db: Any
    lance_table_name: str


@task
def initiate_environment(uri: Path, lance_table_name: str) -> InitializedEnvironment:
    """
    Initialize the environment for book processing.
    Loads environment variables, sets up rich traceback, initializes logger
    and ImageProcessors to ensure all dependencies are loaded.

    Args:
        uri: Path to the LanceDB database.
        lance_table_name: Name of the LanceDB table to create or use.

    Returns:
        InitializedEnvironment: A NamedTuple containing initialized components.
    """
    logger = get_run_logger()
    logger.info("========== Environment Initialization ==========")

    logger.info("Loading environment variables...")
    env_loader = load_dotenv()
    logger.debug("Environment variables loaded: %s", env_loader)

    logger.info("Installing rich traceback handler...")
    install()

    logger.info("Initializing ImageProcessors...")
    image_processors = ImageProcessors()
    logger.info("ImageProcessors initialized successfully")

    logger.info("Connecting to LanceDB at: %s", uri)
    active_lance_db = connect(uri)
    logger.info("Connected to LanceDB successfully")

    # create a lance table
    try:
        logger.info("Attempting to create LanceDB table: %s", lance_table_name)
        # Convert Pydantic model to PyArrow schema
        arrow_schema = pydantic_to_arrow_schema(AggregatedtoLanceOutput)
        logger.debug("Generated PyArrow schema for AggregatedtoLanceOutput")
        _ = active_lance_db.create_table(lance_table_name, schema=arrow_schema)
        logger.info(
            "Created LanceDB table: %s with schema: %s",
            lance_table_name,
            AggregatedtoLanceOutput.__name__,
        )
    except Exception as e:
        logger.warning(
            "LanceDB table %s might already exist. Error: %s", lance_table_name, str(e)
        )
        available_tables = active_lance_db.table_names()
        logger.info("Available tables at %s: %s", uri, available_tables)
        if lance_table_name not in available_tables:
            logger.error(
                "Table %s does not exist and creation failed", lance_table_name
            )
            raise

    logger.info("========== Environment Initialization Complete ==========")
    return InitializedEnvironment(
        image_processors=image_processors,
        active_lance_db=active_lance_db,
        lance_table_name=lance_table_name,
    )


# utilities functions to save data to disk
@task
def save_to_json(data, output_path):
    """
    Saving a Pydantic model to a JSON file on the disk, with proper formatting.
    Will save the file with UTF-8 encoding to handle special characters, at
    the specified output path.

    Args:
        data: Pydantic model instance to be saved.
        output_path: Path object representing the file path where the JSON
                     will be saved.
    """
    logger = get_run_logger()
    logger.debug("Saving data to JSON file: %s", output_path)

    try:
        with output_path.open("w", encoding="utf-8") as f:
            f.write(data.model_dump_json(indent=4, ensure_ascii=False))
        logger.debug("Successfully saved JSON file: %s", output_path)
    except Exception as e:
        logger.exception("Failed to save JSON file: %s, Error: %s", output_path, str(e))
        raise


@task
def save_binary_images_to_disk(
    image_data: ProcessedBookImageData, output_folder: Path
) -> None:
    """
    Save binary images to the specified output folder on disk.

    Args:
        image_data: ProcessedBookImageData containing binary images and book ID.
        output_folder: Path object representing the folder where images
                       will be saved.
    """
    logger = get_run_logger()
    book_id: str = image_data.book_id
    book_output_folder: Path = output_folder / book_id

    # Efficiently clear existing images or create folder
    if book_output_folder.exists():
        logger.info("Clearing existing output folder: %s", str(book_output_folder))
        shutil.rmtree(book_output_folder)
    book_output_folder.mkdir(parents=True, exist_ok=True)

    # Write binary images
    for idx, img_data in enumerate(image_data.binary_images):
        img_file_path: Path = book_output_folder / f"{book_id}_img_{idx + 1:03d}.jpg"
        img_file_path.write_bytes(img_data)

    logger.info(
        "Saved images locally - Book ID: %s, Path: %s, Image Count: %d",
        book_id,
        str(book_output_folder),
        len(image_data.binary_images),
    )
    return None


# inference related tasks
@task
def process_image_folder(image_processor: ImageProcessors, folder_path: str):
    """
    Process a book folder containing images using the provided ImageProcessors instance.
    Return images data as a ProcessedBookImageData, which includes base64, binary, and BAML images.

    Args:
        image_processor: An instance of ImageProcessors to handle the processing.
        folder_path: Path to the folder containing book images.

    Returns:
        ProcessedBookImageData: A data class containing processed images and book ID.
    """
    logger = get_run_logger()
    logger.info("Starting image processing for folder: %s", folder_path)

    image_data: ProcessedBookImageData = image_processor.process_book_folder(
        Path(folder_path)
    )

    logger.info(
        "Processed book with ID: %s, Image Count: %d",
        image_data.book_id,
        len(image_data.binary_images),
    )
    return image_data


# baml inference tasks
@task
def analyze_book_condition(
    baml_images, book_id: str, output_folder: Path
) -> BookConditionData:
    """
    Analyze the book condition using BAML client and return the BookConditionData.

    Args:
        baml_images: List of BAML-compatible images for analysis.
        book_id: The ID of the book being analyzed.
        output_folder: Path to the folder where output data will be saved.

    Returns:
        BookConditionData: The analyzed book condition data.
    """
    logger = get_run_logger()
    try:
        logger.info("Starting book condition analysis for Book ID: %s", book_id)
        data = b.GetBookConditionData(MultiImages=baml_images, bookId=book_id)
        save_to_json(data, output_folder / f"{book_id}_book_condition_data.json")

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
        raise  # Re-raise to properly propagate the error


@task
def run_raw_analysis(baml_images, book_id: str, output_folder: Path) -> RawAnalysis:
    """
    Infer the visual raw analysis of the book using BAML client and return the RawAnalysis.
    The results of the analysis will be used in further processing steps as a way to enrich the book data.
    The resulting outoput will also be saved to disk as a JSON file for future reference,
    and into the main dataframe aggregation down the line.

    Args:
        baml_images: List of BAML-compatible images for analysis.
        book_id: The ID of the book being analyzed.
        output_folder: Path to the folder where output data will be saved.

    Returns:
        RawAnalysis: The analyzed raw analysis data.
    """
    logger = get_run_logger()
    try:
        logger.info("Starting raw visual analysis for Book ID: %s", book_id)
        raw_analysis_data = b.GetBookrawVisual(MultiImages=baml_images, bookId=book_id)
        save_to_json(
            raw_analysis_data, output_folder / f"{book_id}_book_condition_data.json"
        )

        logger.info(
            "Analyzed raw visual analysis - Book ID: %s, Condition: %s, Print Type: %s",
            book_id,
            bool(raw_analysis_data.coverPageDescription),
            bool(raw_analysis_data.backCoverDescription),
        )
        return raw_analysis_data
    except Exception as e:
        logger.exception(
            "Failed to analyze raw visual analysis - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        raise  # Re-raise to properly propagate the error


@task
def analyze_content_hints(
    baml_images: Any, book_id: str, raw_visual_data_json: str, output_folder: Path
) -> BookContentHints:
    """
    Generate content hints using BAML and save the result. It takes in
    a raw visual analysis data in string format to enrich the content hints generation.

    Args:
        baml_images: The BAML-formatted images.
        book_id: The ID of the book.
        raw_visual_visual_data: data from the raw visual analysis.
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
            RawVisualNote=raw_visual_data_json,
        )
        save_to_json(hints, output_folder / f"{book_id}_book_content_hints.json")

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
        raise  # Re-raise to properly propagate the error


@task
def analyze_main_data(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: Path
) -> BookMainData:
    """
    Extract main book data using BAML and save the result. It takes in also a
    raw visual analysis data in string format to enrich the main data extraction.

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
        save_to_json(main_data, output_folder / f"{book_id}_book_main_data.json")

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
        raise  # Re-raise to properly propagate the error


@task
def analyze_publisher_details(
    baml_images: Any, book_id: str, raw_visual_json: str, output_folder: Path
) -> BookPubAndDistDetails:
    """
    Extract publisher and distributor details using BAML and save the result.
    Takes in halso a raw visual analysis data in string format to enrich the extraction.

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

        save_to_json(
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
        raise  # Re-raise to properly propagate the error


@task
def prepare_data_for_ingestion(
    book_id: str,
    binary_images: list[bytes],
    book_condition_data: BookConditionData,
    raw_analysis_data: RawAnalysis,
    content_hints_data: BookContentHints,
    main_data: BookMainData,
    publisher_details_data: BookPubAndDistDetails,
) -> AggregatedtoLanceOutput:
    """
    Prepare and aggregate data for ingestion into the Lance format.

    This function uses the construct_aggregated_lance_output helper to create
    a strongly-typed Pydantic model from the various BAML analysis results.
    The returned model is validated and ready for direct ingestion into LanceDB
    using the improved pydantic-to-schema conversion from the types_utils module.

    Arguments:
        book_id: The ID of the book.
        binary_images: List of binary images of the book.
        book_condition_data: Analyzed book condition data.
        raw_analysis_data: Analyzed raw visual analysis data.
        content_hints_data: Analyzed content hints data.
        main_data: Analyzed main book data.
        publisher_details_data: Analyzed publisher and distributor details data.

    Returns:
        AggregatedtoLanceOutput: The aggregated, validated data ready for ingestion.
    """
    logger = get_run_logger()
    logger.info("Starting data aggregation for Book ID: %s", book_id)
    logger.debug(
        "Processing %d binary images for Book ID: %s", len(binary_images), book_id
    )

    try:
        aggregated_output = construct_aggregated_lance_output(
            book_id=book_id,
            binary_images=binary_images,
            book_main=main_data,
            book_pub=publisher_details_data,
            book_condition=book_condition_data,
            book_content=content_hints_data,
            raw_analysis=raw_analysis_data,
        )

        logger.info(
            "Successfully constructed aggregated output - Book ID: %s, Title: %s",
            book_id,
            aggregated_output.book_title.title_in_latin_script,
        )
        return aggregated_output
    except Exception as e:
        logger.exception(
            "Failed to construct aggregated output - Book ID: %s, Error: %s (Exception type: %s)",
            book_id,
            str(e),
            type(e).__name__,
        )
        raise


# lanceDB ingestion phases
@task(cache_policy=NO_CACHE)
def ingest_to_lance_db(
    active_lance_db, table_name: str, tobe_ingested_data: AggregatedtoLanceOutput
):
    """
    Ingest data into LanceDB. It takes in the constructed aggregated output data and
    writes it into the specified LanceDB table. The table has to be pre-created with the
    appropriate schema that matches the AggregatedtoLanceOutput structure.

    This function explicitly converts the Pydantic model to a PyArrow Table with the
    correct schema to avoid type inference issues with nested structs.

    Args:
        active_lance_db: The LanceDB connection.
        table_name: The name of the table.
        tobe_ingested_data: The data to ingest.

    Returns:
        Any: The table object.
    """
    logger = get_run_logger()
    logger.info(
        "Starting LanceDB ingestion - Table: %s, Book ID: %s",
        table_name,
        tobe_ingested_data.book_id,
    )

    try:
        # open a table from the active lance database
        lance_table = active_lance_db.open_table(table_name)
        logger.debug("Successfully opened LanceDB table: %s", table_name)

        # Convert the Pydantic model to a dictionary
        data_dict = tobe_ingested_data.model_dump()

        # Get the proper PyArrow schema for our model
        # This ensures nested Pydantic models are correctly converted to struct types
        arrow_schema = pydantic_to_arrow_schema(AggregatedtoLanceOutput)

        # Create a PyArrow Table with the explicit schema
        # This prevents PyArrow from incorrectly inferring nested types
        pa_table = pa.Table.from_pylist([data_dict], schema=arrow_schema)

        # Add the properly-typed PyArrow Table to LanceDB
        lance_table.add(pa_table)
        logger.info(
            "Successfully ingested data - Book ID: %s, Table: %s",
            tobe_ingested_data.book_id,
            table_name,
        )
        return lance_table
    except Exception as e:
        logger.exception(
            "Failed to ingest data - Book ID: %s, Table: %s, Error: %s (Exception type: %s)",
            tobe_ingested_data.book_id,
            table_name,
            str(e),
            type(e).__name__,
        )
        raise


# run the environment setup phase only once in the place where the flow is being called


def setup_phase_flow(uri: Path, lance_table_name: str) -> InitializedEnvironment:
    """
    Initialize the environment setup phase for the book processing pipeline.
    This should only be called once per pipeline run.

    Args:
        uri: Path to the LanceDB database.
        lance_table_name: Name of the LanceDB table to create or use.

    Returns:
        InitializedEnvironment: Initialized environment with all necessary components.
    """
    print("Starting environment setup phase flow")

    initiated_environment = initiate_environment(uri, lance_table_name)

    print("Environment setup phase completed successfully")
    return initiated_environment


# the flow that encapsulates all process within the book processing data
@flow
def single_book_flow(
    initiated_environment, input_book_folder_path: str, output_folder_path: str
) -> None:
    """Main flow to process a single book folder through the entire analysis pipeline.

    Args:
        initiated_environment: Initialized environment containing image processors and LanceDB connection.
        input_book_folder_path: Path to the folder containing book images.
        output_folder_path: Path where output data will be saved.
    """
    logger = get_run_logger()
    logger.info("========== Starting Single Book Flow ==========")
    logger.info("Input folder: %s", input_book_folder_path)
    logger.info("Output folder: %s", output_folder_path)

    book_folder = Path(input_book_folder_path)
    output_book_folder = Path(output_folder_path) / book_folder.name
    environment = initiated_environment

    logger.info("Creating output directory: %s", output_book_folder)
    output_book_folder.mkdir(parents=True, exist_ok=True)

    # Phase 1: Image Processing
    logger.info("========== Phase 1: Image Processing ==========")
    image_data = process_image_folder(environment.image_processors, str(book_folder))
    save_binary_images_to_disk(image_data, output_book_folder)

    # Extract common variables
    baml_images = image_data.baml_images
    book_id = image_data.book_id
    logger.info("Processing Book ID: %s", book_id)

    # Phase 2: First BAML Inference (parallel-capable tasks)
    logger.info("========== Phase 2: First BAML Inference ==========")
    logger.info("Running book condition and raw analysis in parallel")
    book_condition_data = analyze_book_condition(
        baml_images, book_id, output_book_folder
    )

    raw_analysis_data = run_raw_analysis(baml_images, book_id, output_book_folder)
    raw_analysis_data_json = raw_analysis_data.model_dump_json()

    # Phase 3: Second BAML Inference (dependent on raw analysis)
    logger.info("========== Phase 3: Second BAML Inference ==========")
    logger.info("Running content hints, main data, and publisher details analysis")
    contetent_hints_data = analyze_content_hints(
        baml_images, book_id, raw_analysis_data_json, output_book_folder
    )
    main_data = analyze_main_data(
        baml_images, book_id, raw_analysis_data_json, output_book_folder
    )
    publisher_details_data = analyze_publisher_details(
        baml_images, book_id, raw_analysis_data_json, output_book_folder
    )

    # Phase 4: Data Aggregation
    logger.info("========== Phase 4: Data Aggregation ==========")
    aggregated_output = prepare_data_for_ingestion(
        book_id=book_id,
        binary_images=image_data.binary_images,
        book_condition_data=book_condition_data,
        raw_analysis_data=raw_analysis_data,
        content_hints_data=contetent_hints_data,
        main_data=main_data,
        publisher_details_data=publisher_details_data,
    )

    # Phase 5: LanceDB Ingestion
    logger.info("========== Phase 5: LanceDB Ingestion ==========")
    ingest_to_lance_db(
        environment.active_lance_db, environment.lance_table_name, aggregated_output
    )  # pyright: ignore[reportUnusedCoroutine]

    logger.info("========== Single Book Flow Completed Successfully ==========")
    logger.info(
        "Book ID: %s processed and ingested into table: %s",
        book_id,
        environment.lance_table_name,
    )
    return None


def example_run():
    """Example flow demonstrating single book processing."""

    lance_db_path = Path("data/lance_db_test")
    lance_table_name = "books_test_table"
    input_book_folder_path = Path(
        "D:/projects/ambarawa_retrieval_prod/sample_data/rak-0003_baris-005_buku-30"
    )

    setup_phase_flow_instance = setup_phase_flow(lance_db_path, lance_table_name)
    single_book_flow(
        setup_phase_flow_instance, str(input_book_folder_path), "data/output"
    )

    return None


if __name__ == "__main__":
    example_run()
