# Ambarawa Retrieval System - AI Agent Guide

## Project Overview
This system performs automatic cataloging of ~10,000 books from Ambarawa Library using computer vision. Field workers capture photos (front cover, back cover, colophon page), and LLMs with vision capabilities extract metadata to build a searchable database using LanceDB.

**Tech Stack**: Python 3.13+ | BAML (LLM orchestration) | LanceDB (vector database) | Polars/PyArrow | PIL/PyMuPDF | Pydantic

## Critical Workflows

### Running the Cataloging Pipeline
```powershell
# Activate virtual environment (uv-managed)
.venv\Scripts\activate

# Process a book folder (main script)
uv run python semi_prod.py

# Drop and recreate LanceDB table
uv run python recreate_table.py
```

### Code Quality Enforcement (MANDATORY after edits)
```powershell
# 1. Lint and format (required after every edit session)
uvx ruff check
uvx ruff format

# 2. Type checking with pyrefly
uvx pyrefly check --summarize-errors

# 3. Auto-infer types when adding new code
uvx pyrefly infer path/to/file.py
```

**Note**: The project runs on Windows 11 with 16GB RAM (see [machine_specifications.md](machine_specifications.md)). Use PowerShell commands.

## Architecture & Data Flow

### 1. Image Processing Pipeline ([image_processors.py](image_processors.py))
```
BookFolderPathData → ImageProcessors.process_book_folder() → ProcessedBookData
```
- **Input**: `sample_data/rak-XXXX_baris-XXX_buku-XX/` folders containing JPG/PNG/PDF images
- **Processing**: 
  - Loads images/PDFs using PIL/PyMuPDF
  - Resizes to max 800x800px (default DPI: 150 for PDFs)
  - Generates 3 formats: `base64_images` (LanceDB), `binary_images` (API), `baml_images` (BAML functions)
  - Parallel processing via joblib (`n_jobs=-1`)
- **Output**: `ProcessedBookData` with book_id and multi-format images

### 2. BAML Extraction Chain ([semi_prod.py](semi_prod.py))
Sequential LLM calls to extract structured metadata:

```
1. GetBookrawVisual (Gemini20FlashLite)
   └─> RawAnalysis: Detailed text extraction from cover/back/colophon

2. GetBookConditionData (CustomGPT4oMini)
   └─> BookConditionData: Physical condition + print type

3. GetBookContentHints (CustomSonnet)
   └─> ContentHints: Genre, NER, fiction/non-fiction, blurb
   └─> Uses RawAnalysis JSON as context

4. GetBookMainData (CustomGPT4oMini)
   └─> BookMainData: Title (3 scripts), authors, ISBN, language
   └─> Uses RawAnalysis + TextExtractionEvidence + DataComparison

5. GetBookPublisherData (CustomGPT4oMini)
   └─> BookPubAndDistDetails: Publisher/distributor with locations
```

**Why this order?** Raw visual extraction first provides grounded evidence for all downstream extractions, reducing hallucinations.

### 3. LanceDB Storage Strategy
```python
# Nested dicts preserved with field labels (NOT JSON strings)
data_to_ingest = [{
    "book_id": str,
    "images_data": list[bytes],  # Binary images for search
    "book_title": {"title_in_origin_script": str, "title_in_latin_script": str, ...},
    "isbns": {"isbn_10": str, "isbn_13": str},
    "authors": [{"author_in_origin_script": str, ...}],
    # Full model dumps for reasoning transparency
    "book_main_data": dict,
    "raw_analysis": dict,
    ...
}]
```
- **Cloud deployment**: `db://ambarawa-book-retrieval-x3jev2` (us-east-1)
- **Schema**: Auto-inferred from nested dicts (no manual PyArrow schema needed)
- **Outputs**: JSON files + Parquet in `data/output_book_data/{book_id}/`

## BAML Configuration Essentials

