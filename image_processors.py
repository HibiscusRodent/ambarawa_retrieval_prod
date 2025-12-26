# file handling libraries
from pathlib import Path

# libraries for handling format conversions
# and also image processings, including PDFs
import base64
import PIL.Image
import pymupdf as fitz
import io


# misc libraries
from typing import Literal, cast
from pydantic import BaseModel, ConfigDict, Field

from baml_py import Image as BamlImage

from prefect.logging import get_run_logger
import psutil
import os

# for parallelizations
from joblib import Parallel, delayed

# rich traceback to show better debugging display
from rich.traceback import install

install()  # activate pretty error printing using rich traceback


class BookFolderPathData(BaseModel):
    """
    Pydantic model representing the input data required for book folder processing.

    This class encapsulates the filesystem path to a book folder and provides
    utility properties to extract book metadata, such as the book ID.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    path: Path = Field(
        ...,
        description="The absolute or relative Path object pointing to the book folder.",
    )

    @property
    def book_id(self) -> str:
        """
        Extracts and returns the book ID based on the folder name.

        Returns:
            str: The name of the directory which serves as the unique identifier for the book.
        """
        return self.path.name


class ProcessedBookData(BaseModel):
    """
    Pydantic model representing the output data after processing a book folder.

    This class holds the results of image processing, including various data formats
    (base64 and binary) suitable for different downstream tasks like vector database
    insertion or LLM inference.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    book_id: str = Field(
        ..., description="The unique identifier of the book, typically the folder name."
    )
    base64_images: list[str] = Field(
        ...,
        description="A list of base64-encoded strings representing the processed images. "
        "These are optimized for storage in columnar formats like LanceDB.",
    )
    binary_images: list[bytes] = Field(
        ...,
        description="A list of raw binary bytes representing the processed images. "
        "These are optimized for direct usage with AI model APIs.",
    )

    baml_images: list[BamlImage] = Field(
        default_factory=list,
        description="A list of BAML Image objects created from the base64 images. "
        "These are suitable for passing directly into BAML functions that accept images.",
    )


