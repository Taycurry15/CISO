"""
Dashboard Analytics API
RESTful endpoints for real-time assessment analytics and insights
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import asyncpg

from services.dashboard_service import DashboardService
from services.pdf_summary_service import PDFSummaryService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dashboard", tags=["dashboard"])


# ===========================
# Response Models
# ===========================

class AssessmentOverviewResponse(BaseModel):
    """Assessment overview response"""
    total_assessments: int
    active_assessments: int
    completed_assessments: int
    draft_assessments: int
    in_progress_assessments: int
    avg_completion_percentage: float
    avg_confidence_score: float
    total_evidence_collected: int


class ControlComplianceResponse(BaseModel):
    """Control compliance response"""
    total_controls: int
    controls_met: int
    controls_not_met: int
    controls_partial: int
    controls_na: int
    compliance_percentage: float
    by_domain: dict
    high_risk_controls: list


class ProgressMetricsResponse(BaseModel):
    """Progress metrics response"""
    date: str
    controls_analyzed: int
    evidence_uploaded: int
    completion_percentage: float


class SavingsResponse(BaseModel):
    """Savings calculation response"""
    manual_hours: float
    automated_hours: float
    hours_saved: float
    cost_savings: float
    provider_inheritance_hours: float
    ai_analysis_hours: float
    report_generation_hours: float
    hourly_rate: float


class DashboardSummaryResponse(BaseModel):
    """Complete dashboard summary"""
    overview: AssessmentOverviewResponse
    compliance: ControlComplianceResponse
    evidence_stats: dict
    recent_activity: list


# ===========================
# Dependency Injection
# ===========================

async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool (to be injected)"""
    raise NotImplementedError("Database pool dependency not configured")


