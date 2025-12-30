"""
Checkpoint system for tracking book processing progress.

This package provides a checkpoint and progress tracking system for the book
processing pipeline. It enables resumption from interruptions by persisting
the processing status of each book to Parquet files.

Main components:
    - CheckpointTracker: Main class for managing checkpoint state.
    - ProcessingStatus: Enum for book processing states.
    - BookProcessingRecord: Model for individual book records.
    - CheckpointState: Model for overall checkpoint state.
    - reconcile_checkpoint_with_lancedb: Function for crash recovery.

Example usage:
    >>> from checkpoint import CheckpointTracker, reconcile_checkpoint_with_lancedb
    >>> from pathlib import Path
    >>>
    >>> # Initialize tracker
    >>> tracker = CheckpointTracker(
    ...     checkpoint_dir=Path("data/checkpoints"),
    ...     run_id="run_2025_01_01_120000",
    ...     lance_db_uri=Path("data/lance_db"),
    ...     lance_table_name="books_table"
    ... )
    >>>
    >>> # Load or create checkpoint
    >>> state = tracker.load_or_create(
    ...     book_folder_paths=["path/to/book1", "path/to/book2"],
    ...     source_parquet_path="data/book_list.parquet"
    ... )
    >>>
    >>> # Reconcile with LanceDB
    >>> reconcile_checkpoint_with_lancedb(tracker, lance_db, "books_table")
    >>>
    >>> # Get pending books
    >>> pending = tracker.get_pending_books()
    >>>
    >>> # Process books
    >>> for book_path in pending:
    ...     tracker.mark_started(book_path)
    ...     # ... process book ...
    ...     tracker.mark_completed(book_path)
    ...     tracker.save()
"""

from .models import BookProcessingRecord, CheckpointState, ProcessingStatus
from .tracker import CheckpointTracker
from .utils import reconcile_checkpoint_with_lancedb, verify_against_lancedb

__all__ = [
    "CheckpointTracker",
    "ProcessingStatus",
    "BookProcessingRecord",
    "CheckpointState",
    "reconcile_checkpoint_with_lancedb",
    "verify_against_lancedb",
]
