"""
Helper script to recreate the LanceDB table with the correct schema.
Run this ONLY if you want to drop and recreate the active_table.
"""

import lancedb
import pyarrow as pa

# Connect to the database
uri = "data/lance_db_semi_prod"
db = lancedb.connect(uri)

# Drop the old table if it exists
try:
    db.drop_table("active_table")
    print("✓ Dropped existing 'active_table'")
except Exception as e:
    print(f"Note: {e}")

# Define schema for LanceDB using PyArrow
# Store complex nested structures as JSON strings for simplicity
full_data_model_pa_schema = pa.schema([
    ("book_id", pa.string()),
    ("images_data", pa.list_(pa.binary())),
    ("raw_analysis", pa.string()),  # JSON string
    ("book_condition_data", pa.string()),  # JSON string
    ("book_content_hints", pa.string()),  # JSON string
    ("book_main_data", pa.string()),  # JSON string
    ("book_pub_and_dist_details", pa.string())  # JSON string
])

# Create the table with the new schema
active_tbl = db.create_table("active_table", schema=full_data_model_pa_schema)
print("✓ Created 'active_table' with new schema")
print(f"✓ Schema:\n{active_tbl.schema}")