class ImageProcessors:
    """
    A class for processing images and PDFs, including loading, resizing,
    and converting to various formats (numpy arrays, base64, binary). Some of the key functions within the class:
    1. end-to-end processing of images from a book folder: taking in a path to a book folder and returning their id, base64 images, and binary images
    2. loading images and PDFs
    3. resizing images
    4. converting images to base64 and binary data

    """

    def __init__(
        self,
        dpi: int = 150,
        max_size: tuple[int, int] = (800, 800),
        resizing_filter: Literal[
            "LANCZOS", "BILINEAR", "BICUBIC", "NEAREST"
        ] = "LANCZOS",
        quality: int = 85,
        webp_method: int = 4,
        binary_quality: int = 85,
        binary_format: str = "WEBP",
        binary_webp_method: int = 4,
        images_extensions: list[str] | None = None,
        pdf_extensions: list[str] | None = None,
        n_jobs: int = -1,
    ) -> None:
        """
        Initialize the ImageProcessors with configuration parameters.

        Args:
            dpi: DPI for PDF rendering (default: 150)
            max_size: Maximum size for resized images (default: (800, 800))
            resizing_filter: PIL resampling filter (default: "LANCZOS")
            quality: JPEG/WEBP quality for base64 encoding (default: 85)
            webp_method: WEBP compression method 0-6 (default: 4)
            binary_quality: Quality for binary encoding (default: 85)
            binary_format: Image format for binary data (default: "WEBP")
            binary_webp_method: WEBP method for binary encoding (default: 4)
            images_extensions: Supported image extensions (default: common formats)
            pdf_extensions: Supported PDF extensions (default: [".pdf"])
            n_jobs: Number of parallel jobs for joblib (default: -1, all CPUs)
        """
        self.dpi = dpi
        self.max_size = max_size
        self.resizing_filter = resizing_filter
        self.quality = quality
        self.webp_method = webp_method
        self.binary_quality = binary_quality
        self.binary_format = binary_format
        self.binary_webp_method = binary_webp_method
        self.n_jobs = n_jobs

        # Set default extensions if not provided
        self.images_extensions = images_extensions or [
            ".jpg",
            ".jpeg",
            ".png",
            ".bmp",
            ".tiff",
            ".tif",
            ".webp",
        ]
        self.pdf_extensions = pdf_extensions or [".pdf"]

        # Normalize extensions to lowercase
        self.images_extensions = [ext.lower() for ext in self.images_extensions]
        self.pdf_extensions = [ext.lower() for ext in self.pdf_extensions]

    @staticmethod
    def _get_memory_usage_mb() -> float:
        """Get current memory usage in megabytes (RSS)."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)

    @property
    def supported_extensions(self) -> set[str]:
        """Get all supported file extensions."""
        return set(self.images_extensions + self.pdf_extensions)

    def get_book_files(
        self, folder_data: BookFolderPathData
    ) -> tuple[list[str], list[Path]]:
        """
        Get all supported files within a given directory.

        Args:
            folder_data: Data object containing the path to the book directory

        Returns:
            A tuple containing a list of file names and paths.

        Raises:
            ValueError: If the path doesn't exist, isn't a directory,
                       is empty, or contains no supported files.
        """
        logger = get_run_logger()
        logger.info("Getting a list of books from path: %s", str(folder_data.path))

        directory = folder_data.path
        try:
            directory = directory.resolve(strict=True)
        except FileNotFoundError:
            raise ValueError(f"The path {directory} does not exist")

        if not directory.is_dir():
            raise ValueError(f"The path {directory} is not a valid directory")

        files = [p for p in directory.iterdir() if p.is_file()]
        if not files:
            raise ValueError(f"The directory {directory} does not contain any files")

        matched_paths = [
            p for p in files if p.suffix.lower() in self.supported_extensions
        ]
        if not matched_paths:
            raise ValueError(
                f"The directory {directory} does not contain supported files "
                f"(supported extensions: {sorted(self.supported_extensions)})"
            )

        matched_paths.sort()
        file_names = [p.name for p in matched_paths]
        logger.info(
            "Found %d supported files in directory: %s",
            len(matched_paths),
            str(directory),
        )
        return file_names, matched_paths

    def get_book_id(self, folder_data: BookFolderPathData) -> str:
        """
        Get the book ID from a given book folder path data.

        Args:
            folder_data: Data object containing the path to the book directory

        Returns:
            A string representing the book ID (folder name).
        """
        return folder_data.book_id

    def determine_book_data_type(
        self, file_names: list[str]
    ) -> Literal["pdf", "images", "others"]:
        """
        Determine the type of book data based on file extensions.

        Args:
            file_names: List of file names to check
        Returns:
            "pdf", "images", or "others"
        """
        logger = get_run_logger()
        logger.info("Determining book data type from %d files", len(file_names))
        extensions = {Path(f).suffix.lower() for f in file_names}

        if any(ext in self.pdf_extensions for ext in extensions):
            logger.info("Detected PDF files with extensions: %s", extensions)
            return "pdf"
        elif any(ext in self.images_extensions for ext in extensions):
            logger.info("Detected image files with extensions: %s", extensions)
            return "images"
        else:
            logger.warning("Detected unsupported file types with extensions: %s", extensions)
            return "others"

    @staticmethod
    def _encode_to_outputs(
        img: PIL.Image.Image, quality: int, method: int
    ) -> tuple[str, bytes]:
        """Encodes a PIL image to both binary bytes and base64 string once."""
        buffer = io.BytesIO()
        # Using WEBP for both as it's efficient and consistent
        img.save(
            buffer,
            format="WEBP",
            quality=quality,
            method=method,
        )
        binary_data = buffer.getvalue()
        base64_data = base64.b64encode(binary_data).decode("utf-8")
        return base64_data, binary_data

    def _process_single_source(
        self, source: Path | tuple[Path, int]
    ) -> tuple[str, bytes]:
        """
        Processor unit that handles load -> resize -> encode in one pass.
        This minimizes memory overhead as pixel data is cleared after each item.
        """
        try:
            resampling_method = getattr(
                PIL.Image.Resampling, self.resizing_filter.upper()
            )

            if isinstance(source, Path):
                # Process image file
                with PIL.Image.open(source) as img:
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    img.thumbnail(self.max_size, resampling_method)
                    return self._encode_to_outputs(img, self.quality, self.webp_method)
            else:
                # Process PDF page (source is (path, page_num))
                path, page_num = source
                with fitz.open(path) as doc:
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=self.dpi)
                    # Create PIL image directly from memory samples (no intermediate JPEG)
                    img = PIL.Image.frombytes(
                        "RGB", (pix.width, pix.height), pix.samples
                    )
                    img.thumbnail(self.max_size, resampling_method)
                    return self._encode_to_outputs(img, self.quality, self.webp_method)
        except Exception as e:
            logger = get_run_logger()
            logger.error(
                "Error processing source %s: %s (Exception type: %s)",
                str(source),
                str(e),
                type(e).__name__,
            )
            raise

    def process_book_folder(self, folder_data: BookFolderPathData) -> ProcessedBookData:
        """
        End-to-end processing of images from a book folder using a unified pipeline.

        Args:
            folder_data: Data object containing the path to the book directory

        Returns:
            A ProcessedBookData object containing IDs and optimized image data.
        """
        logger = get_run_logger()
        start_mem = self._get_memory_usage_mb()
        logger.info(
            "Starting book folder processing - Book ID: %s, Path: %s, Start Memory: %.2f MB",
            folder_data.book_id,
            str(folder_data.path),
            start_mem,
        )
        
        file_names, file_paths = self.get_book_files(folder_data)
        data_type = self.determine_book_data_type(file_names)

        total_disk_size = sum(p.stat().st_size for p in file_paths)
        after_files_mem = self._get_memory_usage_mb()

        logger.info(
            "Files located - Count: %d, Data Type: %s, Total Disk Size: %d bytes (%.2f MB), Memory After Files: %.2f MB",
            len(file_paths),
            data_type,
            total_disk_size,
            total_disk_size / (1024 * 1024),
            after_files_mem,
        )

        # 1. Prepare flat list of processing sources
        sources: list[Path | tuple[Path, int]] = []
        if data_type == "pdf":
            for path in file_paths:
                if path.suffix.lower() in self.pdf_extensions:
                    with fitz.open(path) as doc:
                        sources.extend([(path, i) for i in range(len(doc))])
        elif data_type == "images":
            sources = cast(list[Path | tuple[Path, int]], file_paths)
        else:
            logger.warning(
                "No processable files found for book ID: %s (Data Type: %s)",
                folder_data.book_id,
                data_type,
            )
            return ProcessedBookData(
                book_id=folder_data.book_id, base64_images=[], binary_images=[]
            )

        after_sources_mem = self._get_memory_usage_mb()
        logger.info(
            "Sources prepared - Item Count: %d, Memory: %.2f MB",
            len(sources),
            after_sources_mem,
        )

        # 2. Parallel execution of the unified pipeline
        results = Parallel(n_jobs=self.n_jobs)(
            delayed(self._process_single_source)(s) for s in sources
        )

        after_parallel_mem = self._get_memory_usage_mb()
        logger.info("Parallel processing complete - Memory: %.2f MB, Results Count: %d", after_parallel_mem, len(results))

        if not results:
            return ProcessedBookData(
                book_id=folder_data.book_id, base64_images=[], binary_images=[]
            )

        # 3. Unzip results into separate lists
        # zip(*results) returns two tuples, we convert them to lists
        base64_images, binary_images = map(list, zip(*results))

        baml_images: list[BamlImage] = []
        for idx, base64_image in enumerate(base64_images):
            try:
                # NOTE: our encoder uses WEBP in _encode_to_outputs
                baml_images.append(
                    BamlImage.from_base64("image/webp", base64_image)
                )
            except Exception as e:
                logger.error(
                    "Error creating BAML image at index %d: %s (Exception type: %s)",
                    idx,
                    str(e),
                    type(e).__name__,
                )
                continue

        total_base64_size = sum(len(s) for s in base64_images)
        total_binary_size = sum(len(b) for b in binary_images)
        end_mem = self._get_memory_usage_mb()

        logger.info(
            "Processing complete - Book ID: %s, Image Count: %d, Total Base64 Size: %d bytes (%.2f MB), Total Binary Size: %d bytes (%.2f MB), Final Memory: %.2f MB, Memory Delta: %.2f MB",
            folder_data.book_id,
            len(base64_images),
            total_base64_size,
            total_base64_size / (1024 * 1024),
            total_binary_size,
            total_binary_size / (1024 * 1024),
            end_mem,
            end_mem - start_mem,
        )

        return ProcessedBookData(
            book_id=folder_data.book_id,
            base64_images=cast(list[str], base64_images),
            binary_images=cast(list[bytes], binary_images),
            baml_images=baml_images,
        )


def main() -> None:
    return None


if __name__ == "__main__":
    main()
