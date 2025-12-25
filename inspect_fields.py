from baml_client.types import (
    BookConditionData,
    RawAnalysis,
    BookContentHints,
    BookMainData,
    BookPubAndDistDetails,
)

def get_field_info(cls):
    print(f"\n--- Fields for {cls.__name__} ---")
    for name, field in cls.model_fields.items():
        print(f"{name}: {field.annotation}")

get_field_info(BookConditionData)
get_field_info(RawAnalysis)
get_field_info(BookContentHints)
get_field_info(BookMainData)
get_field_info(BookPubAndDistDetails)
