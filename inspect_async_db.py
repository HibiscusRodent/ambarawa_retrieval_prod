
import asyncio
import lancedb
import inspect

async def main():
    db = await lancedb.connect_async("data/test_db")
    print(f"Type: {type(db)}")
    print(f"Attributes: {dir(db)}")
    if hasattr(db, 'create_table'):
        print(f"create_table: {db.create_table}")
        print(f"create_table annotations: {db.create_table.__annotations__}")
        print(f"create_table signature: {inspect.signature(db.create_table)}")

if __name__ == "__main__":
    asyncio.run(main())
