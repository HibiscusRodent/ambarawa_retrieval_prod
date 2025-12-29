# ---- importing modules ----

import shutil
from venv import logger
from zipfile import Path
from image_processings import ImageProcessors, ProcessedBookImageData
from baml_client.sync_client import b
from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)


# ---- import modules for the prefect functionalities
from prefect import flow, task
from prefect.logging import get_run_logger

#---- misc modules
from dotenv import load_dotenv
from rich.traceback import install
from pathlib import Path


@task
def initiate_environment():
    env_keys_loader = load_dotenv()     # load dotenv variables for baml to access api key in the .env file
    rich_log_prettier = install()  # install rich traceback for better error logging
    logger = get_run_logger() # setting up logger for prefect
    ip = ImageProcessors()  # initiate image processor to make sure all dependencies are loaded
    
    # print info logger to make sure that necessary environment variables are loaded
    logger.info(f"Loaded environment variables: {env_keys_loader}")
    logger.info("Environment configured and variables loaded.")
    return None

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
        
def save_binary_images_to_disk(image_data: ProcessedBookImageData, output_folder: Path) -> None:
    """
    Save binary images to the specified output folder on disk.

    Args:
        binary_images: List of binary image data to be saved.
        output_folder: Path object representing the folder where images
                       will be saved.
    """
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
        ProcessedBookDict: A dictionary containing processed images and book ID.
        The dictionary has the following structure:
            {
                "book_id": str,
                "base64_images": list[str],
                "binary_images": list[bytes], wil be saved as binary images into the disk
                "baml_images": list[b.BamlImage], will be used in the BAML inference
            }
    """
    
    image_data: ProcessedBookImageData = image_processor.process_book_folder(Path(folder_path))
    logger.info(f"Processed book with id of: {image_data.book_id}")
    logger.info(f"Got a total of {len(image_data.binary_images)} images")
    return image_data
        
# the flow that encapsulates all process within the book processing data
@flow
def setup_phase_flow():
    # the environment setup phase should happen only once in the entire pararllel flow run
    initiated_environment = initiate_environment() # intiate environment
    return initiated_environment

@flow
def single_book_flow(initiated_environment, input_book_folder_path: str, output_folder_path: str) -> None:
    
    book_folder = Path(input_book_folder_path) # taking in a book folder path and validating it
    output_book_folder = Path(output_folder_path) / book_folder.name
    environment = initiated_environment  # ensuring that the environment is initiated before proceeding further
    
    # begin image processing
    image_data = process_image_folder(environment.image_processors, str(book_folder)) # process the book folder to get images data
    save_binary_images_to_disk(image_data, output_book_folder) # save the binary images to disk
    
    return None
