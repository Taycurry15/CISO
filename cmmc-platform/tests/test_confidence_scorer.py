"""
Tests for Confidence Scoring Service
"""

import pytest
from datetime import datetime, timedelta

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from services.confidence_scorer import (
    ConfidenceScorer,
    ConfidenceFactors,
    ConfidenceLevel,
    ConfidenceBreakdown,
    calculate_confidence
)


@pytest.fixture
def scorer():
    """Create confidence scorer instance"""
    return ConfidenceScorer()


def test_calculate_confidence_high(scorer):
    """Test high confidence scenario"""
    factors = ConfidenceFactors(
        evidence_quality=0.9,
        evidence_quantity=0.8,
        evidence_recency=0.9,
        provider_inheritance=1.0,
        ai_certainty=0.85
    )

    score = scorer.calculate_confidence(factors)

    assert 0.85 <= score <= 0.95  # Should be high
    assert scorer.get_confidence_level(score) in [ConfidenceLevel.HIGH, ConfidenceLevel.VERY_HIGH]


def test_calculate_confidence_low(scorer):
    """Test low confidence scenario"""
    factors = ConfidenceFactors(
        evidence_quality=0.3,
        evidence_quantity=0.2,
        evidence_recency=0.4,
        provider_inheritance=0.5,
        ai_certainty=0.5
    )

    score = scorer.calculate_confidence(factors)

    assert score < 0.5  # Should be low
    assert scorer.get_confidence_level(score) in [ConfidenceLevel.LOW, ConfidenceLevel.VERY_LOW]


def test_calculate_confidence_medium(scorer):
    """Test medium confidence scenario"""
    factors = ConfidenceFactors(
        evidence_quality=0.7,
        evidence_quantity=0.6,
        evidence_recency=0.7,
        provider_inheritance=0.5,
        ai_certainty=0.7
    )

    score = scorer.calculate_confidence(factors)

    assert 0.55 <= score <= 0.75  # Should be medium
    assert scorer.get_confidence_level(score) in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]


def test_confidence_breakdown(scorer):
    """Test detailed confidence breakdown"""
    factors = ConfidenceFactors(
        evidence_quality=0.8,
        evidence_quantity=0.7,
        evidence_recency=0.9,
        provider_inheritance=0.6,
        ai_certainty=0.75
    )

    breakdown = scorer.calculate_with_breakdown(factors)

    assert isinstance(breakdown, ConfidenceBreakdown)
    assert 0 <= breakdown.overall_score <= 1
    assert isinstance(breakdown.confidence_level, ConfidenceLevel)
    assert len(breakdown.weighted_scores) == 5
    assert isinstance(breakdown.explanation, str)
    assert isinstance(breakdown.recommendations, list)


def test_confidence_levels():
    """Test confidence level categorization"""
    scorer = ConfidenceScorer()

    assert scorer.get_confidence_level(0.95) == ConfidenceLevel.VERY_HIGH
    assert scorer.get_confidence_level(0.80) == ConfidenceLevel.HIGH
    assert scorer.get_confidence_level(0.65) == ConfidenceLevel.MEDIUM
    assert scorer.get_confidence_level(0.50) == ConfidenceLevel.LOW
    assert scorer.get_confidence_level(0.30) == ConfidenceLevel.VERY_LOW


def test_assess_evidence_quality(scorer):
    """Test evidence quality assessment"""
    # High quality
    quality = scorer.assess_evidence_quality(
        evidence_count=5,
        avg_relevance_score=0.9,
        has_direct_evidence=True,
        evidence_types_count=3
    )
    assert quality >= 0.9

    # Low quality
    quality = scorer.assess_evidence_quality(
        evidence_count=1,
        avg_relevance_score=0.5,
        has_direct_evidence=False,
        evidence_types_count=1
    )
    assert quality < 0.5

    # No evidence
    quality = scorer.assess_evidence_quality(
        evidence_count=0,
        avg_relevance_score=0.0,
        has_direct_evidence=False,
        evidence_types_count=0
    )
    assert quality == 0.0


def test_assess_evidence_quantity(scorer):
    """Test evidence quantity assessment"""
    # Ideal quantity (2+ per objective)
    quantity = scorer.assess_evidence_quantity(
        evidence_count=6,
        objectives_count=3
    )
    assert quantity == 1.0

    # Sufficient quantity (1 per objective)
    quantity = scorer.assess_evidence_quantity(
        evidence_count=3,
        objectives_count=3
    )
    assert 0.7 <= quantity < 1.0

    # Insufficient quantity
    quantity = scorer.assess_evidence_quantity(
        evidence_count=1,
        objectives_count=3
    )
    assert quantity < 0.7

    # No evidence
    quantity = scorer.assess_evidence_quantity(
        evidence_count=0,
        objectives_count=3
    )
    assert quantity == 0.0


