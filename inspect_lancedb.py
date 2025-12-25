
import lancedb
import asyncio
import inspect
from lancedb.db import DBConnection

async def main():
    print("--- connect_async ---")
    print(lancedb.connect_async)
    print("\n--- DBConnection ---")
    print(DBConnection)
    print("\n--- AsyncConnection (inferred via connect_async return) ---")
    try:
        # We can't easily connect without a valid URI, but we can inspect the source code of connect_async if possible
        # or just print docstring
        print(lancedb.connect_async.__annotations__)
    except AttributeError:
        pass
    
    print("\n--- Listing lancedb attributes ---")
    for name in dir(lancedb):
        if "Async" in name:
            print(f"- {name}")

if __name__ == "__main__":
    asyncio.run(main())
