"""
Pydantic schemas for book condition data compatible with LanceDB.

These models define the structure for storing book condition analysis
in a LanceDB table, including physical observations, condition analysis,
and print type information.
"""

import pyarrow as pa
from lancedb.pydantic import LanceModel
from pydantic import BaseModel

from pydantic_to_lance_db_schema import pydantic_to_arrow_schema


class ConditionAnalysis(BaseModel):
    """Analysis of the book's overall condition and preservation needs."""

    overall_assessment: str
    condition_reasoning: str
    preservation_urgency: str


class PhysicalObservationUnit(BaseModel):
    """
    A single observation of physical characteristics for a specific book component.

    This model represents observations from a specific image, documenting
    the condition of a particular book component.
    """

    image_number: int
    book_component: str
    observed_features: list[str]
    severity_level: str
    readability_impact: str


# class PhysicalObservation(BaseModel):
#     """Collection of physical observations for the book."""

#     observations: list[PhysicalObservationUnit]


class PrintTypeAnalysis(BaseModel):
    """Analysis of the book's physical printing and binding characteristics."""

    cover_material: str
    binding_type: str
    print_quality_indicators: list[str]
    print_type_reasoning: str


class LanceConditionData(LanceModel):
    """
    Main LanceDB model for storing complete book condition data.

    This model combines physical observations, condition analysis, and print type
    information into a single record suitable for storage in LanceDB.
    """

    physical_observations: list[PhysicalObservationUnit]
    condition_analysis: ConditionAnalysis
    print_type_analysis: PrintTypeAnalysis
    condition: str
    print_type: str

    @classmethod
    def to_arrow_schema(cls) -> pa.Schema:
        """
        Convert the Pydantic model to an Arrow schema.

        Uses the universal pydantic_to_arrow_schema function that properly handles
        nested Pydantic models within lists (workaround for LanceDB 0.26.0 bug).

        Returns:
            pa.Schema: The PyArrow schema for this model.
        """
        return pydantic_to_arrow_schema(cls)