def test_assess_evidence_recency(scorer):
    """Test evidence recency assessment"""
    # Very recent (< 30 days)
    recency = scorer.assess_evidence_recency(
        most_recent_date=datetime.utcnow() - timedelta(days=15)
    )
    assert recency == 1.0

    # Recent (30-90 days)
    recency = scorer.assess_evidence_recency(
        most_recent_date=datetime.utcnow() - timedelta(days=60)
    )
    assert 0.85 <= recency <= 0.95

    # Somewhat old (90-180 days)
    recency = scorer.assess_evidence_recency(
        most_recent_date=datetime.utcnow() - timedelta(days=120)
    )
    assert 0.6 <= recency <= 0.85

    # Old (> 180 days)
    recency = scorer.assess_evidence_recency(
        most_recent_date=datetime.utcnow() - timedelta(days=365)
    )
    assert recency < 0.5

    # Unknown date
    recency = scorer.assess_evidence_recency(None)
    assert recency == 0.5


def test_assess_provider_inheritance(scorer):
    """Test provider inheritance assessment"""
    # Fully inherited with docs
    inheritance = scorer.assess_provider_inheritance(
        responsibility="Inherited",
        has_documentation=True
    )
    assert inheritance == 1.0

    # Fully inherited without docs
    inheritance = scorer.assess_provider_inheritance(
        responsibility="Inherited",
        has_documentation=False
    )
    assert inheritance == 1.0  # Still fully inherited

    # Shared responsibility with docs
    inheritance = scorer.assess_provider_inheritance(
        responsibility="Shared",
        has_documentation=True
    )
    assert 0.7 <= inheritance <= 0.8

    # Customer responsibility
    inheritance = scorer.assess_provider_inheritance(
        responsibility="Customer",
        has_documentation=False
    )
    assert inheritance == 0.5

    # No provider
    inheritance = scorer.assess_provider_inheritance(
        responsibility=None,
        has_documentation=False
    )
    assert inheritance == 0.5


def test_factor_bounds_validation(scorer):
    """Test that out-of-bounds factors are clamped"""
    factors = ConfidenceFactors(
        evidence_quality=1.5,  # Out of bounds
        evidence_quantity=-0.1,  # Out of bounds
        evidence_recency=0.8,
        provider_inheritance=0.7,
        ai_certainty=0.6
    )

    score = scorer.calculate_confidence(factors)

    # Should not raise error and should return valid score
    assert 0 <= score <= 1


def test_custom_weights():
    """Test custom weight initialization"""
    # Custom weights
    scorer = ConfidenceScorer(
        evidence_quality_weight=0.5,
        evidence_quantity_weight=0.3,
        evidence_recency_weight=0.1,
        provider_inheritance_weight=0.05,
        ai_certainty_weight=0.05
    )

    factors = ConfidenceFactors(
        evidence_quality=1.0,
        evidence_quantity=0.0,
        evidence_recency=0.0,
        provider_inheritance=0.0,
        ai_certainty=0.0
    )

    score = scorer.calculate_confidence(factors)

    # With 50% weight on quality and quality=1.0, score should be 0.5
    assert abs(score - 0.5) < 0.01


def test_invalid_weights():
    """Test that invalid weights raise error"""
    with pytest.raises(ValueError):
        ConfidenceScorer(
            evidence_quality_weight=0.5,
            evidence_quantity_weight=0.3,
            # Weights don't sum to 1.0
        )


def test_convenience_function():
    """Test the convenience calculate_confidence function"""
    score = calculate_confidence(
        evidence_quality=0.8,
        evidence_quantity=0.7,
        evidence_recency=0.9,
        provider_inheritance=0.6,
        ai_certainty=0.75
    )

    assert 0 <= score <= 1
    assert isinstance(score, float)


def test_recommendations_generation(scorer):
    """Test that appropriate recommendations are generated"""
    # Low quality scenario
    factors = ConfidenceFactors(
        evidence_quality=0.4,
        evidence_quantity=0.3,
        evidence_recency=0.4,
        provider_inheritance=0.4,
        ai_certainty=0.5
    )

    breakdown = scorer.calculate_with_breakdown(factors)

    # Should have multiple recommendations
    assert len(breakdown.recommendations) >= 3

    # Should mention specific issues
    recommendations_text = " ".join(breakdown.recommendations).lower()
    assert any(word in recommendations_text for word in ['evidence', 'quality', 'quantity', 'recency'])


def test_explanation_generation(scorer):
    """Test that explanation is generated"""
    factors = ConfidenceFactors(
        evidence_quality=0.9,
        evidence_quantity=0.4,  # Weakness
        evidence_recency=0.9,
        provider_inheritance=0.9,
        ai_certainty=0.85
    )

    breakdown = scorer.calculate_with_breakdown(factors)

    # Explanation should contain key information
    assert "Confidence Level" in breakdown.explanation
    assert "Factor Breakdown" in breakdown.explanation

    # Should identify the weakness
    assert "concern" in breakdown.explanation.lower() or "quantity" in breakdown.explanation.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
