"""Scoring modules for benchmark."""

from .calculator import ScoringCalculator, ScoreWeights, calculate_scores, create_report
from .multi_section import (
    MultiSectionEvaluator,
    ReportConfig,
    SectionConfig,
    evaluate_report_config,
)
from .model_comparison import (
    ModelComparisonRunner,
    ComparisonConfig,
    ComparisonReport,
    ModelConfig,
    ModelResult,
)

__all__ = [
    'ScoringCalculator',
    'ScoreWeights',
    'calculate_scores',
    'create_report',
    # Multi-section
    'MultiSectionEvaluator',
    'ReportConfig',
    'SectionConfig',
    'evaluate_report_config',
    # Model comparison
    'ModelComparisonRunner',
    'ComparisonConfig',
    'ComparisonReport',
    'ModelConfig',
    'ModelResult',
]
