"""
AI Cost Forecasting API
Endpoints for predicting AI costs based on assessment size
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
import asyncpg

from middleware.auth_middleware import get_auth_context, AuthContext
from services.ai_forecast_service import AICostForecaster

router = APIRouter()

# Dependency to get database pool (will be overridden by app.py)
async def get_db_pool() -> asyncpg.Pool:
    raise NotImplementedError("Database pool dependency not configured")


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class ForecastAssessmentRequest(BaseModel):
    """Request for assessment cost forecast"""
    control_count: int = Field(..., ge=1, le=1000, description="Number of controls to assess")
    document_count: Optional[int] = Field(default=None, ge=0, description="Number of evidence documents")
    page_count: Optional[int] = Field(default=None, ge=0, description="Total pages in documentation")
    cmmc_level: int = Field(default=2, ge=1, le=3, description="CMMC level (1, 2, or 3)")
    expected_rag_queries: Optional[int] = Field(default=None, ge=0, description="Expected RAG searches")
    use_historical_data: bool = Field(default=True, description="Use organization's historical data")


class PlannedAssessment(BaseModel):
    """Planned assessment for monthly forecast"""
    control_count: int = Field(..., ge=1, le=1000)
    document_count: Optional[int] = Field(default=None, ge=0)
    page_count: Optional[int] = Field(default=None, ge=0)
    cmmc_level: int = Field(default=2, ge=1, le=3)


class ForecastMonthlyRequest(BaseModel):
    """Request for monthly cost forecast"""
    planned_assessments: List[PlannedAssessment] = Field(..., min_items=1, max_items=50)
    historical_months: int = Field(default=3, ge=1, le=12, description="Months of history to analyze")


class CostBreakdown(BaseModel):
    """Cost breakdown for a component"""
    cost: float
    percentage: float
    description: str
    unit_cost: Optional[float] = None
    units: Optional[int] = None


class SimilarAssessment(BaseModel):
    """Similar historical assessment"""
    id: str
    name: str
    cmmc_level: int
    control_count: int
    total_cost: float
    completed_at: Optional[str]
    similarity: str


class ForecastResponse(BaseModel):
    """Assessment cost forecast response"""
    estimated_cost: float
    min_cost: float
    max_cost: float
    confidence_level: str
    confidence_interval: str
    data_source: str
    breakdown: dict
    parameters: dict
    similar_assessments: List[SimilarAssessment]
    recommendations: List[str]
    forecasted_at: str


class MonthlyForecastResponse(BaseModel):
    """Monthly cost forecast response"""
    planned_monthly_cost: float
    historical_avg_monthly: float
    variance_percentage: float
    trend: str
    planned_assessment_count: int
    avg_historical_assessments: float
    planned_assessments: List[dict]
    historical_data: List[dict]
    recommendations: List[str]


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/forecast/assessment", response_model=ForecastResponse)
async def forecast_assessment_cost(
    request: ForecastAssessmentRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Forecast AI costs for a new assessment

    Predicts costs based on assessment characteristics:
    - Number of controls to assess
    - Number of evidence documents
    - Total pages of documentation
    - CMMC level (affects complexity)
    - Expected RAG queries

    Uses organization's historical data when available, otherwise
    uses industry averages. Returns estimated cost with confidence
    interval, detailed breakdown, and optimization recommendations.

    Example:
    ```
    POST /api/v1/ai/forecast/assessment
    {
        "control_count": 110,
        "document_count": 500,
        "page_count": 2500,
        "cmmc_level": 2
    }
    ```

    Response includes:
    - Estimated total cost
    - Min/max cost range (confidence interval)
    - Breakdown by operation type
    - Similar past assessments for comparison
    - Cost optimization recommendations
    """
    try:
        forecaster = AICostForecaster(db_pool=pool)

        forecast = await forecaster.forecast_assessment_cost(
            organization_id=auth_context.organization_id,
            control_count=request.control_count,
            document_count=request.document_count,
            page_count=request.page_count,
            cmmc_level=request.cmmc_level,
            expected_rag_queries=request.expected_rag_queries,
            use_historical_data=request.use_historical_data
        )

        return ForecastResponse(**forecast)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to forecast cost: {str(e)}")


