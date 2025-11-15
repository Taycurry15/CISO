"""
Confidence Scoring Service
Calculates confidence scores for AI-generated findings
"""

import logging
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class ConfidenceLevel(str, Enum):
    """Confidence level categories"""
    VERY_HIGH = "Very High"  # 90-100%
    HIGH = "High"            # 75-89%
    MEDIUM = "Medium"        # 60-74%
    LOW = "Low"              # 40-59%
    VERY_LOW = "Very Low"    # 0-39%


@dataclass
class ConfidenceFactors:
    """
    Factors that contribute to confidence score

    Each factor is a float between 0 and 1:
    - 1.0 = Perfect/Ideal
    - 0.5 = Acceptable
    - 0.0 = Poor/Missing
    """
    evidence_quality: float  # Quality/relevance of evidence
    evidence_quantity: float  # Sufficient evidence available
    evidence_recency: float  # How recent is the evidence
    provider_inheritance: float  # Provider inheritance certainty
    ai_certainty: float  # AI model's confidence in its answer


@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of confidence score"""
    overall_score: float
    confidence_level: ConfidenceLevel
    factors: ConfidenceFactors
    weighted_scores: Dict[str, float]
    explanation: str
    recommendations: List[str]


class ConfidenceScorer:
    """
    Service for calculating confidence scores for AI-generated findings

    The confidence score represents how certain we are that the AI's
    assessment is accurate and defensible in a C3PAO audit.

    Factors considered:
    1. Evidence Quality (40%) - Relevance and directness of evidence
    2. Evidence Quantity (20%) - Sufficient evidence to support finding
    3. Evidence Recency (15%) - How current is the evidence
    4. Provider Inheritance (15%) - Certainty about inherited controls
    5. AI Certainty (10%) - Model's confidence in its analysis
    """

    def __init__(
        self,
        evidence_quality_weight: float = 0.40,
        evidence_quantity_weight: float = 0.20,
        evidence_recency_weight: float = 0.15,
        provider_inheritance_weight: float = 0.15,
        ai_certainty_weight: float = 0.10
    ):
        """
        Initialize confidence scorer with custom weights

        Args:
            evidence_quality_weight: Weight for evidence quality (default: 0.40)
            evidence_quantity_weight: Weight for evidence quantity (default: 0.20)
            evidence_recency_weight: Weight for evidence recency (default: 0.15)
            provider_inheritance_weight: Weight for provider inheritance (default: 0.15)
            ai_certainty_weight: Weight for AI certainty (default: 0.10)
        """
        self.weights = {
            'evidence_quality': evidence_quality_weight,
            'evidence_quantity': evidence_quantity_weight,
            'evidence_recency': evidence_recency_weight,
            'provider_inheritance': provider_inheritance_weight,
            'ai_certainty': ai_certainty_weight
        }

        # Validate weights sum to 1.0
        total_weight = sum(self.weights.values())
        if abs(total_weight - 1.0) > 0.01:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")

        logger.info(f"Initialized ConfidenceScorer with weights: {self.weights}")

    def calculate_confidence(
        self,
        factors: ConfidenceFactors
    ) -> float:
        """
        Calculate overall confidence score

        Args:
            factors: Confidence factors (all values 0-1)

        Returns:
            Confidence score between 0 and 1
        """
        # Validate factor values
        for field_name, field_value in factors.__dict__.items():
            if not 0 <= field_value <= 1:
                logger.warning(f"Factor {field_name} out of range: {field_value}")
                # Clamp to valid range
                setattr(factors, field_name, max(0.0, min(1.0, field_value)))

        # Calculate weighted score
        score = (
            factors.evidence_quality * self.weights['evidence_quality'] +
            factors.evidence_quantity * self.weights['evidence_quantity'] +
            factors.evidence_recency * self.weights['evidence_recency'] +
            factors.provider_inheritance * self.weights['provider_inheritance'] +
            factors.ai_certainty * self.weights['ai_certainty']
        )

        # Ensure score is in valid range
        score = max(0.0, min(1.0, score))

        logger.debug(f"Calculated confidence: {score:.2%}")
        return score

    def calculate_with_breakdown(
        self,
        factors: ConfidenceFactors
    ) -> ConfidenceBreakdown:
        """
        Calculate confidence with detailed breakdown

        Args:
            factors: Confidence factors

        Returns:
            Detailed confidence breakdown
        """
        overall_score = self.calculate_confidence(factors)

        # Calculate weighted contributions
        weighted_scores = {
            'evidence_quality': factors.evidence_quality * self.weights['evidence_quality'],
            'evidence_quantity': factors.evidence_quantity * self.weights['evidence_quantity'],
            'evidence_recency': factors.evidence_recency * self.weights['evidence_recency'],
            'provider_inheritance': factors.provider_inheritance * self.weights['provider_inheritance'],
            'ai_certainty': factors.ai_certainty * self.weights['ai_certainty']
        }

        # Determine confidence level
        confidence_level = self.get_confidence_level(overall_score)

        # Generate explanation
        explanation = self._generate_explanation(overall_score, factors, weighted_scores)

        # Generate recommendations
        recommendations = self._generate_recommendations(factors)

        return ConfidenceBreakdown(
            overall_score=overall_score,
            confidence_level=confidence_level,
            factors=factors,
            weighted_scores=weighted_scores,
            explanation=explanation,
            recommendations=recommendations
        )

    def get_confidence_level(self, score: float) -> ConfidenceLevel:
        """
        Convert numeric score to confidence level

        Args:
            score: Confidence score (0-1)

        Returns:
            Confidence level category
        """
        if score >= 0.90:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.75:
            return ConfidenceLevel.HIGH
        elif score >= 0.60:
            return ConfidenceLevel.MEDIUM
        elif score >= 0.40:
            return ConfidenceLevel.LOW
        else:
            return ConfidenceLevel.VERY_LOW

    def _generate_explanation(
        self,
        score: float,
        factors: ConfidenceFactors,
        weighted_scores: Dict[str, float]
    ) -> str:
        """Generate human-readable explanation of confidence score"""

        level = self.get_confidence_level(score)

        # Start with overall assessment
        explanation = f"Confidence Level: {level.value} ({score:.1%})\n\n"

        # Identify strengths
        strengths = []
        weaknesses = []

        for factor_name, factor_value in factors.__dict__.items():
            if factor_value >= 0.8:
                strengths.append(self._factor_name_friendly(factor_name))
            elif factor_value < 0.5:
                weaknesses.append(self._factor_name_friendly(factor_name))

        if strengths:
            explanation += "Strengths:\n"
            for strength in strengths:
                explanation += f"  ✓ {strength}\n"
            explanation += "\n"

        if weaknesses:
            explanation += "Areas of Concern:\n"
            for weakness in weaknesses:
                explanation += f"  ⚠ {weakness}\n"
            explanation += "\n"

        # Add factor breakdown
        explanation += "Factor Breakdown:\n"
        for factor_name, weighted_value in weighted_scores.items():
            factor_value = getattr(factors, factor_name)
            contribution = weighted_value / score * 100 if score > 0 else 0
            explanation += f"  • {self._factor_name_friendly(factor_name)}: {factor_value:.1%} (contributes {contribution:.1f}%)\n"

        return explanation

    def _generate_recommendations(self, factors: ConfidenceFactors) -> List[str]:
        """Generate recommendations for improving confidence"""
        recommendations = []

        if factors.evidence_quality < 0.6:
            recommendations.append(
                "Obtain more direct evidence (e.g., screenshots, configuration exports, test results)"
            )

        if factors.evidence_quantity < 0.6:
            recommendations.append(
                "Gather additional evidence from multiple sources to corroborate findings"
            )

        if factors.evidence_recency < 0.6:
            recommendations.append(
                "Update evidence to reflect current state (evidence may be outdated)"
            )

        if factors.provider_inheritance < 0.6:
            recommendations.append(
                "Clarify provider inheritance responsibilities with documentation"
            )

        if factors.ai_certainty < 0.6:
            recommendations.append(
                "AI analysis is uncertain - recommend manual assessor review"
            )

        if not recommendations:
            recommendations.append("Confidence is high - finding is well-supported by evidence")

        return recommendations

    def _factor_name_friendly(self, factor_name: str) -> str:
        """Convert factor name to friendly display name"""
        return factor_name.replace('_', ' ').title()

    def assess_evidence_quality(
        self,
        evidence_count: int,
        avg_relevance_score: float,
        has_direct_evidence: bool = False,
        evidence_types_count: int = 1
    ) -> float:
        """
        Assess evidence quality based on multiple factors

        Args:
            evidence_count: Number of evidence items
            avg_relevance_score: Average relevance score (0-1)
            has_direct_evidence: Whether direct evidence exists
            evidence_types_count: Number of different evidence types

        Returns:
            Quality score (0-1)
        """
        # Base score from relevance
        quality = avg_relevance_score

        # Bonus for direct evidence (screenshots, configs, test results)
        if has_direct_evidence:
            quality = min(quality + 0.1, 1.0)

        # Bonus for diverse evidence types
        diversity_bonus = min((evidence_types_count - 1) * 0.05, 0.15)
        quality = min(quality + diversity_bonus, 1.0)

        # Penalty for very low evidence count
        if evidence_count == 0:
            quality = 0.0
        elif evidence_count == 1:
            quality *= 0.7

        return quality

    def assess_evidence_quantity(
        self,
        evidence_count: int,
        objectives_count: int = 1
    ) -> float:
        """
        Assess if sufficient evidence is available

        Args:
            evidence_count: Number of evidence items
            objectives_count: Number of assessment objectives

        Returns:
            Quantity score (0-1)
        """
        # Ideal: 2+ evidence items per objective
        ideal_count = objectives_count * 2

        if evidence_count >= ideal_count:
            return 1.0
        elif evidence_count >= objectives_count:
            return 0.7 + (evidence_count - objectives_count) / objectives_count * 0.3
        elif evidence_count > 0:
            return 0.4 + (evidence_count / objectives_count * 0.3)
        else:
            return 0.0

    def assess_evidence_recency(
        self,
        most_recent_date: Optional[datetime],
        max_age_days: int = 180
    ) -> float:
        """
        Assess how recent evidence is

        Args:
            most_recent_date: Date of most recent evidence
            max_age_days: Maximum acceptable age in days (default: 180 = 6 months)

        Returns:
            Recency score (0-1)
        """
        if most_recent_date is None:
            return 0.5  # Unknown - neutral score

        age_days = (datetime.utcnow() - most_recent_date).days

        if age_days <= 30:
            return 1.0  # Very recent
        elif age_days <= 90:
            return 0.9  # Recent
        elif age_days <= max_age_days:
            # Linear decay from 0.9 to 0.5
            return 0.9 - (age_days - 90) / (max_age_days - 90) * 0.4
        else:
            # Older than max age
            # Exponential decay beyond max age
            extra_days = age_days - max_age_days
            return max(0.5 * (0.95 ** (extra_days / 30)), 0.1)

    def assess_provider_inheritance(
        self,
        responsibility: Optional[str],
        has_documentation: bool = False
    ) -> float:
        """
        Assess provider inheritance certainty

        Args:
            responsibility: "Inherited", "Shared", "Customer", or None
            has_documentation: Whether provider documentation exists

        Returns:
            Inheritance certainty score (0-1)
        """
        if responsibility is None:
            return 0.5  # No provider - neutral

        base_scores = {
            "Inherited": 1.0,  # Fully inherited
            "Shared": 0.7,     # Shared responsibility
            "Customer": 0.5    # Customer responsibility (no inheritance benefit)
        }

        score = base_scores.get(responsibility, 0.5)

        # Bonus for documentation
        if has_documentation and responsibility in ["Inherited", "Shared"]:
            score = min(score + 0.1, 1.0)

        return score


# Convenience function
def calculate_confidence(
    evidence_quality: float,
    evidence_quantity: float,
    evidence_recency: float = 0.8,
    provider_inheritance: float = 0.5,
    ai_certainty: float = 0.7
) -> float:
    """
    Quick confidence calculation with default weights

    Args:
        evidence_quality: Evidence quality score (0-1)
        evidence_quantity: Evidence quantity score (0-1)
        evidence_recency: Evidence recency score (0-1, default: 0.8)
        provider_inheritance: Provider inheritance score (0-1, default: 0.5)
        ai_certainty: AI certainty score (0-1, default: 0.7)

    Returns:
        Confidence score (0-1)
    """
    scorer = ConfidenceScorer()
    factors = ConfidenceFactors(
        evidence_quality=evidence_quality,
        evidence_quantity=evidence_quantity,
        evidence_recency=evidence_recency,
        provider_inheritance=provider_inheritance,
        ai_certainty=ai_certainty
    )
    return scorer.calculate_confidence(factors)


# Example usage and testing
if __name__ == "__main__":
    # Initialize scorer
    scorer = ConfidenceScorer()

    # Example 1: High confidence scenario
    print("=== Example 1: High Confidence ===")
    factors_high = ConfidenceFactors(
        evidence_quality=0.9,    # Excellent evidence
        evidence_quantity=0.8,   # Sufficient quantity
        evidence_recency=0.9,    # Very recent
        provider_inheritance=1.0, # Fully inherited
        ai_certainty=0.85        # High AI confidence
    )

    breakdown_high = scorer.calculate_with_breakdown(factors_high)
    print(f"Score: {breakdown_high.overall_score:.1%}")
    print(f"Level: {breakdown_high.confidence_level.value}")
    print(f"\n{breakdown_high.explanation}")
    print("\nRecommendations:")
    for rec in breakdown_high.recommendations:
        print(f"  • {rec}")

    # Example 2: Low confidence scenario
    print("\n\n=== Example 2: Low Confidence ===")
    factors_low = ConfidenceFactors(
        evidence_quality=0.4,    # Poor evidence quality
        evidence_quantity=0.3,   # Insufficient evidence
        evidence_recency=0.5,    # Somewhat outdated
        provider_inheritance=0.5, # No provider inheritance
        ai_certainty=0.6         # Medium AI confidence
    )

    breakdown_low = scorer.calculate_with_breakdown(factors_low)
    print(f"Score: {breakdown_low.overall_score:.1%}")
    print(f"Level: {breakdown_low.confidence_level.value}")
    print(f"\n{breakdown_low.explanation}")
    print("\nRecommendations:")
    for rec in breakdown_low.recommendations:
        print(f"  • {rec}")

    # Example 3: Helper functions
    print("\n\n=== Example 3: Helper Functions ===")

    quality = scorer.assess_evidence_quality(
        evidence_count=5,
        avg_relevance_score=0.85,
        has_direct_evidence=True,
        evidence_types_count=3
    )
    print(f"Evidence Quality: {quality:.1%}")

    quantity = scorer.assess_evidence_quantity(
        evidence_count=3,
        objectives_count=2
    )
    print(f"Evidence Quantity: {quantity:.1%}")

    recency = scorer.assess_evidence_recency(
        most_recent_date=datetime.utcnow() - timedelta(days=45)
    )
    print(f"Evidence Recency: {recency:.1%}")

    inheritance = scorer.assess_provider_inheritance(
        responsibility="Shared",
        has_documentation=True
    )
    print(f"Provider Inheritance: {inheritance:.1%}")
