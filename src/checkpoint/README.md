# Checkpoint System Documentation

## Overview

The checkpoint system provides robust progress tracking and crash recovery for the book processing pipeline. It logs which book folders have been processed, enabling resumption from interruptions without reprocessing completed books.

## Features

- **Persistent State**: Checkpoint data stored as Parquet files for efficient I/O
- **Crash Recovery**: Automatic reconciliation with LanceDB to detect already-ingested books
- **Granular Tracking**: Book-level completion status (pending/in_progress/completed/failed)
- **Run Isolation**: Each processing run has a unique checkpoint file
- **Progress Monitoring**: Real-time statistics and logging

## Architecture

### Components

1. **models.py**: Pydantic models for checkpoint data structures
   - `ProcessingStatus`: Enum for book states
   - `BookProcessingRecord`: Individual book tracking
   - `CheckpointState`: Overall run state

2. **tracker.py**: Core `CheckpointTracker` class
   - Load/create checkpoints
   - Update book status
   - Persist to Parquet
   - Query pending books

3. **utils.py**: Helper functions
   - `verify_against_lancedb()`: Query existing books in LanceDB
   - `reconcile_checkpoint_with_lancedb()`: Crash recovery logic

4. **__init__.py**: Package exports

### Data Flow

```
┌─────────────────────────────────────────────────────┐
│  Command Line Arguments                             │
│  --run-id, --resume, --reset, --checkpoint-dir      │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Initialize CheckpointTracker                       │
│  - Create checkpoint directory                      │
│  - Set run ID                                       │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Load or Create Checkpoint                          │
│  - If exists: Load from {run_id}.parquet            │
│  - If new: Create with all books as PENDING         │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Reconcile with LanceDB                             │
│  - Query LanceDB for existing book_ids              │
│  - Mark found books as COMPLETED                    │
│  - Handle crash recovery                            │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Get Pending Books                                  │
│  - Filter books with PENDING status                 │
│  - Skip COMPLETED and FAILED                        │
└──────────────────┬──────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────┐
│  Process Books in Batches                           │
│  - Mark as IN_PROGRESS when started                 │
│  - Mark as COMPLETED on success                     │
│  - Mark as FAILED on error                          │
│  - Save checkpoint after each batch                 │
└─────────────────────────────────────────────────────┘
```

## Usage

### Basic Usage (Fresh Run)

```bash
# Start a new processing run
uv run src/main.py

# This creates a checkpoint with timestamp-based run_id:
# data/checkpoints/run_20250101_120000.parquet
```

### Resume from Interruption

```bash
# Resume a specific run
uv run src/main.py --run-id run_20250101_120000 --resume

# The system will:
# 1. Load the existing checkpoint
# 2. Reconcile with LanceDB (crash recovery)
# 3. Process only PENDING books
```

### Reset and Start Fresh

```bash
# Ignore existing checkpoint and start over
uv run src/main.py --run-id run_20250101_120000 --reset

# This deletes the existing checkpoint and creates a new one
```

### Custom Configuration

```bash
uv run src/main.py \
  --run-id my_custom_run \
  --checkpoint-dir data/my_checkpoints \
  --source-parquet data/custom_book_list.parquet \
  --output-folder data/custom_output \
  --lance-db-uri data/custom_lancedb \
  --table-name custom_table \
  --batch-size 10
```

### Command Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--run-id` | str | timestamp | Unique run ID for checkpoint |
| `--resume` | flag | False | Resume from existing checkpoint |
| `--reset` | flag | False | Ignore existing checkpoint |
| `--checkpoint-dir` | str | `data/checkpoints` | Checkpoint directory |
| `--source-parquet` | str | `data/book_folder_list.parquet` | Source book list |
| `--output-folder` | str | `data/output_book_data` | Output directory |
| `--lance-db-uri` | str | `data/test/lance_db_semi_prod` | LanceDB path |
| `--table-name` | str | `pararel_test_new` | LanceDB table name |
| `--batch-size` | int | 5 | Parallel batch size |

## Checkpoint File Structure

Checkpoint files are stored as Parquet with the following schema:

