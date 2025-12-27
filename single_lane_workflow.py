import baml_client.types as baml_types
import types_utils.pydantic_to_lance_schema as pyd_to_lance

import lancedb
from pathlib import Path


# get some basic folder paths
book_folder_path = Path("sample_data/rak-0018_baris-002_buku-12")
output_folder_path = Path("data/output_book_data/pydantic_try")
lance_db_uri = Path("data/test/single_lane_experiment")
table_name = "run_single_lane"

# connect to lance db
active_db = lancedb.connect(lance_db_uri.as_posix())

# initialize the schema, and convert it to lance schema
bookConditionDataLance = pyd_to_lance.pydantic_to_arrow_schema(baml_types.BookConditionData)

# create an empty table using the schema
# TODO please change the overwrite mode later, this is just for testing
active_db.create_table(table_name, schema=bookConditionDataLance, mode="overwrite")
print(f"Created LanceDB table '{table_name}' at '{lance_db_uri.as_posix()}' with BookConditionData schema.")