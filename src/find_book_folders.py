from pathlib import Path
import polars as pl
import os
from prefect import flow, task
from prefect.task_runners import ThreadPoolTaskRunner
from prefect.futures import wait


@task
def process_directory(
    root_path: str, image_extensions: set[str], pdf_extension: set[str]
) -> tuple[str, list[str], list[str]] | None:
    """
    Process a single directory to find files with target extensions.

    This function is decorated with @task for parallel execution using Prefect's
    ThreadPoolTaskRunner. It scans a directory (non-recursively) to find files
    matching the specified image or PDF extensions.

    Args:
        root_path (str): Path to the directory to process.
        image_extensions (set[str]): Set of image file extensions to search for
            (e.g., {'.jpg', '.png'}).
        pdf_extension (set[str]): Set of PDF file extensions to search for
            (typically {'.pdf'}).

    Returns:
        tuple[str, list[str], list[str]] | None: A tuple containing:
            - The absolute path to the directory (str)
            - List of matching filenames (list[str])
            - List of full file paths (list[str])
            Returns None if no target files are found or if the directory
            cannot be accessed due to permission or existence errors.
    """
    target_extensions = image_extensions.union(pdf_extension)

    try:
        # Get files in this specific directory (not recursive)
        files = os.listdir(root_path)
        target_files = [
            f
            for f in files
            if os.path.isfile(os.path.join(root_path, f))
            and Path(f).suffix.lower() in target_extensions
        ]

        if target_files:
            full_filepaths = [os.path.join(root_path, f) for f in target_files]
            return (os.path.abspath(root_path), target_files, full_filepaths)
        else:
            return None
    except (PermissionError, FileNotFoundError):
        # Skip directories we can't access
        return None


@flow(task_runner=ThreadPoolTaskRunner(max_workers=8))
def finding_book_folder(input_folder: str) -> pl.DataFrame:
    """
    Scour through subfolders to find folders that contain images and/or PDF files.

    This function walks through all subdirectories of the input folder in parallel
    using Prefect's ThreadPoolTaskRunner to identify directories containing image
    or PDF files. Directories containing only other directories (no target files)
    are ignored.

    The function uses concurrent thread-based execution to efficiently process
    large directory structures. Each directory is processed as a separate Prefect
    task, allowing for parallel I/O operations.

    Args:
        input_folder (str): Path to the root folder to scan. All subdirectories
            will be recursively searched for image and PDF files.

    Returns:
        pl.DataFrame: A Polars DataFrame with the following columns:
            - 'Path' (Utf8): Absolute path to directories containing target files.
            - 'files' (List[Utf8]): List of matching filenames in each directory.
            - 'filepaths' (List[Utf8]): List of full paths to each matching file.
            Returns an empty DataFrame with the correct schema if no matching
            directories are found.

    Supported file extensions:
        - Images: .jpg, .jpeg, .png, .webp, .gif, .bmp, .tiff, .tif, .svg, .ico
        - Documents: .pdf

    Example:
        >>> df = finding_book_folder("/path/to/books")
        >>> print(df)
        shape: (2, 3)
        ┌─────────────────────┬───────────────────┬─────────────────────────┐
        │ Path                ┆ files             ┆ filepaths               │
        │ ---                 ┆ ---               ┆ ---                     │
        │ str                 ┆ list[str]         ┆ list[str]               │
        ╞═════════════════════╪═══════════════════╪═════════════════════════╡
        │ /path/to/books/dir1 ┆ ["cover.jpg"]     ┆ ["/path/.../cover.jpg"] │
        │ /path/to/books/dir2 ┆ ["doc.pdf", ...]  ┆ ["/path/.../doc.pdf"]   │
        └─────────────────────┴───────────────────┴─────────────────────────┘
    """
    # Define supported extensions
    image_extensions = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".bmp",
        ".tiff",
        ".tif",
        ".svg",
        ".ico",
    }
    pdf_extension = {".pdf"}

    print("Scanning directory structure with parallel processing...")
    print("-" * 60)

    # Collect all directories to process
    all_directories: list[str] = []
    for root, dirs, files in os.walk(input_folder):
        all_directories.append(root)

    print(f"Found {len(all_directories)} directories to process...")

    # Submit tasks for parallel execution using Prefect
    print("Processing directories in parallel with ThreadPoolTaskRunner...")
    futures = [
        process_directory.submit(directory, image_extensions, pdf_extension)
        for directory in all_directories
    ]

    # Wait for all tasks to complete
    wait(futures)

    # Collect results from futures
    results = [future.result() for future in futures]

    # Filter out None results and separate the data
    valid_results = [result for result in results if result is not None]

    paths: list[str] = []
    files_lists: list[list[str]] = []
    filepaths_lists: list[list[str]] = []

    for root_path, target_files, full_filepaths in valid_results:
        folder_name = os.path.basename(root_path)
        print(f"Found target files in: {folder_name}")

        paths.append(root_path)
        files_lists.append(target_files)
        filepaths_lists.append(full_filepaths)

    # Display results in terminal
    print(f"\nFound {len(paths)} folder(s) containing images and/or PDFs:")
    print("-" * 60)
    for folder_path in paths:
        print(folder_path)
    print("-" * 60)

    # Create Polars DataFrame directly
    if paths:
        df = pl.DataFrame(
            {"Path": paths, "files": files_lists, "filepaths": filepaths_lists}
        )
    else:
        # Create empty DataFrame with correct schema
        df = pl.DataFrame(
            {"Path": [], "files": [], "filepaths": []},
            schema={
                "Path": pl.Utf8,
                "files": pl.List(pl.Utf8),
                "filepaths": pl.List(pl.Utf8),
            },
        )

    print(f"\nDataFrame created with {len(df)} rows")
    print(df.head())

    return df


def main() -> pl.DataFrame:
    """
    Example usage of the finding_book_folder function.

    This function serves as an entry point for testing the finding_book_folder
    function. It scans the current directory for folders containing images or PDFs.

    Returns:
        pl.DataFrame: The resulting DataFrame from finding_book_folder containing
            paths to directories with image/PDF files and their contents.
    """
    # You can add test code here or modify as needed
    test_folder = "."  # Current directory for testing
    result_df = finding_book_folder(test_folder)
    return result_df


if __name__ == "__main__":
    main()