async def get_dashboard_service(
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> DashboardService:
    """Get dashboard service instance"""
    return DashboardService(db_pool)


# ===========================
# Dashboard Endpoints
# ===========================

@router.get("/overview", response_model=AssessmentOverviewResponse)
async def get_assessment_overview(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    date_from: Optional[datetime] = Query(None, description="Filter from date"),
    date_to: Optional[datetime] = Query(None, description="Filter to date"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get high-level assessment overview

    Returns summary statistics across all assessments including:
    - Total, active, completed assessment counts
    - Average completion percentage
    - Average confidence score
    - Total evidence collected

    **Example:**
    ```
    GET /api/v1/dashboard/overview?organization_id=uuid
    {
      "total_assessments": 15,
      "active_assessments": 8,
      "completed_assessments": 7,
      "draft_assessments": 2,
      "in_progress_assessments": 5,
      "avg_completion_percentage": 68.5,
      "avg_confidence_score": 0.79,
      "total_evidence_collected": 1247
    }
    ```
    """
    try:
        overview = await service.get_assessment_overview(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to
        )

        return AssessmentOverviewResponse(**overview.__dict__)

    except Exception as e:
        logger.error(f"Error getting overview: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get overview: {str(e)}")


@router.get("/compliance", response_model=ControlComplianceResponse)
async def get_control_compliance(
    assessment_id: Optional[str] = Query(None, description="Filter by assessment"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get control compliance metrics

    Returns detailed compliance statistics including:
    - Total controls and status breakdown
    - Compliance percentage
    - Compliance by domain (AC, IA, SC, etc.)
    - High-risk controls (Not Met in critical domains)

    **Example:**
    ```
    GET /api/v1/dashboard/compliance?assessment_id=uuid
    {
      "total_controls": 110,
      "controls_met": 85,
      "controls_not_met": 10,
      "controls_partial": 12,
      "controls_na": 3,
      "compliance_percentage": 77.3,
      "by_domain": {
        "AC": {
          "total": 22,
          "met": 18,
          "not_met": 2,
          "partial": 2,
          "compliance_pct": 81.8
        },
        "IA": {
          "total": 11,
          "met": 8,
          "not_met": 2,
          "partial": 1,
          "compliance_pct": 72.7
        }
      },
      "high_risk_controls": [
        {
          "control_id": "AC.L2-3.1.5",
          "title": "Separation of Duties",
          "domain": "AC",
          "status": "Not Met",
          "confidence_score": 0.82
        }
      ]
    }
    ```
    """
    try:
        compliance = await service.get_control_compliance(
            assessment_id=assessment_id,
            organization_id=organization_id
        )

        return ControlComplianceResponse(**compliance.__dict__)

    except Exception as e:
        logger.error(f"Error getting compliance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get compliance: {str(e)}")


@router.get("/progress/{assessment_id}", response_model=list[ProgressMetricsResponse])
async def get_progress_over_time(
    assessment_id: str,
    days: int = Query(30, ge=1, le=90, description="Number of days"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get assessment progress over time

    Returns daily progress metrics showing:
    - Controls analyzed per day
    - Evidence uploaded per day
    - Completion percentage trend

    **Example:**
    ```
    GET /api/v1/dashboard/progress/uuid?days=7
    [
      {
        "date": "2024-01-15",
        "controls_analyzed": 45,
        "evidence_uploaded": 68,
        "completion_percentage": 40.9
      },
      {
        "date": "2024-01-16",
        "controls_analyzed": 62,
        "evidence_uploaded": 95,
        "completion_percentage": 56.4
      }
    ]
    ```
    """
    try:
        progress = await service.get_progress_over_time(
            assessment_id=assessment_id,
            days=days
        )

        return [ProgressMetricsResponse(**p.__dict__) for p in progress]

    except Exception as e:
        logger.error(f"Error getting progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get progress: {str(e)}")


@router.get("/evidence", response_model=dict)
async def get_evidence_statistics(
    assessment_id: Optional[str] = Query(None, description="Filter by assessment"),
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get evidence statistics

    Returns comprehensive evidence metrics including:
    - Total evidence count and storage usage
    - Evidence by type (Document, Screenshot, etc.)
    - Evidence by assessment method (Examine, Interview, Test)
    - Controls with evidence

    **Example:**
    ```
    GET /api/v1/dashboard/evidence?assessment_id=uuid
    {
      "total_evidence": 142,
      "evidence_types": 6,
      "total_size_bytes": 52428800,
      "avg_size_bytes": 369200,
      "controls_with_evidence": 95,
      "by_type": {
        "Document": 45,
        "Screenshot": 38,
        "Configuration": 25,
        "Log": 20,
        "Policy": 10,
        "Diagram": 4
      },
      "by_method": {
        "Examine": 85,
        "Interview": 32,
        "Test": 25
      }
    }
    ```
    """
    try:
        stats = await service.get_evidence_statistics(
            assessment_id=assessment_id,
            organization_id=organization_id
        )

        return stats

    except Exception as e:
        logger.error(f"Error getting evidence statistics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get evidence statistics: {str(e)}")


@router.get("/savings/{assessment_id}", response_model=SavingsResponse)
async def calculate_savings(
    assessment_id: str,
    hourly_rate: float = Query(200.0, ge=50, le=500, description="Assessor hourly rate"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Calculate time and cost savings from automation

    Shows how much time and money is saved by using the platform vs. manual assessment.

    Savings breakdown:
    - Provider inheritance (inherited/shared controls)
    - AI analysis (vs. manual control review)
    - Report generation (SSP/POA&M automation)

    **Example:**
    ```
    GET /api/v1/dashboard/savings/uuid?hourly_rate=200
    {
      "manual_hours": 220.0,
      "automated_hours": 8.5,
      "hours_saved": 211.5,
      "cost_savings": 42300.00,
      "provider_inheritance_hours": 83.6,
      "ai_analysis_hours": 178.2,
      "report_generation_hours": 48.0,
      "hourly_rate": 200.0
    }
    ```
    """
    try:
        savings = await service.calculate_savings(
            assessment_id=assessment_id,
            hourly_rate=hourly_rate
        )

        return SavingsResponse(
            **savings.__dict__,
            hourly_rate=hourly_rate
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error calculating savings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate savings: {str(e)}")


@router.get("/activity", response_model=list[dict])
async def get_recent_activity(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get recent activity feed

    Returns chronological list of recent activities including:
    - Evidence uploads
    - Control analyses
    - Status changes
    - Report generations

    **Example:**
    ```
    GET /api/v1/dashboard/activity?limit=5
    [
      {
        "activity_type": "evidence_upload",
        "timestamp": "2024-01-15T14:30:00Z",
        "description": "Access Control Policy",
        "assessment_id": "uuid",
        "actor": "Jane Doe"
      },
      {
        "activity_type": "evidence_upload",
        "timestamp": "2024-01-15T14:25:00Z",
        "description": "MFA Configuration Screenshot",
        "assessment_id": "uuid",
        "actor": "John Smith"
      }
    ]
    ```
    """
    try:
        activity = await service.get_recent_activity(
            organization_id=organization_id,
            limit=limit
        )

        return activity

    except Exception as e:
        logger.error(f"Error getting activity: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get activity: {str(e)}")


@router.get("/summary", response_model=DashboardSummaryResponse)
async def get_dashboard_summary(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    assessment_id: Optional[str] = Query(None, description="Filter by assessment"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get complete dashboard summary

    Returns all dashboard metrics in a single call:
    - Assessment overview
    - Control compliance
    - Evidence statistics
    - Recent activity

    Perfect for populating a dashboard UI with one API call.

    **Example:**
    ```
    GET /api/v1/dashboard/summary?organization_id=uuid
    {
      "overview": {
        "total_assessments": 15,
        "active_assessments": 8,
        "avg_completion_percentage": 68.5,
        ...
      },
      "compliance": {
        "total_controls": 110,
        "controls_met": 85,
        "compliance_percentage": 77.3,
        "by_domain": {...},
        ...
      },
      "evidence_stats": {
        "total_evidence": 1247,
        "by_type": {...},
        ...
      },
      "recent_activity": [...]
    }
    ```
    """
    try:
        # Get all dashboard data
        overview = await service.get_assessment_overview(
            organization_id=organization_id
        )

        compliance = await service.get_control_compliance(
            assessment_id=assessment_id,
            organization_id=organization_id
        )

        evidence_stats = await service.get_evidence_statistics(
            assessment_id=assessment_id,
            organization_id=organization_id
        )

        recent_activity = await service.get_recent_activity(
            organization_id=organization_id,
            limit=10
        )

        return DashboardSummaryResponse(
            overview=AssessmentOverviewResponse(**overview.__dict__),
            compliance=ControlComplianceResponse(**compliance.__dict__),
            evidence_stats=evidence_stats,
            recent_activity=recent_activity
        )

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get dashboard summary: {str(e)}")


@router.get("/heatmap/{assessment_id}", response_model=dict)
async def get_compliance_heatmap(
    assessment_id: str,
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Get compliance heatmap data

    Returns data formatted for heatmap visualization showing
    compliance status by domain and control.

    **Example:**
    ```
    GET /api/v1/dashboard/heatmap/uuid
    {
      "domains": ["AC", "AU", "CM", "IA", "IR", "MA", "MP", "PE", "PS", "RE", "RM", "SA", "SC", "SI", "SR"],
      "data": [
        {
          "domain": "AC",
          "total": 22,
          "met": 18,
          "not_met": 2,
          "partial": 2,
          "compliance_pct": 81.8,
          "color": "#4CAF50"
        }
      ]
    }
    ```
    """
    try:
        compliance = await service.get_control_compliance(
            assessment_id=assessment_id
        )

        # Format for heatmap
        heatmap_data = []
        for domain, stats in compliance.by_domain.items():
            # Assign color based on compliance percentage
            compliance_pct = stats['compliance_pct']
            if compliance_pct >= 90:
                color = "#4CAF50"  # Green
            elif compliance_pct >= 75:
                color = "#8BC34A"  # Light green
            elif compliance_pct >= 50:
                color = "#FFC107"  # Yellow/Amber
            elif compliance_pct >= 25:
                color = "#FF9800"  # Orange
            else:
                color = "#F44336"  # Red

            heatmap_data.append({
                'domain': domain,
                'total': stats['total'],
                'met': stats['met'],
                'not_met': stats['not_met'],
                'partial': stats['partial'],
                'compliance_pct': stats['compliance_pct'],
                'color': color
            })

        # Sort by domain name
        heatmap_data.sort(key=lambda x: x['domain'])

        return {
            'domains': [d['domain'] for d in heatmap_data],
            'data': heatmap_data
        }

    except Exception as e:
        logger.error(f"Error getting heatmap: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get heatmap: {str(e)}")


@router.get("/export/pdf", response_class=StreamingResponse)
async def export_dashboard_pdf(
    organization_id: Optional[str] = Query(None, description="Filter by organization"),
    assessment_id: Optional[str] = Query(None, description="Filter by assessment"),
    organization_name: str = Query("Organization", description="Organization name"),
    assessment_name: Optional[str] = Query(None, description="Assessment name"),
    include_savings: bool = Query(True, description="Include savings calculation"),
    service: DashboardService = Depends(get_dashboard_service)
):
    """
    Export dashboard summary to PDF

    Generates an executive summary PDF report with:
    - Assessment overview
    - Control compliance metrics and charts
    - Evidence statistics
    - Cost/time savings (optional)

    Perfect for executive presentations and stakeholder updates.

    **Example:**
    ```
    GET /api/v1/dashboard/export/pdf?assessment_id=uuid&organization_name=Defense%20Contractor%20Inc&include_savings=true

    Response:
    Content-Type: application/pdf
    Content-Disposition: attachment; filename="Dashboard_Summary_20240115.pdf"

    [PDF file download]
    ```
    """
    try:
        # Get dashboard data
        overview = await service.get_assessment_overview(
            organization_id=organization_id
        )

        compliance = await service.get_control_compliance(
            assessment_id=assessment_id,
            organization_id=organization_id
        )

        evidence_stats = await service.get_evidence_statistics(
            assessment_id=assessment_id,
            organization_id=organization_id
        )

        # Get savings if requested and assessment_id provided
        savings = None
        if include_savings and assessment_id:
            try:
                savings_calc = await service.calculate_savings(
                    assessment_id=assessment_id
                )
                savings = savings_calc.__dict__
            except Exception as e:
                logger.warning(f"Could not calculate savings: {e}")

        # Generate PDF
        pdf_service = PDFSummaryService()
        pdf_bytes = pdf_service.generate_summary_pdf(
            overview=overview.__dict__,
            compliance=compliance.__dict__,
            evidence_stats=evidence_stats,
            savings=savings,
            organization_name=organization_name,
            assessment_name=assessment_name
        )

        # Return as download
        file_name = f"Dashboard_Summary_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={file_name}"
            }
        )

    except Exception as e:
        logger.error(f"Error exporting PDF: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to export PDF: {str(e)}")
