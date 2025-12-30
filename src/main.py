import argparse
import sys
from datetime import datetime

import polars as pl
from pathlib import Path
from prefect import task, flow
from prefect.cache_policies import NO_CACHE
from prefect.logging import get_run_logger

import single_book_flow as single_inf
from single_book_flow import InitializedEnvironment
from checkpoint import CheckpointTracker, reconcile_checkpoint_with_lancedb


# book_folder = Path("sample_data")
# # retrieve all subfolders in the book_folder
# book_folder_paths = [str(folder) for folder in book_folder.iterdir() if folder.is_dir()]
# print(f"Found {len(book_folder_paths)} book folders for inference.")


def parse_arguments() -> argparse.Namespace:
    """
    Parse command line arguments for the book processing pipeline.

    Returns:
        argparse.Namespace: Parsed command line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Book processing pipeline with checkpoint support"
    )

    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Unique run ID for checkpoint tracking (default: timestamp-based)",
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume from existing checkpoint with the specified run-id",
    )

    parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore any existing checkpoint and start fresh",
    )

    parser.add_argument(
        "--checkpoint-dir",
        type=str,
        default="data/checkpoints",
        help="Directory for checkpoint files (default: data/checkpoints)",
    )

    parser.add_argument(
        "--source-parquet",
        type=str,
        default="data/book_folder_list.parquet",
        help="Path to source parquet file with book folders (default: data/book_folder_list.parquet)",
    )

    parser.add_argument(
        "--output-folder",
        type=str,
        default="data/output_book_data",
        help="Output folder for processed data (default: data/output_book_data)",
    )

    parser.add_argument(
        "--lance-db-uri",
        type=str,
        default="data/test/lance_db_semi_prod",
        help="Path to LanceDB database (default: data/test/lance_db_semi_prod)",
    )

    parser.add_argument(
        "--table-name",
        type=str,
        default="pararel_test_new",
        help="LanceDB table name (default: pararel_test_new)",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=5,
        help="Number of books to process in parallel batches (default: 5)",
    )

    return parser.parse_args()


@task(cache_policy=NO_CACHE)
def run_single_inference(
    setup_instance: InitializedEnvironment,
    book_folder_path: str,
    output_folder_path: str,
    tracker: CheckpointTracker,
) -> None:
    """
    Run inference on a single book and store results in LanceDB.

    This function wraps the single_book_flow with checkpoint tracking,
    marking books as started/completed/failed and handling errors gracefully.

    Args:
        setup_instance: Initialized environment containing image processors and LanceDB connection.
        book_folder_path: Path to the folder containing book images.
        output_folder_path: Path where output data will be saved.
        tracker: CheckpointTracker instance for updating book status.
    """
    logger = get_run_logger()

    try:
        # Mark book as started
        tracker.mark_started(book_folder_path)

        # Run the book processing flow
        single_inf.single_book_flow(
            setup_instance, book_folder_path, output_folder_path
        )

        # Mark book as completed
        tracker.mark_completed(book_folder_path)
        logger.info(f"Successfully completed processing: {book_folder_path}")

    except Exception as e:
        # Mark book as failed with error message
        error_message = f"{type(e).__name__}: {str(e)}"
        tracker.mark_failed(book_folder_path, error_message)
        logger.error(f"Failed to process {book_folder_path}: {error_message}")
        # Re-raise to allow Prefect to handle the error
        raise

    return None


@flow
def main_inference_multiple_books(
    book_folder_paths: list[str],
    output_folder_path: str,
    setup_instance: InitializedEnvironment,
    tracker: CheckpointTracker,
    batch_size: int = 5,
) -> None:
    """
    Run inference on multiple books in parallel batches and store results in LanceDB.

    This flow processes books in batches with checkpoint tracking, enabling
    recovery from interruptions by resuming only pending books.

    Args:
        book_folder_paths: List of paths to book folders.
        output_folder_path: Path where output data will be saved.
        setup_instance: Initialized environment with image processors and LanceDB.
        tracker: CheckpointTracker instance for progress tracking.
        batch_size: Number of books to process in parallel at once (default: 5).
    """
    logger = get_run_logger()

    # Get summary before starting
    summary = tracker.get_summary()
    logger.info("=" * 60)
    logger.info("Starting book processing with checkpoint tracking")
    logger.info(f"Run ID: {summary['run_id']}")
    logger.info(f"Total books: {summary['total_books']}")
    logger.info(f"Already processed: {summary['processed_count']}")
    logger.info(f"Failed: {summary['failed_count']}")
    logger.info(f"Pending: {summary['pending_count']}")
    logger.info(f"Batch size: {batch_size}")
    logger.info("=" * 60)

    # Process books in batches to limit concurrent executions
    for i in range(0, len(book_folder_paths), batch_size):
        batch = book_folder_paths[i : i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(book_folder_paths) + batch_size - 1) // batch_size

        logger.info(
            f"Processing batch {batch_num}/{total_batches} ({len(batch)} books)"
        )

        futures = []

        # Submit all tasks in the batch for parallel execution
        for book_folder_path in batch:
            future = run_single_inference.submit(
                setup_instance=setup_instance,
                book_folder_path=book_folder_path,
                output_folder_path=output_folder_path,
                tracker=tracker,
            )
            futures.append(future)

        # Wait for all tasks in the current batch to complete before starting the next batch
        for future in futures:
            try:
                future.wait()
            except Exception as e:
                # Log the error but continue with other books
                logger.error(f"Error in batch processing: {str(e)}")

        # Save checkpoint after each batch
        tracker.save()
        logger.info(f"Batch {batch_num}/{total_batches} completed. Checkpoint saved.")

        # Log progress
        summary = tracker.get_summary()
        logger.info(
            f"Progress: {summary['processed_count']}/{summary['total_books']} "
            f"({summary['progress_percent']:.1f}%) | "
            f"Failed: {summary['failed_count']}"
        )

    # Final summary
    final_summary = tracker.get_summary()
    logger.info("=" * 60)
    logger.info("Processing complete!")
    logger.info(f"Total processed: {final_summary['processed_count']}")
    logger.info(f"Total failed: {final_summary['failed_count']}")
    logger.info(f"Success rate: {final_summary['progress_percent']:.1f}%")
    logger.info("=" * 60)

    return None


def main() -> None:
    """
    Main entry point for the book processing pipeline with checkpoint support.

    This function orchestrates the entire processing pipeline:
    1. Parses command line arguments
    2. Loads book folder list from parquet
    3. Initializes or loads checkpoint
    4. Reconciles with LanceDB for crash recovery
    5. Processes pending books in batches
    6. Saves checkpoint after each batch
    """
    # Parse command line arguments
    args = parse_arguments()

    # Generate run_id if not provided
    if args.run_id is None:
        args.run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    print("=" * 60)
    print("Book Processing Pipeline with Checkpoint Support")
    print("=" * 60)
    print(f"Run ID: {args.run_id}")
    print(f"Resume mode: {args.resume}")
    print(f"Reset mode: {args.reset}")
    print(f"Checkpoint directory: {args.checkpoint_dir}")
    print(f"Source parquet: {args.source_parquet}")
    print(f"Output folder: {args.output_folder}")
    print(f"LanceDB URI: {args.lance_db_uri}")
    print(f"Table name: {args.table_name}")
    print(f"Batch size: {args.batch_size}")
    print("=" * 60)

    # Validate arguments
    if args.resume and args.reset:
        print("ERROR: Cannot use --resume and --reset together")
        sys.exit(1)

    if args.resume and args.run_id is None:
        print("ERROR: --resume requires --run-id to specify which run to resume")
        sys.exit(1)

    # Load book folder list from parquet
    book_folder_dataframe = pl.read_parquet(args.source_parquet)
    all_book_folder_paths = book_folder_dataframe["Path"].to_list()

    print(
        f"Loaded {len(all_book_folder_paths)} book folders from {args.source_parquet}"
    )

    # Setup paths
    checkpoint_dir = Path(args.checkpoint_dir)
    lance_db_uri = Path(args.lance_db_uri)
    output_folder_path = args.output_folder

    # Initialize environment (LanceDB connection, ImageProcessors, etc.)
    print("\nInitializing environment...")
    setup_instance = single_inf.setup_phase_flow(lance_db_uri, args.table_name)
    print("Environment initialized successfully")

    # Initialize checkpoint tracker
    print("\nInitializing checkpoint tracker...")
    tracker = CheckpointTracker(
        checkpoint_dir=checkpoint_dir,
        run_id=args.run_id,
        lance_db_uri=lance_db_uri,
        lance_table_name=args.table_name,
    )

    # Load or create checkpoint
    if args.reset:
        print("Reset mode: Creating fresh checkpoint (ignoring existing)")
        # Delete existing checkpoint if it exists
        if tracker.checkpoint_path.exists():
            tracker.checkpoint_path.unlink()
            print(f"Deleted existing checkpoint: {tracker.checkpoint_path}")

    tracker.load_or_create(all_book_folder_paths, args.source_parquet)

    # Reconcile with LanceDB for crash recovery
    print("\nReconciling checkpoint with LanceDB...")
    reconcile_checkpoint_with_lancedb(
        tracker, setup_instance.active_lance_db, args.table_name
    )

    # Get pending books
    pending_books = tracker.get_pending_books()

    if not pending_books:
        print("\n" + "=" * 60)
        print("All books have been processed!")
        summary = tracker.get_summary()
        print(f"Total: {summary['total_books']}")
        print(f"Completed: {summary['processed_count']}")
        print(f"Failed: {summary['failed_count']}")
        print("=" * 60)
        return

    print(f"\nFound {len(pending_books)} pending books to process")

    # Start processing
    print("\nStarting book processing flow...\n")
    main_inference_multiple_books(
        book_folder_paths=pending_books,
        output_folder_path=output_folder_path,
        setup_instance=setup_instance,
        tracker=tracker,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
