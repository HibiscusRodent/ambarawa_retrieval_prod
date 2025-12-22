"""
Helper script to drop the LanceDB table if needed.
With the new approach, the table schema is automatically inferred from data,
so you don't need to recreate the table with a predefined schema.

Run this ONLY if you want to drop the active_table and start fresh.
"""

import lancedb

# Connect to the database
uri = "data/lance_db_semi_prod"
db = lancedb.connect(uri)

# Drop the old table if it exists
try:
    db.drop_table("active_table")
    print("✓ Dropped existing 'active_table'")
    print("✓ The table will be recreated automatically when you run semi_prod.py")
    print("✓ Schema will be inferred from your data structure")
except Exception as e:
    print(f"Note: {e}")
