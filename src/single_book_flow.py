# ---- importing modules ----

from image_processings import ImageProcessors
from baml_client.sync_client import b


# ---- import modules for the prefect functionalities
from prefect import flow, task
from prefect.logging import get_run_logger

#---- misc modules
from dotenv import load_dotenv
from rich.traceback import install


def initiate_environment():
    env_keys_loader = load_dotenv()     # load dotenv variables for baml to access api key in the .env file
    rich_log_prettier = install()  # install rich traceback for better error logging
    logger = get_run_logger() # setting up logger for prefect
    
    # print info logger to make sure that necessary environment variables are loaded
    logger.info(f"Loaded environment variables: {env_keys_loader}")
    logger.info("Environment configured and variables loaded.")
    return None


# the flow that encapoolates all process within the book processing data
def single_book_flow():
    return None
