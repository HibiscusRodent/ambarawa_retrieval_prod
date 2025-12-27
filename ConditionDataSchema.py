"""
Pydantic schemas for book condition data compatible with LanceDB.

These models define the structure for storing book condition analysis
in a LanceDB table, including physical observations, condition analysis,
and print type information.
"""

import pyarrow as pa
from lancedb.pydantic import LanceModel
from pydantic import BaseModel


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


class PhysicalObservation(BaseModel):
    """Collection of physical observations for the book."""

    observations: list[PhysicalObservationUnit]


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

    physical_observations: PhysicalObservation
    condition_analysis: ConditionAnalysis
    print_type_analysis: PrintTypeAnalysis
    condition: str
    print_type: str

    @classmethod
    def to_arrow_schema(cls) -> pa.Schema:
        """
        Convert the Pydantic model to an Arrow schema.

        This is a workaround for a bug in LanceDB 0.26.0 where nested Pydantic models
        within lists are not properly converted to Arrow types.

        Returns:
            pa.Schema: The PyArrow schema for this model.
        """
        # Define the nested struct for PhysicalObservationUnit
        physical_observation_unit_struct = pa.struct(
            [
                pa.field("image_number", pa.int64(), nullable=False),
                pa.field("book_component", pa.utf8(), nullable=False),
                pa.field("observed_features", pa.list_(pa.utf8()), nullable=False),
                pa.field("severity_level", pa.utf8(), nullable=False),
                pa.field("readability_impact", pa.utf8(), nullable=False),
            ]
        )

        # Define the nested struct for PhysicalObservation
        physical_observation_struct = pa.struct(
            [
                pa.field(
                    "observations",
                    pa.list_(physical_observation_unit_struct),
                    nullable=False,
                ),
            ]
        )

        # Define the nested struct for ConditionAnalysis
        condition_analysis_struct = pa.struct(
            [
                pa.field("overall_assessment", pa.utf8(), nullable=False),
                pa.field("condition_reasoning", pa.utf8(), nullable=False),
                pa.field("preservation_urgency", pa.utf8(), nullable=False),
            ]
        )

        # Define the nested struct for PrintTypeAnalysis
        print_type_analysis_struct = pa.struct(
            [
                pa.field("cover_material", pa.utf8(), nullable=False),
                pa.field("binding_type", pa.utf8(), nullable=False),
                pa.field(
                    "print_quality_indicators", pa.list_(pa.utf8()), nullable=False
                ),
                pa.field("print_type_reasoning", pa.utf8(), nullable=False),
            ]
        )

        # Combine into the main schema
        return pa.schema(
            [
                pa.field(
                    "physical_observations", physical_observation_struct, nullable=False
                ),
                pa.field(
                    "condition_analysis", condition_analysis_struct, nullable=False
                ),
                pa.field(
                    "print_type_analysis", print_type_analysis_struct, nullable=False
                ),
                pa.field("condition", pa.utf8(), nullable=False),
                pa.field("print_type", pa.utf8(), nullable=False),
            ]
        )
