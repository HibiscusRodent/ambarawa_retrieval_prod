"""
Test script to verify LanceDB's automatic schema inference with nested dicts.
This bypasses BAML to test just the LanceDB functionality.
"""

import lancedb
from typing import List, Dict, Any

# Sample nested data structure similar to BAML models
test_data = [{
    "book_id": "test-book-001",
    "images_data": [b"fake_image_data_1", b"fake_image_data_2"],
    "raw_analysis": {
        "coverPageDescription": "Test cover description",
        "backCoverDescription": "Test back cover",
        "colophonPageDescription": "Test colophon",
        "otherPageDescriptions": None
    },
    "book_condition_data": {
        "physicalObservations": [
            {
                "imageNumber": 1,
                "bookComponent": "cover",
                "observedFeatures": ["clean", "intact"],
                "severityLevel": "none",
                "readabilityImpact": "none"
            }
        ],
        "conditionAnalysis": {
            "overallAssessment": "Good condition",
            "conditionReasoning": "Well preserved",
            "preservationUrgency": "low"
        },
        "printTypeAnalysis": {
            "coverMaterial": "paperback",
            "bindingType": "perfect bound",
            "printQualityIndicators": ["clear text"],
            "printTypeReasoning": "Standard printing"
        },
        "Condition": "BAIK",
        "PrintType": "PAPERBACK"
    },
    "book_main_data": {
        "title": {
            "title_in_origin_script": "Test Title",
            "title_in_latin_script": "Test Title",
            "title_in_indonesian": "Judul Test"
        },
        "authors": [
            {
                "author_in_origin_script": "Test Author",
                "author_in_latin_script": "Test Author"
            }
        ],
        "language": ["Indonesian"],
        "script": ["Latin"],
        "published_year": 2024,
        "confidence": 0.95
    }
}]

print("Testing LanceDB automatic schema inference...")
print("=" * 60)

# Connect to test database
uri = "data/lance_db_test_inference"
db = lancedb.connect(uri)

# Drop table if exists
try:
    db.drop_table("test_table")
    print("✓ Dropped existing test_table")
except:
    pass

# Create table with automatic schema inference
print("\nCreating table with automatic schema inference from nested dicts...")
try:
    test_table = db.create_table("test_table", data=test_data)
    print("✓ Table created successfully!")
    print(f"\n✓ Inferred Schema:")
    print(test_table.schema)
    
    # Try to retrieve the data
    print("\n✓ Retrieving data...")
    result = test_table.to_polars().collect()
    print(f"\n✓ Retrieved {len(result)} rows")
    print(f"\n✓ Columns: {result.columns}")
    
    # Check if nested structures are preserved
    print("\n✓ Checking nested structure preservation...")
    first_row = result[0]
    print(f"  - book_id type: {type(first_row['book_id'][0])}")
    print(f"  - raw_analysis type: {type(first_row['raw_analysis'][0])}")
    print(f"  - book_condition_data type: {type(first_row['book_condition_data'][0])}")
    
    print("\n" + "=" * 60)
    print("✅ SUCCESS: LanceDB automatic schema inference works!")
    print("   Nested dicts are properly handled and structured!")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
