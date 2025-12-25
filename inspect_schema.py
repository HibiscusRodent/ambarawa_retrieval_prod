from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)
import json

def print_schema(cls):
    print(f"--- Schema for {cls.__name__} ---")
    try:
        # Pydantic v2
        print(json.dumps(cls.model_json_schema(), indent=2))
    except AttributeError:
        # Pydantic v1
        print(json.dumps(cls.schema(), indent=2))

print_schema(BookConditionData)
print_schema(RawAnalysis)
print_schema(BookContentHints)
print_schema(BookMainData)
print_schema(BookPubAndDistDetails)