| Column | Type | Description |
|--------|------|-------------|
| `run_id` | str | Unique run identifier |
| `created_at` | datetime | Checkpoint creation time |
| `updated_at` | datetime | Last update time |
| `total_books` | int | Total books in run |
| `processed_count` | int | Successfully processed |
| `failed_count` | int | Failed processing |
| `source_parquet_path` | str | Source book list path |
| `lance_db_uri` | str | LanceDB database path |
| `lance_table_name` | str | Target table name |
| `book_folder_path` | str | Book folder path |
| `book_id` | str | Book identifier |
| `status` | str | `pending`/`in_progress`/`completed`/`failed` |
| `started_at` | datetime | Processing start time |
| `completed_at` | datetime | Processing completion time |
| `error_message` | str | Error details if failed |
| `retry_count` | int | Number of retries |

## Programmatic Usage

### Example: Custom Integration

```python
from pathlib import Path
from checkpoint import CheckpointTracker, reconcile_checkpoint_with_lancedb

# Initialize tracker
tracker = CheckpointTracker(
    checkpoint_dir=Path("data/checkpoints"),
    run_id="my_run",
    lance_db_uri=Path("data/lancedb"),
    lance_table_name="books"
)

# Load or create checkpoint
state = tracker.load_or_create(
    book_folder_paths=["path/to/book1", "path/to/book2"],
    source_parquet_path="data/books.parquet"
)

# Reconcile with LanceDB (crash recovery)
reconcile_checkpoint_with_lancedb(tracker, lance_db, "books")

# Get pending books
pending = tracker.get_pending_books()

# Process each book
for book_path in pending:
    tracker.mark_started(book_path)
    
    try:
        # Your processing logic here
        process_book(book_path)
        
        tracker.mark_completed(book_path)
    except Exception as e:
        tracker.mark_failed(book_path, str(e))
    
    # Save checkpoint after each book
    tracker.save()

# Get final summary
summary = tracker.get_summary()
print(f"Processed: {summary['processed_count']}/{summary['total_books']}")
```

## Crash Recovery

The system handles various crash scenarios:

### Scenario 1: Process Crashes Before Checkpoint Save

1. Book processed and ingested to LanceDB
2. Process crashes before `tracker.save()`
3. On resume: `reconcile_checkpoint_with_lancedb()` detects book in LanceDB
4. Book marked as COMPLETED in checkpoint

### Scenario 2: Process Crashes During Batch

1. Batch partially processed
2. Some books completed, some still pending
3. On resume: Completed books skipped, pending books reprocessed

### Scenario 3: Failed Books

1. Book processing fails with error
2. Marked as FAILED with error message
3. On resume: Currently FAILED books are skipped (no auto-retry)
4. Manual intervention or code fix required

## Best Practices

1. **Run ID Naming**: Use descriptive run IDs for easy identification
   ```bash
   --run-id prod_batch_jan2025
   ```

2. **Regular Checkpoints**: Checkpoint saved after each batch automatically

3. **Monitor Progress**: Check logs for real-time progress statistics

4. **Error Handling**: Review failed books in checkpoint file
   ```python
   df = pl.read_parquet("data/checkpoints/run_xyz.parquet")
   failed = df.filter(pl.col("status") == "failed")
   print(failed.select(["book_id", "error_message"]))
   ```

5. **Disk Space**: Checkpoint files are small (~KB per 1000 books)

## Limitations

1. **No Phase-Level Tracking**: Tracks book completion, not individual phases (image processing, BAML inference, etc.)

2. **No Auto-Retry**: Failed books are not automatically retried on resume (can be added in future)

3. **Single-Instance**: Not designed for distributed/multi-instance processing

4. **No Checkpoint Cleanup**: Old checkpoint files must be manually deleted

## Future Enhancements

- [ ] Auto-retry mechanism for failed books with `--retry-failed` flag
- [ ] Phase-level tracking for partial recovery
- [ ] Checkpoint file cleanup/archival
- [ ] Web dashboard for monitoring progress
- [ ] Distributed processing support
- [ ] Email notifications on completion/failure

## Troubleshooting

### Issue: "Checkpoint state not initialized"
**Solution**: Call `tracker.load_or_create()` before other operations

### Issue: Books reprocessed despite completion
**Solution**: Ensure checkpoint is saved after each batch with `tracker.save()`

### Issue: LanceDB reconciliation not working
**Solution**: Check table name matches and LanceDB connection is valid

### Issue: Cannot resume - checkpoint not found
**Solution**: Verify run_id matches existing checkpoint file name

## Support

For issues or questions about the checkpoint system, please:
1. Check this documentation
2. Review checkpoint Parquet file with Polars/Pandas
3. Check Prefect logs for detailed error messages
4. Consult the codebase maintainer
