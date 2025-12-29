# ---- importing modules ----

from image_processings import ImageProcessors
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

@task
def initiate_environment():
    env_keys_loader = load_dotenv()     # load dotenv variables for baml to access api key in the .env file
    rich_log_prettier = install()  # install rich traceback for better error logging
    logger = get_run_logger() # setting up logger for prefect
    
    # print info logger to make sure that necessary environment variables are loaded
    logger.info(f"Loaded environment variables: {env_keys_loader}")
    logger.info("Environment configured and variables loaded.")
    return None

@task
def setup_output_directory(output_path):
    output_path.mkdir(parents=True, exist_ok=True)
    pass

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
# the flow that encapoolates all process within the book processing data
@flow
def single_book_flow():
    # intiate environment
    initiate_environment()
    
    return None
