from baml_client.types import BookConditionData
from lancedb.pydantic import LanceModel
from types_utils.pydantic_to_lance_schema import pydantic_to_arrow_schema


class LanceBookConditionData(LanceModel):
    book_condition_data : BookConditionData
    
    @classmethod
    def to_arrow_schema(cls):
        return pydantic_to_arrow_schema(cls)