### Client Definitions ([baml_src/clients.baml](baml_src/clients.baml))
```baml
client<llm> CustomGPT4oMini {
  provider openai
  retry_policy Exponential
  options { model "gpt-4o-mini", api_key env.OPENAI_API_KEY }
}

client<llm> VisionModelQwen25_24b {
  provider "openai-generic"
  options {
    base_url "https://openrouter.ai/api/v1"
    model "qwen/qwen2.5-vl-32b-instruct"
    api_key env.OPENROUTER_KEY_PROD
  }
}
```
**Environment variables required**: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENROUTER_KEY_PROD`, `LANCEDB_API_KEY_PROD`

### Multi-Script Handling Pattern ([baml_src/bookMainData.baml](baml_src/bookMainData.baml))
All text fields capture 3 representations:
- `*_in_origin_script`: Original script (Cyrillic, Arabic, Chinese, etc.)
- `*_in_latin_script`: Transliterated to ASCII-safe Latin
- `*_in_indonesian`: Indonesian translation

**Rationale**: Preserves cultural accuracy while enabling cross-linguistic search.

## Project-Specific Conventions

### 1. Object-Oriented Design
Organize code as classes with methods (see `ImageProcessors` class pattern). Avoid standalone utility functions.

### 2. Comprehensive Docstrings
```python
class BookFolderPathData(BaseModel):
    """
    Pydantic model representing the input data required for book folder processing.

    This class encapsulates the filesystem path to a book folder and provides
    utility properties to extract book metadata, such as the book ID.
    """
```
Write for readers **without specialized expertise** but basic Python knowledge.

### 3. Strong Typing (Pydantic + Type Hints)
- All data models use Pydantic `BaseModel`
- Type hints required for all functions/methods
- Use `pyrefly infer` to auto-generate missing types

### 4. Error Handling with Rich Traceback
```python
from rich.traceback import install
install()  # Pretty error printing enabled globally
```

### 5. File Naming Convention
Output structure: `data/output_book_data/{book_id}/{book_id}_{data_type}.json`
- Example: `rak-0018_baris-002_buku-12_book_main_data.json`

## Critical Integration Points

### BAML Client Usage Pattern
```python
from baml_client.sync_client import b
from baml_client.types import BookMainData

# Rebuild models before use (resolves forward references)
BookMainData.model_rebuild()

# Call BAML function
result: BookMainData = b.GetBookMainData(
    MultiImages=baml_images,
    bookId=book_id,
    RawVisualNote=raw_analysis.model_dump_json()
)
```

### LanceDB Connection
```python
import lancedb
db = lancedb.connect(
    uri="db://ambarawa-book-retrieval-x3jev2",
    api_key=os.getenv("LANCEDB_API_KEY_PROD"),
    region="us-east-1"
)
tbl = db.create_table("active_table", data=data, mode="overwrite")
```

### Image Format Conversion
```python
ip = ImageProcessors()
book_folder = BookFolderPathData(path="sample_data/rak-0018_baris-002_buku-12")
images_data = ip.process_book_folder(book_folder)

# Use appropriate format for each consumer
baml_images   # For BAML functions (b.GetBook*)
binary_images # For LanceDB storage
base64_images # For columnar storage formats
```

## Development Notes

- **TODO**: Migrate BAML prompts to Bahasa Indonesia for better localization (currently English)
- **BAML Generation**: Run `baml generate` after modifying `.baml` files to update `baml_client/`
- **Virtual Env**: Project uses `uv` package manager (NOT pip/poetry). Virtual env is in `list/` (non-standard location)
- **Dependencies**: Managed via `pyproject.toml` + `requirements.txt` (sync with `uv add`/`uv remove`)

## Common Tasks

### Adding a New BAML Extraction Function
1. Define types/function in `baml_src/*.baml`
2. Run `baml generate` (regenerates `baml_client/`)
3. Import types: `from baml_client.types import NewType`
4. Call function: `result = b.NewFunction(...)`
5. Add to extraction chain in [semi_prod.py](semi_prod.py)

### Processing a New Book Batch
1. Place photos in `sample_data/{book_folder_name}/`
2. Update `sample_book_folder_path` in [semi_prod.py](semi_prod.py)
3. Run `uv run python semi_prod.py`
4. Check outputs in `data/output_book_data/{book_id}/`

### Debugging LLM Extractions
- JSON outputs stored per-book in `data/output_book_data/{book_id}/`
- Full reasoning chains saved in `*_data.json` fields
- Use `raw_analysis.json` to verify visual extraction accuracy

---

**Related Instructions**: [.github/instructions/python_working_rules.instructions.md](.github/instructions/python_working_rules.instructions.md) (detailed Python tooling rules)
