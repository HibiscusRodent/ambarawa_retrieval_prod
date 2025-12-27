from typing import List
from lancedb.pydantic import LanceModel, Vector


class ConditionAnalysis:
    overall_assessment: str
    condition_reasoning: str
    preservation_urgency: str

    def __init__(self, overall_assessment: str, condition_reasoning: str, preservation_urgency: str) -> None:
        self.overall_assessment = overall_assessment
        self.condition_reasoning = condition_reasoning
        self.preservation_urgency = preservation_urgency


class PhysicalObservation:
    image_number: int
    book_component: str
    observed_features: List[str]
    severity_level: str
    readability_impact: str

    def __init__(self, image_number: int, book_component: str, observed_features: List[str], severity_level: str, readability_impact: str) -> None:
        self.image_number = image_number
        self.book_component = book_component
        self.observed_features = observed_features
        self.severity_level = severity_level
        self.readability_impact = readability_impact


class PrintTypeAnalysis:
    cover_material: str
    binding_type: str
    print_quality_indicators: List[str]
    print_type_reasoning: str

    def __init__(self, cover_material: str, binding_type: str, print_quality_indicators: List[str], print_type_reasoning: str) -> None:
        self.cover_material = cover_material
        self.binding_type = binding_type
        self.print_quality_indicators = print_quality_indicators
        self.print_type_reasoning = print_type_reasoning


class LanceConditionData(LanceModel):
    physical_observations: list[PhysicalObservation]
    condition_analysis: ConditionAnalysis
    print_type_analysis: PrintTypeAnalysis
    condition: str
    print_type: str

    def __init__(self, physical_observations: List[PhysicalObservation], condition_analysis: ConditionAnalysis, print_type_analysis: PrintTypeAnalysis, condition: str, print_type: str) -> None:
        self.physical_observations = physical_observations
        self.condition_analysis = condition_analysis
        self.print_type_analysis = print_type_analysis
        self.condition = condition
        self.print_type = print_type
