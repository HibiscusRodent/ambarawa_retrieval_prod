from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from baml_client.types import (
    BookConditionData,
    BookConditionEnum,
    BookPrintTypeEnum,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
    BookTitle,
    BookAuthor,
    BookTranslator,
    PublisherName,
    PublisherLocation,
    DistributorName,
    DistributorLocation,
)

from baml_py import Image as BamlImage


class ISBNData(BaseModel):
    """
    Container for ISBN-10 and ISBN-13 identifiers.
    """

    isbn_10: Optional[str] = Field(
        default=None, description="The 10-digit ISBN if available"
    )
    isbn_13: Optional[str] = Field(
        default=None, description="The 13-digit ISBN if available"
    )


class LanguageData(BaseModel):
    """
    Container for language and script information.
    """

    languages: list[str] = Field(
        default_factory=list, description="List of languages identified in the book"
    )
    scripts: list[str] = Field(
        default_factory=list, description="List of scripts/writing systems used"
    )


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
    A Pydantic BaseModel that aggregates all book data for ingestion into LanceDB.

    This model combines data from image processing and BAML-based inference results,
    structured for optimal storage and querying in LanceDB. It follows the same
    structure as the data_to_ingest dictionary but uses strong typing via Pydantic.

    The model is designed to work with the improved pydantic-to-schema conversion
    in the types_utils module, allowing direct usage with LanceDB tables.

    Fields:
        book_id: Unique identifier for the book (typically folder name).
        images_data: List of binary image data for the book.
        book_title: Structured book title information in multiple scripts/languages.
        isbns: Container for ISBN-10 and ISBN-13 identifiers.
        language_data: Container for languages and scripts used in the book.
        authors: List of author information in multiple scripts.
        translators: List of translator information if applicable.
        published_year: Year of publication if available.
        book_main_data: Complete main book data from BAML analysis.
        publisher_name: Publisher name in multiple scripts/languages.
        publisher_location: Publisher location information.
        distributor_name: Distributor name if different from publisher.
        distributor_location: Distributor location if applicable.
        book_pub_and_dist_details: Complete publisher and distributor data.
        book_condition_summary: Overall condition rating enum value.
        print_type: Type of print (hardcover, paperback, etc.).
        book_condition_data: Complete condition analysis data.
        book_blurb_text: Extracted book blurb/description if available.
        bookNERData: Named Entity Recognition data extracted from content.
        isFiction: Boolean indicating if the book is fiction.
        book_genre: List of genre classifications.
        book_content_hints: Complete content analysis data.
        raw_analysis: Raw visual analysis from initial image processing.
    """

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
    )

    # Core identification and image data
    book_id: str = Field(description="Unique identifier for the book")
    images_data: list[bytes] = Field(
        description="Binary image data for all book images"
    )

    # Extracted and structured metadata
    book_title: BookTitle = Field(description="Book title in multiple scripts")
    isbns: ISBNData = Field(default_factory=ISBNData, description="ISBN identifiers")
    language_data: LanguageData = Field(
        default_factory=LanguageData, description="Language and script information"
    )
    authors: list[BookAuthor] = Field(
        default_factory=list, description="List of book authors"
    )
    translators: Optional[list[BookTranslator]] = Field(
        default=None, description="List of translators if applicable"
    )
    published_year: Optional[int] = Field(
        default=None, description="Year of publication"
    )

    # Complete structured data from BAML analysis
    book_main_data: BookMainData = Field(
        description="Complete main book data from BAML analysis"
    )

    # Publisher and distributor information
    publisher_name: PublisherName = Field(
        description="Publisher name in multiple formats"
    )
    publisher_location: PublisherLocation = Field(
        description="Publisher location details"
    )
    distributor_name: Optional[DistributorName] = Field(
        default=None, description="Distributor name if different from publisher"
    )
    distributor_location: Optional[DistributorLocation] = Field(
        default=None, description="Distributor location if applicable"
    )
    book_pub_and_dist_details: BookPubAndDistDetails = Field(
        description="Complete publisher and distributor data"
    )

    # Condition and physical attributes
    book_condition_summary: BookConditionEnum = Field(
        description="Overall condition rating"
    )
    print_type: BookPrintTypeEnum = Field(
        description="Type of print (hardcover, paperback, etc.)"
    )
    book_condition_data: BookConditionData = Field(
        description="Complete condition analysis"
    )

    # Content analysis
    book_blurb_text: Optional[str] = Field(
        default=None, description="Extracted book blurb/description"
    )
    bookNERData: list[str] = Field(
        default_factory=list, description="Named entities extracted from content"
    )
    isFiction: bool = Field(description="Whether the book is fiction")
    book_genre: list[str] = Field(
        default_factory=list, description="List of genre classifications"
    )
    book_content_hints: BookContentHints = Field(
        description="Complete content analysis data"
    )

    # Raw analysis
    raw_analysis: RawAnalysis = Field(
        description="Raw visual analysis from initial processing"
    )


def construct_aggregated_lance_output(
    book_id: str,
    binary_images: list[bytes],
    book_main: BookMainData,
    book_pub: BookPubAndDistDetails,
    book_condition: BookConditionData,
    book_content: BookContentHints,
    raw_analysis: RawAnalysis,
) -> AggregatedtoLanceOutput:
    """
    Construct an AggregatedtoLanceOutput from individual BAML analysis results.

    This function aggregates data from multiple BAML inference tasks into a single
    validated Pydantic model ready for LanceDB ingestion. It mirrors the structure
    of the prepare_data_for_ingestion function but returns a strongly-typed
    Pydantic model instead of a dictionary.

    Args:
        book_id: Unique identifier for the book (typically folder name).
        binary_images: List of binary image data for the book.
        book_main: Main book data from BAML analysis including title, authors, language, etc.
        book_pub: Publisher and distributor details from BAML analysis.
        book_condition: Book condition and print type analysis from BAML.
        book_content: Content hints including genre, fiction status, and NER data.
        raw_analysis: Raw visual analysis descriptions from initial image processing.

    Returns:
        AggregatedtoLanceOutput: A validated Pydantic model containing all aggregated data.

    Example:
        >>> output = construct_aggregated_lance_output(
        ...     book_id="rak-001_baris-002_buku-003",
        ...     binary_images=[b"image_data_1", b"image_data_2"],
        ...     book_main=main_data,
        ...     book_pub=pub_data,
        ...     book_condition=condition_data,
        ...     book_content=content_data,
        ...     raw_analysis=raw_data,
        ... )
        >>> print(output.book_id)
        'rak-001_baris-002_buku-003'
    """
    # Construct ISBN data
    isbns = ISBNData(
        isbn_10=book_main.isbn_10,
        isbn_13=book_main.isbn_13,
    )

    # Construct language data
    language_data = LanguageData(
        languages=book_main.language,
        scripts=book_main.script,
    )

    # Create the aggregated output
    return AggregatedtoLanceOutput(
        book_id=book_id,
        images_data=binary_images,
        book_title=book_main.title,
        isbns=isbns,
        language_data=language_data,
        authors=book_main.authors,
        translators=book_main.translator,
        published_year=book_main.published_year,
        book_main_data=book_main,
        publisher_name=book_pub.publisher_name,
        publisher_location=book_pub.publisher_location,
        distributor_name=book_pub.distributor_name,
        distributor_location=book_pub.distributor_location,
        book_pub_and_dist_details=book_pub,
        book_condition_summary=book_condition.Condition,
        print_type=book_condition.PrintType,
        book_condition_data=book_condition,
        book_blurb_text=book_content.bookBlurbText,
        bookNERData=book_content.bookNERData,
        isFiction=book_content.isFiction,
        book_genre=book_content.bookGenre,
        book_content_hints=book_content,
        raw_analysis=raw_analysis,
    )
