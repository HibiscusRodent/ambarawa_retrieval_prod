import os

# lanceDB imports
import lancedb
from lancedb.db import DBConnection

# image processings imports
from image_processors import (
    ImageProcessors,
    BookFolderPathData,
    ProcessedBookData,
)

# BAML imports
from baml_client.sync_client import b
from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)
from typing import Any

# logfire imports
from logfire import Logfire, Logfire
from dotenv import load_dotenv

# define mainInference class
class mainInference:
    def __init__(self, lanceDB_Uri):
        
        # init logfire logging
        self.logfire = Logfire()
        
        # init the image processors
        self.ip = self.ImageProcessorsInitiation()
        
        # setting lanceDB connection
        self.lanceDB_connection: DBConnection = lancedb.connect(lanceDB_Uri)
        
    def ImageProcessorsInitiation(self):
        # initiating the image processors class, before the function is called
        ip: ImageProcessors = ImageProcessors(
            dpi=150,
            resizing_filter="LANCZOS",
            quality=85,
            webp_method=4,
            binary_quality=85,
            binary_format="WEBP",
            binary_webp_method=4,
            images_extensions=[".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"],
            pdf_extensions=[".pdf"],
            n_jobs=-1,
        )
        return ip
    
    def InputFolderSingle(self, single_book_folder_path):
        """
        Takes in a single folder path containing books data and validate the
        path so that it can be used for processing.

        Args:
            single_book_folder_path (str): the path to the single book folder

        Returns:
            single_book_folder_path (BookFolderPathData): the validated path to 
            the single book folder
        """
        single_book_folder_path = BookFolderPathData(path = single_book_folder_path)
        return single_book_folder_path
    
    def ImagesData (self, single_book_folder_path):
        """
        This function takes in a single book folder path, and returns the processed book data.
        In the form of an object containing three separate data:
            - book_id: str
            - baml_images: list[Image]
            - binary_images: list[bytes]

        Args:
            single_book_folder_path (BookFolderPathData): the path to the single book folder

        Returns:
            images_data (ProcessedBookData): the processed book data
        """
        images_data: ProcessedBookData = self.ip.process_book_folder(single_book_folder_path)
        return images_data

    def 
# create a main function to guard the mainInference class

def main():
    pass

if __name__ == "__main__":
    main()