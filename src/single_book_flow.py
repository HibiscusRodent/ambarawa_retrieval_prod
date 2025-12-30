# ---- importing modules ----
from email.mime import image
from image_processings import ImageProcessors
from types_definition import (
    ProcessedBookImageData,
    AggregatedtoLanceOutput,
    construct_aggregated_lance_output,
)
from baml_client.sync_client import b
from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)

#--- lanceDB modules
from lancedb import connect

# ---- import modules for the prefect functionalities
from prefect import flow, task
from prefect.logging import get_run_logger

# ---- misc modules
from dotenv import load_dotenv
from rich.traceback import install
from pathlib import Path
from typing import Any
import shutil


logger = get_run_logger()


@task
def initiate_environment(uri: Path, lance_table_name: str):
    """
    Initialize the environment for book processing.
    Loads environment variables, sets up rich traceback, initializes logger
    and ImageProcessors to ensure all dependencies are loaded.

    Returns:
        None
    """
    env_loader = load_dotenv()  # load dotenv variables for baml to access api key in the .env file
    rich_traceback_printer = install()  # install rich traceback for better error logging
    logger = get_run_logger()  # setting up logger for prefect
    image_processors = ImageProcessors()  # initiate image processor to make sure all dependencies are loaded

    active_lance_db = connect(uri)
    logger.info(f"Connected to LanceDB at: {uri}")
    
    # create a lance table
    # throw an error to a logger if the table already exists
    try:
        lance_table = active_lance_db.create_table(lance_table_name, schema=AggregatedtoLanceOutput)
        logger.info(f"Created LanceDB table: {lance_table_name} with schema: {AggregatedtoLanceOutput}")
    except Exception as e:
        logger.warning(f"LanceDB table {lance_table_name} might already exist. Error: {str(e)}")
        logger.info(f"Here's the list of available tables at {uri}: {active_lance_db.list_tables()}")
    
    # print info logger to make sure that necessary environment variables are loaded
    logger.info("Environment configured, variables and lanceDB loaded.")
    return image_processors, active_lance_db


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
    with output_path.open("w", encoding="utf-8") as f:
        f.write(data.model_dump_json(indent=4, ensure_ascii=False))


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
    image_data: ProcessedBookImageData = image_processor.process_book_folder(
        Path(folder_path)
    )
    logger.info(f"Processed book with id of: {image_data.book_id}")
    logger.info(f"Got a total of {len(image_data.binary_images)} images")
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
    return BookConditionData.model_construct()


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
    try:
        logger.info("Starting book condition analysis for Book ID: %s", book_id)
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
    return RawAnalysis.model_construct()


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
        return BookContentHints.model_construct()


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
        return BookMainData.model_construct()


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
        return BookPubAndDistDetails.model_construct()


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
    logger.info("Constructing aggregated lance output for Book ID: %s", book_id)

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

# lanceDB ingestion phases
@task
def ingest_to_lance_db(active_lance_db,, table_name: str, tobe_ingested_data: AggregatedtoLanceOutput):
    """
    Ingest data into LanceDB. It takes in the constructed aggregated output data and
    writes it into the specified LanceDB table. The table has to be pre-created with the
    appropriate schema that matches the AggregatedtoLanceOutput structure.

    Args:
        active_lance_db: The LanceDB connection.
        table_name: The name of the table.
        tobe_ingested_data: The data to ingest.
        mode: The write mode ('overwrite', 'append', etc.).

    Returns:
        Any: The table object.
    """
    logger.info("Ingesting data into LanceDB table: %s", table_name)
    
    # open a table from the active lance database
    lance_table = active_lance_db.get_table(table_name)

# run the environment setup phase only once in the place where the flow is being called
def setup_phase_flow(uri: Path, lance_table_name: str):
    # the environment setup phase should happen only once in the entire pararllel flow run
    initiated_environment = initiate_environment(uri, lance_table_name)  # intiate environment
    return initiated_environment


# the flow that encapsulates all process within the book processing data
@flow
def single_book_flow(
    initiated_environment, input_book_folder_path: str, output_folder_path: str
) -> None:
    book_folder = Path(
        input_book_folder_path
    )  # taking in a book folder path and validating it
    output_book_folder = Path(output_folder_path) / book_folder.name
    environment = initiated_environment  # ensuring that the environment is initiated before proceeding further

    # begin image processing
    image_data = process_image_folder(
        environment.image_processors, str(book_folder)
    )  # process the book folder to get images data
    save_binary_images_to_disk(
        image_data, output_book_folder
    )  # save the binary images to disk

    # main BAML inference phase
    baml_images = (
        image_data.baml_images
    )  # extract baml images from the processed image data
    book_id = image_data.book_id  # extract book id from the processed image

    # first phase of the inference, the two runs in parallel
    book_condition_data = analyze_book_condition(baml_images, book_id, output_book_folder)
    
    raw_analysis_data_json = run_raw_analysis(baml_images, book_id, output_book_folder).model_dump_json()

    # second phase of the inference, dependent on the raw analysis result
    # the three analysis runs in parallel
    contetent_hints_data = analyze_content_hints(baml_images, book_id, raw_analysis_data_json, output_book_folder)
    main_data = analyze_main_data(baml_images, book_id, raw_analysis_data_json, output_book_folder)
    publisher_details_data = analyze_publisher_details(baml_images, book_id, raw_analysis_data_json, output_book_folder)
    
    # construct aggregated data for ingestion
    aggregated_output = prepare_data_for_ingestion(
        book_id=book_id,
        binary_images=image_data.binary_images,
        book_condition_data=book_condition_data,
        raw_analysis_data=RawAnalysis.model_validate_json(raw_analysis_data_json),
        content_hints_data=contetent_hints_data,
        main_data=main_data,
        publisher_details_data=publisher_details_data,
    )
    
    
    
    return None
