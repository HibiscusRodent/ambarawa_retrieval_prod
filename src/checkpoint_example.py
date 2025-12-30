"""
Example script demonstrating checkpoint system usage.

This script shows how to use the checkpoint system both programmatically
and via command line for the book processing pipeline.
"""

from pathlib import Path

from checkpoint import CheckpointTracker


def example_programmatic_usage():
    """
    Example of using the checkpoint system programmatically.

    This function demonstrates how to integrate checkpoint tracking
    into a custom processing loop.
    """
    # Initialize checkpoint tracker
    tracker = CheckpointTracker(
        checkpoint_dir=Path("data/checkpoints"),
        run_id="example_run_001",
        lance_db_uri=Path("data/lance_db_test"),
        lance_table_name="books_test_table",
    )

    # Sample book folder paths (in real use, load from parquet)
    book_folder_paths = [
        "sample_data/rak-0003_baris-005_buku-30",
        "sample_data/rak-0003_baris-005_buku-52",
        "sample_data/rak-0003_baris-005_buku-53",
    ]

    # Load or create checkpoint
    state = tracker.load_or_create(
        book_folder_paths=book_folder_paths,
        source_parquet_path="data/book_folder_list.parquet",
    )

    print(f"Checkpoint initialized: {state.run_id}")
    print(f"Total books: {state.total_books}")
    print(f"Already processed: {state.processed_count}")

    # Note: In real usage, you would connect to LanceDB here
    # lance_db = connect("data/lance_db_test")
    # reconcile_checkpoint_with_lancedb(tracker, lance_db, "books_test_table")

    # Get pending books
    pending_books = tracker.get_pending_books()
    print(f"\nPending books: {len(pending_books)}")

    # Process each book (simulated)
    for book_path in pending_books:
        print(f"\nProcessing: {book_path}")

        # Mark as started
        tracker.mark_started(book_path)

        try:
            # Your processing logic here
            # process_book(book_path)

            # Simulate successful processing
            print("  ✓ Successfully processed")
            tracker.mark_completed(book_path)

        except Exception as e:
            # Mark as failed
            error_msg = f"{type(e).__name__}: {str(e)}"
            print(f"  ✗ Failed: {error_msg}")
            tracker.mark_failed(book_path, error_msg)

        # Save checkpoint after each book
        tracker.save()

    # Get final summary
    summary = tracker.get_summary()
    print("\n" + "=" * 60)
    print("Processing Summary:")
    print(f"  Total: {summary['total_books']}")
    print(f"  Completed: {summary['processed_count']}")
    print(f"  Failed: {summary['failed_count']}")
    print(f"  Pending: {summary['pending_count']}")
    print(f"  Progress: {summary['progress_percent']:.1f}%")
    print("=" * 60)


def print_cli_examples():
    """
    Print example command line usages of the checkpoint system.
    """
    print("\n" + "=" * 60)
    print("CHECKPOINT SYSTEM - COMMAND LINE EXAMPLES")
    print("=" * 60)

    print("\n1. Start a new processing run (auto-generated run ID):")
    print("   uv run src/main.py")

    print("\n2. Start a new run with custom run ID:")
    print("   uv run src/main.py --run-id prod_batch_20250101")

    print("\n3. Resume from an interrupted run:")
    print("   uv run src/main.py --run-id prod_batch_20250101 --resume")

    print("\n4. Reset and start fresh (ignore existing checkpoint):")
    print("   uv run src/main.py --run-id prod_batch_20250101 --reset")

    print("\n5. Custom configuration:")
    print("   uv run src/main.py \\")
    print("     --run-id my_test_run \\")
    print("     --checkpoint-dir data/my_checkpoints \\")
    print("     --source-parquet data/custom_books.parquet \\")
    print("     --output-folder data/custom_output \\")
    print("     --lance-db-uri data/custom_lancedb \\")
    print("     --table-name custom_table \\")
    print("     --batch-size 10")

    print("\n6. View checkpoint status (using Polars):")
    print('   python -c "import polars as pl; \\')
    print("     df = pl.read_parquet('data/checkpoints/run_xyz.parquet'); \\")
    print("     print(df.group_by('status').agg(pl.count()))\"")

    print("\n7. Find failed books:")
    print('   python -c "import polars as pl; \\')
    print("     df = pl.read_parquet('data/checkpoints/run_xyz.parquet'); \\")
    print("     failed = df.filter(pl.col('status') == 'failed'); \\")
    print("     print(failed.select(['book_id', 'error_message']))\"")

    print("\n" + "=" * 60)


def main():
    """
    Main entry point for the example script.
    """
    print("Checkpoint System Example")
    print("=" * 60)

    # Show CLI examples
    print_cli_examples()

    # Run programmatic example (commented out to avoid creating files)
    # print("\n\nRunning programmatic example...")
    # example_programmatic_usage()


if __name__ == "__main__":
    main()
