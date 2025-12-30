from pydantic import BaseModel, ConfigDict
from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)

from baml_py import Image as BamlImage



class ProcessedBookImageData(BaseModel):
    """
    Pydantic model representing the return type for processed book data.

    Fields:
        book_id: The unique identifier of the book, typically the folder name.
        base64_images: A list of base64-encoded strings representing the processed images.
                      These are optimized for storage in columnar formats like LanceDB.
        binary_images: A list of raw binary bytes representing the processed images.
                      These are optimized for direct usage with AI model APIs.
        baml_images: A list of BAML Image objects created from the base64 images.
                    These are suitable for passing directly into BAML functions that accept images.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    book_id: str
    base64_images: list[str]
    binary_images: list[bytes]
    baml_images: list[BamlImage]

class AggregatedtoLanceOutput(BaseModel):
    """
    A pydantic basemodel that takes in the aggregated data for a book,
    obtained from the the image processing steps, and also the BAML
    based inference results.
    """
    book_id: str
    images_data: list[bytes]
    book_title: BookMainData.authors
    
    
    
    book_condition_data: BookConditionData
    raw_analysis: RawAnalysis
    book_content_hints: BookContentHints
    book_main_data: BookMainData
    book_pub_and_dist_details: BookPubAndDistDetails