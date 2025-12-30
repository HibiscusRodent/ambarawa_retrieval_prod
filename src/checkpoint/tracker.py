"""
CheckpointTracker class for managing book processing state and persistence.

This module provides the main CheckpointTracker class that handles loading,
updating, and saving checkpoint state to Parquet files. It enables recovery
from interruptions by tracking which books have been processed and maintaining
their status throughout the pipeline.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import polars as pl
from prefect.logging import get_run_logger

from .models import BookProcessingRecord, CheckpointState, ProcessingStatus


class CheckpointTracker:
    """
    Manages checkpoint state for book processing pipeline.

    This class provides methods to create, load, update, and persist checkpoint
    data using Parquet files. It tracks the processing status of individual books
    and maintains overall statistics for the processing run.

    The checkpoint file is stored at: {checkpoint_dir}/{run_id}.parquet

    Attributes:
        checkpoint_dir: Directory where checkpoint files are stored.
        run_id: Unique identifier for this processing run.
        lance_db_uri: Path to the LanceDB database.
        lance_table_name: Name of the LanceDB table.
        state: Current checkpoint state containing all book records.
        checkpoint_path: Full path to the checkpoint Parquet file.
    """

    def __init__(
        self,
        checkpoint_dir: Path,
        run_id: str,
        lance_db_uri: Path,
        lance_table_name: str,
    ) -> None:
        """
        Initialize the CheckpointTracker.

        Args:
            checkpoint_dir: Directory where checkpoint files will be stored.
            run_id: Unique identifier for this processing run.
            lance_db_uri: Path to the LanceDB database.
            lance_table_name: Name of the LanceDB table for ingestion.
        """
        self.checkpoint_dir = checkpoint_dir
        self.run_id = run_id
        self.lance_db_uri = lance_db_uri
        self.lance_table_name = lance_table_name
        self.state: CheckpointState | None = None
        self.checkpoint_path = checkpoint_dir / f"{run_id}.parquet"

        # Create checkpoint directory if it doesn't exist
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def load_or_create(
        self, book_folder_paths: list[str], source_parquet_path: str
    ) -> CheckpointState:
        """
        Load existing checkpoint or create a new one.

        If a checkpoint file exists for this run_id, it will be loaded from disk.
        Otherwise, a new checkpoint will be created with all books in PENDING status.

        Args:
            book_folder_paths: List of absolute paths to book folders.
            source_parquet_path: Path to the source parquet file with book list.

        Returns:
            CheckpointState: The loaded or newly created checkpoint state.
        """
        logger = get_run_logger()

        if self.checkpoint_path.exists():
            logger.info(f"Loading existing checkpoint from: {self.checkpoint_path}")
            self.state = self._load_from_parquet()
            logger.info(
                f"Loaded checkpoint with {self.state.total_books} books, "
                f"{self.state.processed_count} completed, "
                f"{self.state.failed_count} failed"
            )
        else:
            logger.info(f"Creating new checkpoint for run_id: {self.run_id}")
            now = datetime.now()

            # Create book records for all books in PENDING status
            books: dict[str, BookProcessingRecord] = {}
            for path in book_folder_paths:
                book_id = Path(path).name
                books[path] = BookProcessingRecord(
                    book_folder_path=path,
                    book_id=book_id,
                    status=ProcessingStatus.PENDING,
                )

            self.state = CheckpointState(
                run_id=self.run_id,
                created_at=now,
                updated_at=now,
                total_books=len(book_folder_paths),
                processed_count=0,
                failed_count=0,
                source_parquet_path=source_parquet_path,
                lance_db_uri=str(self.lance_db_uri),
                lance_table_name=self.lance_table_name,
                books=books,
            )

            logger.info(f"Created new checkpoint with {self.state.total_books} books")

        return self.state

    def _load_from_parquet(self) -> CheckpointState:
        """
        Load checkpoint state from Parquet file.

        Returns:
            CheckpointState: Deserialized checkpoint state.
        """
        df = pl.read_parquet(self.checkpoint_path)

        # Extract metadata from first row
        first_row = df.row(0, named=True)
        run_id = first_row["run_id"]
        created_at = first_row["created_at"]
        updated_at = first_row["updated_at"]
        total_books = first_row["total_books"]
        processed_count = first_row["processed_count"]
        failed_count = first_row["failed_count"]
        source_parquet_path = first_row["source_parquet_path"]
        lance_db_uri = first_row["lance_db_uri"]
        lance_table_name = first_row["lance_table_name"]

        # Reconstruct book records
        books: dict[str, BookProcessingRecord] = {}
        for row in df.iter_rows(named=True):
            record = BookProcessingRecord(
                book_folder_path=row["book_folder_path"],
                book_id=row["book_id"],
                status=ProcessingStatus(row["status"]),
                started_at=row["started_at"],
                completed_at=row["completed_at"],
                error_message=row["error_message"],
                retry_count=row["retry_count"],
            )
            books[row["book_folder_path"]] = record

        return CheckpointState(
            run_id=run_id,
            created_at=created_at,
            updated_at=updated_at,
            total_books=total_books,
            processed_count=processed_count,
            failed_count=failed_count,
            source_parquet_path=source_parquet_path,
            lance_db_uri=lance_db_uri,
            lance_table_name=lance_table_name,
            books=books,
        )

    def mark_started(self, book_folder_path: str) -> None:
        """
        Mark a book as started processing.

        Updates the book's status to IN_PROGRESS and records the start timestamp.

        Args:
            book_folder_path: Absolute path to the book folder.
        """
        if self.state is None:
            raise RuntimeError(
                "Checkpoint state not initialized. Call load_or_create first."
            )

        if book_folder_path in self.state.books:
            self.state.books[book_folder_path].status = ProcessingStatus.IN_PROGRESS
            self.state.books[book_folder_path].started_at = datetime.now()
            self.state.updated_at = datetime.now()

    def mark_completed(self, book_folder_path: str) -> None:
        """
        Mark a book as successfully completed.

        Updates the book's status to COMPLETED, records the completion timestamp,
        and increments the processed_count.

        Args:
            book_folder_path: Absolute path to the book folder.
        """
        if self.state is None:
            raise RuntimeError(
                "Checkpoint state not initialized. Call load_or_create first."
            )

        if book_folder_path in self.state.books:
            record = self.state.books[book_folder_path]
            # Only increment count if transitioning from non-completed status
            if record.status != ProcessingStatus.COMPLETED:
                self.state.processed_count += 1

            record.status = ProcessingStatus.COMPLETED
            record.completed_at = datetime.now()
            record.error_message = None  # Clear any previous error
            self.state.updated_at = datetime.now()

    def mark_failed(self, book_folder_path: str, error_message: str) -> None:
        """
        Mark a book as failed processing.

        Updates the book's status to FAILED, stores the error message,
        increments retry_count, and updates the failed_count.

        Args:
            book_folder_path: Absolute path to the book folder.
            error_message: Description of the error that caused failure.
        """
        if self.state is None:
            raise RuntimeError(
                "Checkpoint state not initialized. Call load_or_create first."
            )

        if book_folder_path in self.state.books:
            record = self.state.books[book_folder_path]
            # Only increment failed_count if transitioning from non-failed status
            if record.status != ProcessingStatus.FAILED:
                self.state.failed_count += 1

            record.status = ProcessingStatus.FAILED
            record.error_message = error_message
            record.retry_count += 1
            self.state.updated_at = datetime.now()

    def get_pending_books(self) -> list[str]:
        """
        Get list of books that are pending processing.

        Returns only books with PENDING status (not IN_PROGRESS, COMPLETED, or FAILED).

        Returns:
            list[str]: List of book folder paths that are pending.
        """
        if self.state is None:
            raise RuntimeError(
                "Checkpoint state not initialized. Call load_or_create first."
            )

        return [
            path
            for path, record in self.state.books.items()
            if record.status == ProcessingStatus.PENDING
        ]

    def save(self) -> None:
        """
        Save checkpoint state to Parquet file.

        Serializes the current checkpoint state and writes it to the checkpoint
        file using Polars. This enables recovery from interruptions.
        """
        if self.state is None:
            raise RuntimeError(
                "Checkpoint state not initialized. Call load_or_create first."
            )

        logger = get_run_logger()

        # Flatten checkpoint state for Parquet storage
        rows = []
        for book_folder_path, record in self.state.books.items():
            rows.append(
                {
                    "run_id": self.state.run_id,
                    "created_at": self.state.created_at,
                    "updated_at": self.state.updated_at,
                    "total_books": self.state.total_books,
                    "processed_count": self.state.processed_count,
                    "failed_count": self.state.failed_count,
                    "source_parquet_path": self.state.source_parquet_path,
                    "lance_db_uri": self.state.lance_db_uri,
                    "lance_table_name": self.state.lance_table_name,
                    "book_folder_path": record.book_folder_path,
                    "book_id": record.book_id,
                    "status": record.status.value,
                    "started_at": record.started_at,
                    "completed_at": record.completed_at,
                    "error_message": record.error_message,
                    "retry_count": record.retry_count,
                }
            )

        df = pl.DataFrame(rows)
        df.write_parquet(self.checkpoint_path)
        logger.debug(f"Saved checkpoint to: {self.checkpoint_path}")

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of the checkpoint state for logging.

        Returns:
            dict[str, Any]: Summary containing counts by status and progress metrics.
        """
        if self.state is None:
            raise RuntimeError(
                "Checkpoint state not initialized. Call load_or_create first."
            )

        pending_count = sum(
            1
            for record in self.state.books.values()
            if record.status == ProcessingStatus.PENDING
        )
        in_progress_count = sum(
            1
            for record in self.state.books.values()
            if record.status == ProcessingStatus.IN_PROGRESS
        )

        return {
            "run_id": self.state.run_id,
            "total_books": self.state.total_books,
            "processed_count": self.state.processed_count,
            "failed_count": self.state.failed_count,
            "pending_count": pending_count,
            "in_progress_count": in_progress_count,
            "progress_percent": (
                self.state.processed_count / self.state.total_books * 100
                if self.state.total_books > 0
                else 0
            ),
        }
