
import asyncio
import lancedb
from lancedb.db import AsyncConnection

async def main():
    db = await lancedb.connect_async("data/test_db_check")
    print(f"drop_table exists: {hasattr(db, 'drop_table')}")
    print(f"table_names exists: {hasattr(db, 'table_names')}")
    if hasattr(db, 'drop_table'):
         print(f"drop_table doc: {db.drop_table.__doc__}")

if __name__ == "__main__":
    asyncio.run(main())