@router.post("/forecast/monthly", response_model=MonthlyForecastResponse)
async def forecast_monthly_costs(
    request: ForecastMonthlyRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Forecast monthly AI costs based on planned assessments

    Predicts monthly spending based on:
    - List of planned assessments with their characteristics
    - Historical monthly spending patterns
    - Trends and variance analysis

    Helps with:
    - Monthly budget planning
    - Capacity planning
    - Identifying cost spikes
    - Optimizing assessment scheduling

    Example:
    ```
    POST /api/v1/ai/forecast/monthly
    {
        "planned_assessments": [
            {
                "control_count": 110,
                "document_count": 500,
                "cmmc_level": 2
            },
            {
                "control_count": 75,
                "document_count": 300,
                "cmmc_level": 1
            }
        ],
        "historical_months": 3
    }
    ```

    Response includes:
    - Total planned monthly cost
    - Historical average for comparison
    - Variance percentage and trend
    - Individual forecast for each assessment
    - Recommendations for optimization
    """
    try:
        forecaster = AICostForecaster(db_pool=pool)

        # Convert Pydantic models to dicts
        planned_assessments_dict = [
            assessment.dict() for assessment in request.planned_assessments
        ]

        forecast = await forecaster.forecast_monthly_costs(
            organization_id=auth_context.organization_id,
            planned_assessments=planned_assessments_dict,
            historical_months=request.historical_months
        )

        return MonthlyForecastResponse(**forecast)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to forecast monthly costs: {str(e)}")


@router.get("/forecast/quick")
async def quick_cost_estimate(
    control_count: int = Query(..., ge=1, le=1000, description="Number of controls"),
    cmmc_level: int = Query(default=2, ge=1, le=3, description="CMMC level"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Quick cost estimate (simplified forecast)

    Fast endpoint for getting a rough cost estimate with minimal parameters.
    Uses default values for documents and pages based on typical assessments.

    Useful for:
    - Quick quotes
    - Initial budget discussions
    - Assessment planning

    Example:
    ```
    GET /api/v1/ai/forecast/quick?control_count=110&cmmc_level=2
    ```

    Returns simplified response with:
    - Estimated cost
    - Cost range (min-max)
    - Confidence level
    """
    try:
        forecaster = AICostForecaster(db_pool=pool)

        # Use typical defaults for a CMMC assessment
        typical_docs_per_control = 5
        typical_pages_per_doc = 5

        document_count = control_count * typical_docs_per_control
        page_count = document_count * typical_pages_per_doc

        forecast = await forecaster.forecast_assessment_cost(
            organization_id=auth_context.organization_id,
            control_count=control_count,
            document_count=document_count,
            page_count=page_count,
            cmmc_level=cmmc_level,
            use_historical_data=True
        )

        return {
            "estimated_cost": forecast['estimated_cost'],
            "cost_range": {
                "min": forecast['min_cost'],
                "max": forecast['max_cost']
            },
            "confidence_level": forecast['confidence_level'],
            "assumptions": {
                "documents_per_control": typical_docs_per_control,
                "pages_per_document": typical_pages_per_doc,
                "total_documents": document_count,
                "total_pages": page_count
            },
            "note": "This is a quick estimate. Use the detailed forecast endpoint for more accurate predictions."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate quick estimate: {str(e)}")


@router.get("/forecast/historical-averages")
async def get_historical_averages(
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Get organization's historical cost averages

    Returns average costs based on past assessments:
    - Average cost per control
    - Average cost per document
    - Average total assessment cost
    - Standard deviation
    - Number of assessments analyzed

    Useful for:
    - Understanding typical spending patterns
    - Benchmarking new estimates
    - Budget planning

    Example:
    ```
    GET /api/v1/ai/forecast/historical-averages
    ```
    """
    try:
        forecaster = AICostForecaster(db_pool=pool)

        historical = await forecaster._get_historical_costs(auth_context.organization_id)

        if not historical or historical['assessment_count'] == 0:
            return {
                "has_data": False,
                "message": "No historical data available. Complete at least one assessment with AI features to see averages.",
                "default_estimates": forecaster.default_costs
            }

        return {
            "has_data": True,
            "assessment_count": historical['assessment_count'],
            "averages": {
                "total_cost_per_assessment": round(historical['avg_total_cost'], 2),
                "cost_per_control": round(historical['avg_cost_per_control'], 4),
                "cost_per_document": round(historical['avg_cost_per_document'], 4),
                "analysis_per_control": round(historical['avg_analysis_per_control'], 4)
            },
            "variability": {
                "standard_deviation": round(historical['stddev_cost'], 2),
                "note": "Higher standard deviation indicates more variable costs across assessments"
            },
            "data_quality": "high" if historical['assessment_count'] >= 5 else "medium" if historical['assessment_count'] >= 3 else "low",
            "recommendation": "Continue using AI features to improve forecast accuracy" if historical['assessment_count'] < 5 else "Sufficient data for accurate forecasting"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get historical averages: {str(e)}")


@router.get("/forecast/comparison/{cmmc_level}")
async def compare_cmmc_levels(
    cmmc_level: int,
    control_count: int = Query(..., ge=1, le=1000),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Compare costs across CMMC levels

    Shows how costs differ between CMMC levels for the same control count.
    Useful for understanding the cost impact of pursuing higher certification levels.

    Example:
    ```
    GET /api/v1/ai/forecast/comparison/2?control_count=110
    ```

    Returns comparison of Level 1, 2, and 3 costs.
    """
    try:
        forecaster = AICostForecaster(db_pool=pool)

        comparisons = {}

        for level in [1, 2, 3]:
            forecast = await forecaster.forecast_assessment_cost(
                organization_id=auth_context.organization_id,
                control_count=control_count,
                cmmc_level=level,
                use_historical_data=False  # Use defaults for fair comparison
            )

            comparisons[f"level_{level}"] = {
                "estimated_cost": forecast['estimated_cost'],
                "cost_range": f"${forecast['min_cost']:.2f} - ${forecast['max_cost']:.2f}",
                "multiplier": forecaster.level_multipliers[level],
                "complexity": "Low" if level == 1 else "Medium" if level == 2 else "High"
            }

        # Calculate relative differences
        base_cost = comparisons['level_2']['estimated_cost']

        return {
            "control_count": control_count,
            "base_level": 2,
            "comparisons": comparisons,
            "relative_costs": {
                "level_1_vs_2": f"{((comparisons['level_1']['estimated_cost'] / base_cost - 1) * 100):.1f}% {'lower' if comparisons['level_1']['estimated_cost'] < base_cost else 'higher'}",
                "level_3_vs_2": f"{((comparisons['level_3']['estimated_cost'] / base_cost - 1) * 100):.1f}% {'lower' if comparisons['level_3']['estimated_cost'] < base_cost else 'higher'}"
            },
            "note": "Costs based on default estimates. Actual costs may vary based on evidence complexity."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare levels: {str(e)}")
