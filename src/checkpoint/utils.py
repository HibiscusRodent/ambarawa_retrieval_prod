"""
Utility functions for checkpoint system integration.

This module provides helper functions for verifying checkpoint state against
LanceDB records and reconciling discrepancies that may arise from processing
interruptions or crashes.
"""

from typing import Any

from prefect.logging import get_run_logger

from .models import ProcessingStatus
from .tracker import CheckpointTracker


def verify_against_lancedb(
    lance_db: Any, table_name: str, book_ids: list[str]
) -> set[str]:
    """
    Query LanceDB to find which book IDs have already been ingested.

    This function queries the specified LanceDB table to check which books
    from the provided list have already been successfully ingested. This is
    useful for crash recovery where the checkpoint file may not reflect the
    actual state in the database.

    Args:
        lance_db: Active LanceDB connection.
        table_name: Name of the table to query.
        book_ids: List of book IDs to check for existence.

    Returns:
        set[str]: Set of book IDs that exist in the LanceDB table.
    """
    logger = get_run_logger()

    try:
        # Check if table exists
        if table_name not in lance_db.table_names():
            logger.info(f"Table '{table_name}' does not exist yet. No books ingested.")
            return set()

        table = lance_db.open_table(table_name)

        # Query for existing book_ids
        # Use a more efficient approach: get all book_ids from the table
        # and intersect with the provided list
        try:
            result = table.to_pandas()
            existing_book_ids = set(result["book_id"].tolist())
            found_books = existing_book_ids.intersection(set(book_ids))

            logger.info(
                f"Found {len(found_books)} books already in LanceDB table '{table_name}'"
            )
            return found_books

        except Exception as e:
            logger.warning(
                f"Could not query LanceDB table '{table_name}': {str(e)}. "
                "Assuming no books are ingested."
            )
            return set()

    except Exception as e:
        logger.error(
            f"Error connecting to LanceDB table '{table_name}': {str(e)}. "
            "Proceeding without LanceDB verification."
        )
        return set()


def reconcile_checkpoint_with_lancedb(
    tracker: CheckpointTracker, lance_db: Any, table_name: str
) -> None:
    """
    Reconcile checkpoint state with LanceDB for crash recovery.

    This function checks which books exist in LanceDB but are marked as
    pending or in-progress in the checkpoint. It updates the checkpoint
    to mark these books as completed, enabling accurate recovery from
    crashes where the checkpoint wasn't saved after successful ingestion.

    Args:
        tracker: CheckpointTracker instance with loaded state.
        lance_db: Active LanceDB connection.
        table_name: Name of the LanceDB table.
    """
    logger = get_run_logger()

    if tracker.state is None:
        raise RuntimeError("Tracker state not initialized")

    logger.info("Starting checkpoint reconciliation with LanceDB...")

    # Get all book IDs from checkpoint
    all_book_ids = [record.book_id for record in tracker.state.books.values()]

    # Query LanceDB for existing books
    existing_book_ids = verify_against_lancedb(lance_db, table_name, all_book_ids)

    if not existing_book_ids:
        logger.info("No reconciliation needed - no books found in LanceDB")
        return

    # Find books that exist in LanceDB but aren't marked as completed
    reconciled_count = 0
    for path, record in tracker.state.books.items():
        if (
            record.book_id in existing_book_ids
            and record.status != ProcessingStatus.COMPLETED
        ):
            logger.info(
                f"Reconciling book '{record.book_id}': "
                f"Found in LanceDB but marked as {record.status.value}"
            )
            tracker.mark_completed(path)
            reconciled_count += 1

    if reconciled_count > 0:
        logger.info(
            f"Reconciled {reconciled_count} books found in LanceDB. Saving checkpoint..."
        )
        tracker.save()
    else:
        logger.info(
            "All checkpoint records match LanceDB state. No reconciliation needed."
        )
