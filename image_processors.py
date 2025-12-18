# file handling libraries
from pathlib import Path

# libraries for handling format conversions
# and also image processings, including PDFs
import base64
import numpy as np
import PIL.Image
import pymupdf as fitz
import io

# misc libraries
from loguru import logger
from typing import Any, Literal, cast

# for parallelizations
from joblib import Parallel, delayed

# rich traceback to show better debugging display
from rich.traceback import install

install()


class ImageProcessors:
    """
    A class for processing images and PDFs, including loading, resizing,
    and converting to various formats (numpy arrays, base64, binary).

    All configuration is managed through instance attributes, eliminating
    the need for a separate configuration schema.
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

    @property
    def supported_extensions(self) -> set[str]:
        """Get all supported file extensions."""
        return set(self.images_extensions + self.pdf_extensions)

    def get_book_files(self, book_folder: str | Path) -> tuple[list[str], list[Path]]:
        """
        Get all supported files within a given directory.

        Args:
            book_folder: Path to the book directory

        Returns:
            A tuple containing a list of file names and paths.

        Raises:
            ValueError: If the path doesn't exist, isn't a directory,
                       is empty, or contains no supported files.
        """
        logger.info(f"Getting a list of books from {book_folder}")

        directory = Path(book_folder)
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
        logger.info(f"Found {len(matched_paths)} supported files in {directory}")
        return file_names, matched_paths

    @staticmethod
    def get_book_id(book_folder: str | Path) -> str:
        """
        Get the book ID from a given book folder path.

        Args:
            book_folder: Path to the book directory

        Returns:
            A string representing the book ID (folder name).
        """
        return Path(book_folder).name

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
        logger.info("Determining book data type...")
        extensions = {Path(f).suffix.lower() for f in file_names}

        if any(ext in self.pdf_extensions for ext in extensions):
            logger.info("Detected PDF files")
            return "pdf"
        elif any(ext in self.images_extensions for ext in extensions):
            logger.info("Detected image files")
            return "images"
        else:
            logger.warning("Detected unsupported file types")
            return "others"

    @staticmethod
    def _load_single_image(image_path: Path) -> np.ndarray:
        """Load a single image into a numpy array."""
        try:
            with PIL.Image.open(image_path) as img:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                return np.array(img)
        except Exception as e:
            logger.error(f"Error processing image {image_path}: {e}")
            raise

    def load_images_to_numpyarrays(self, image_paths: list[Path]) -> list[np.ndarray]:
        """
        Convert image files to numpy arrays using parallel processing.

        Args:
            image_paths: List of image file paths

        Returns:
            List of numpy arrays, each representing an image.
        """
        logger.debug(f"Converting {len(image_paths)} image files to NumPy arrays...")

        results = cast(
            list[np.ndarray],
            Parallel(n_jobs=self.n_jobs)(
                delayed(self._load_single_image)(path) for path in image_paths
            ),
        )
        return results

    def get_pdf_paths(self, file_paths: list[Path]) -> list[Path]:
        """Get PDF file paths from the list of file paths."""
        return [
            path for path in file_paths if path.suffix.lower() in self.pdf_extensions
        ]

    def pdfs_to_numpy_arrays(self, pdf_paths: list[Path]) -> list[np.ndarray]:
        """
        Convert PDF files to numpy arrays using PyMuPDF (fitz).

        Args:
            pdf_paths: List of PDF file paths

        Returns:
            List of numpy arrays, each representing a page.
        """
        logger.info(
            f"Converting {len(pdf_paths)} PDF files to NumPy arrays via fitz..."
        )

        if not pdf_paths:
            raise ValueError("No PDF files provided")

        combined_pdf = fitz.open()
        try:
            for pdf_path in pdf_paths:
                logger.debug(f"Processing PDF: {pdf_path}")
                with fitz.open(pdf_path) as source_pdf:
                    combined_pdf.insert_pdf(source_pdf)

            logger.info(f"Combined PDF has {len(combined_pdf)} pages")

            results = []
            for page_num in range(len(combined_pdf)):
                page = combined_pdf.load_page(page_num)
                pix = page.get_pixmap(dpi=self.dpi)
                img_bytes = pix.tobytes(output="jpeg")
                img = PIL.Image.open(io.BytesIO(img_bytes))
                if img.mode != "RGB":
                    img = img.convert("RGB")
                results.append(np.array(img))
                logger.debug(f"Processed page {page_num + 1}/{len(combined_pdf)}")

            result = results

            logger.debug(
                f"Successfully converted PDF pages to {len(result)} numpy arrays"
            )
            return result

        finally:
            combined_pdf.close()

    def get_image_arrays(
        self, file_names: list[str], file_paths: list[Path]
    ) -> list[np.ndarray]:
        """
        Get numpy arrays from book files based on their type.

        Args:
            file_names: List of file names
            file_paths: List of file paths

        Returns:
            List of numpy arrays representing images or PDF pages.
        """
        data_type = self.determine_book_data_type(file_names)

        match data_type:
            case "pdf":
                pdf_paths = self.get_pdf_paths(file_paths)
                return self.pdfs_to_numpy_arrays(pdf_paths)
            case "images":
                return self.load_images_to_numpyarrays(file_paths)
            case _:
                logger.error("Unsupported book data type")
                return []

    def _resize_single_image(self, image_array: np.ndarray) -> np.ndarray:
        """Resize a single image numpy array."""
        resampling_method = getattr(PIL.Image.Resampling, self.resizing_filter.upper())
        pil_img = PIL.Image.fromarray(image_array)
        pil_img.thumbnail(self.max_size, resampling_method, reducing_gap=3.0)
        return np.array(pil_img)

    def resize_image_arrays(self, image_arrays: list[np.ndarray]) -> list[np.ndarray]:
        """
        Resize image numpy arrays using parallel processing.

        Args:
            image_arrays: List of numpy arrays

        Returns:
            List of resized numpy arrays.
        """
        logger.debug(f"Resizing {len(image_arrays)} image arrays...")

        results = cast(
            list[np.ndarray],
            Parallel(n_jobs=self.n_jobs)(
                delayed(self._resize_single_image)(img) for img in image_arrays
            ),
        )
        return results

    def _image_array_to_base64(self, img_array: np.ndarray) -> str:
        """Convert a single numpy array to base64 string."""
        pil_img = PIL.Image.fromarray(img_array)
        buffer = io.BytesIO()
        pil_img.save(
            buffer,
            quality=self.quality,
            format="WEBP",
            method=self.webp_method,
        )
        return base64.b64encode(buffer.getvalue()).decode("utf-8")

    def image_arrays_to_base64(self, image_arrays: list[np.ndarray]) -> list[str]:
        """
        Convert numpy arrays to base64 strings.

        Args:
            image_arrays: List of numpy arrays

        Returns:
            List of base64-encoded strings.
        """
        logger.info(f"Converting {len(image_arrays)} images to Base64 encoding...")

        results = cast(
            list[str],
            Parallel(n_jobs=self.n_jobs)(
                delayed(self._image_array_to_base64)(img) for img in image_arrays
            ),
        )

        logger.success(f"Successfully converted {len(results)} images to Base64")
        return results

    def _image_array_to_binary(self, img_array: np.ndarray) -> bytes:
        """Convert a single numpy array to binary data."""
        pil_img = PIL.Image.fromarray(img_array)
        buffer = io.BytesIO()
        pil_img.save(
            buffer,
            quality=self.binary_quality,
            format=self.binary_format,
            method=self.binary_webp_method,
        )
        return buffer.getvalue()

    def image_arrays_to_binary(self, image_arrays: list[np.ndarray]) -> list[bytes]:
        """
        Convert numpy arrays to binary data.

        Args:
            image_arrays: List of numpy arrays

        Returns:
            List of bytes objects.
        """
        logger.info(f"Converting {len(image_arrays)} images to binary data...")

        results = cast(
            list[bytes],
            Parallel(n_jobs=self.n_jobs)(
                delayed(self._image_array_to_binary)(img) for img in image_arrays
            ),
        )

        logger.success(f"Successfully converted {len(results)} images to binary data")
        return results

    def process_book_folder(
        self, book_folder: str | Path
    ) -> tuple[list[str], list[bytes]]:
        """
        End-to-end processing of images from a book folder.

        Args:
            book_folder: Path to the book directory

        Returns:
            A tuple containing:
            - base64_images: List of base64-encoded strings
            - binary_images: List of bytes objects
        """
        file_names, file_paths = self.get_book_files(book_folder)
        image_arrays = self.get_image_arrays(file_names, file_paths)
        resized_arrays = self.resize_image_arrays(image_arrays)

        base64_images = self.image_arrays_to_base64(resized_arrays)
        binary_images = self.image_arrays_to_binary(resized_arrays)
        return base64_images, binary_images


def main() -> None:
    return None


if __name__ == "__main__":
    ip = ImageProcessors()
