"""
Pydantic models for checkpoint and progress tracking system.

This module defines the data structures used to track the processing status
of books through the analysis pipeline. It provides strongly-typed models
for individual book records and overall checkpoint state, enabling persistence
and recovery from processing interruptions.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ProcessingStatus(str, Enum):
    """
    Enum representing the processing status of a book.

    Values:
        PENDING: Book has not yet been processed.
        IN_PROGRESS: Book processing has started but not completed.
        COMPLETED: Book processing finished successfully.
        FAILED: Book processing encountered an error and failed.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BookProcessingRecord(BaseModel):
    """
    Record tracking the processing status of a single book.

    This model captures the complete lifecycle of a book's processing,
    from initial pending state through completion or failure. It includes
    timestamps for tracking duration and error messages for debugging failures.

    Attributes:
        book_folder_path: Absolute path to the book's folder containing images.
        book_id: Unique identifier extracted from the folder name.
        status: Current processing status (pending/in_progress/completed/failed).
        started_at: Timestamp when processing began (None if not started).
        completed_at: Timestamp when processing completed (None if not completed).
        error_message: Error message if processing failed (None if successful or pending).
        retry_count: Number of times this book has been retried after failure.
    """

    book_folder_path: str = Field(description="Absolute path to book folder")
    book_id: str = Field(description="Extracted book ID from folder name")
    status: ProcessingStatus = Field(
        default=ProcessingStatus.PENDING, description="Current processing status"
    )
    started_at: Optional[datetime] = Field(
        default=None, description="Timestamp when processing started"
    )
    completed_at: Optional[datetime] = Field(
        default=None, description="Timestamp when processing completed"
    )
    error_message: Optional[str] = Field(
        default=None, description="Error message if processing failed"
    )
    retry_count: int = Field(default=0, description="Number of retry attempts")


class CheckpointState(BaseModel):
    """
    Overall checkpoint state for a processing run.

    This model maintains the complete state of a book processing run,
    including metadata about the run itself and records for all books
    being processed. It is persisted to disk as a Parquet file to enable
    recovery from interruptions.

    Attributes:
        run_id: Unique identifier for this processing run.
        created_at: Timestamp when this checkpoint was first created.
        updated_at: Timestamp of the most recent checkpoint update.
        total_books: Total number of books to be processed in this run.
        processed_count: Number of books successfully processed.
        failed_count: Number of books that failed processing.
        source_parquet_path: Path to the source parquet file containing book folder list.
        lance_db_uri: URI/path to the LanceDB database.
        lance_table_name: Name of the LanceDB table for ingestion.
        books: Dictionary mapping book_folder_path to BookProcessingRecord.
    """

    run_id: str = Field(description="Unique ID for this processing run")
    created_at: datetime = Field(description="Checkpoint creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    total_books: int = Field(description="Total number of books to process")
    processed_count: int = Field(default=0, description="Number of books completed")
    failed_count: int = Field(default=0, description="Number of books failed")
    source_parquet_path: str = Field(
        description="Path to source book folder list parquet"
    )
    lance_db_uri: str = Field(description="Path/URI to LanceDB database")
    lance_table_name: str = Field(description="LanceDB table name for ingestion")
    books: dict[str, BookProcessingRecord] = Field(
        default_factory=dict, description="Book processing records keyed by folder path"
    )
