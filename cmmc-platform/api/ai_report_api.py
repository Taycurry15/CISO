"""
AI Cost Report API
Endpoints for generating and downloading cost reports
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
from enum import Enum
import asyncpg

from middleware.auth_middleware import get_auth_context, AuthContext
from services.ai_report_service import AIReportService, ReportFormat

router = APIRouter()

# Dependency to get database pool (will be overridden by app.py)
async def get_db_pool() -> asyncpg.Pool:
    raise NotImplementedError("Database pool dependency not configured")


# ============================================================================
# ENUMS
# ============================================================================

class ReportFormatEnum(str, Enum):
    """Report format options"""
    PDF = "pdf"
    EXCEL = "excel"


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/reports/assessment/{assessment_id}")
async def generate_assessment_report(
    assessment_id: str,
    format: ReportFormatEnum = Query(default=ReportFormatEnum.PDF, description="Report format (pdf or excel)"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Generate and download AI cost report for a specific assessment

    Returns a downloadable file containing:
    - Assessment information and summary
    - Total cost, operations, and tokens
    - Breakdown by operation type and model
    - Daily spending trend
    - Top controls by cost
    - Response time statistics

    Formats:
    - PDF: Professional formatted report with tables
    - Excel: Spreadsheet with multiple sheets and data
    """
    try:
        report_service = AIReportService(db_pool=pool)

        # Generate report
        report_buffer = await report_service.generate_assessment_report(
            assessment_id=assessment_id,
            organization_id=auth_context.organization_id,
            format=ReportFormat(format.value)
        )

        # Prepare response
        if format == ReportFormatEnum.PDF:
            media_type = "application/pdf"
            filename = f"assessment_cost_report_{assessment_id}_{datetime.utcnow().strftime('%Y%m%d')}.pdf"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"assessment_cost_report_{assessment_id}_{datetime.utcnow().strftime('%Y%m%d')}.xlsx"

        return StreamingResponse(
            report_buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/reports/organization")
async def generate_organization_report(
    format: ReportFormatEnum = Query(default=ReportFormatEnum.PDF, description="Report format (pdf or excel)"),
    start_date: Optional[datetime] = Query(default=None, description="Start date (defaults to 30 days ago)"),
    end_date: Optional[datetime] = Query(default=None, description="End date (defaults to now)"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Generate and download organization-wide AI cost report

    Returns a downloadable file containing:
    - Organization summary for the period
    - Total cost, operations, and tokens
    - Breakdown by operation type and model
    - Daily spending trend
    - Top assessments by cost
    - Model usage statistics

    Query Parameters:
    - format: pdf or excel (default: pdf)
    - start_date: Report start date (default: 30 days ago)
    - end_date: Report end date (default: now)

    Formats:
    - PDF: Professional formatted report with charts
    - Excel: Spreadsheet with multiple sheets, charts, and pivot tables
    """
    try:
        report_service = AIReportService(db_pool=pool)

        # Generate report
        report_buffer = await report_service.generate_organization_report(
            organization_id=auth_context.organization_id,
            start_date=start_date,
            end_date=end_date,
            format=ReportFormat(format.value)
        )

        # Prepare response
        period_str = f"{(start_date or datetime.utcnow() - timedelta(days=30)).strftime('%Y%m%d')}_{(end_date or datetime.utcnow()).strftime('%Y%m%d')}"

        if format == ReportFormatEnum.PDF:
            media_type = "application/pdf"
            filename = f"organization_cost_report_{period_str}.pdf"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"organization_cost_report_{period_str}.xlsx"

        return StreamingResponse(
            report_buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/reports/monthly")
async def generate_monthly_report(
    year: int = Query(..., description="Year (e.g., 2025)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)"),
    format: ReportFormatEnum = Query(default=ReportFormatEnum.PDF, description="Report format (pdf or excel)"),
    auth_context: AuthContext = Depends(get_auth_context),
    pool: asyncpg.Pool = Depends(get_db_pool)
):
    """
    Generate monthly AI cost report

    Convenience endpoint for generating reports for a specific month.
    Automatically calculates start and end dates for the month.

    Query Parameters:
    - year: Year (e.g., 2025)
    - month: Month (1-12)
    - format: pdf or excel (default: pdf)

    Returns the same data as the organization report but for the specified month.
    """
    try:
        # Calculate month boundaries
        from calendar import monthrange

        start_date = datetime(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)

        report_service = AIReportService(db_pool=pool)

        # Generate report
        report_buffer = await report_service.generate_organization_report(
            organization_id=auth_context.organization_id,
            start_date=start_date,
            end_date=end_date,
            format=ReportFormat(format.value)
        )

        # Prepare response
        month_str = f"{year}{month:02d}"

        if format == ReportFormatEnum.PDF:
            media_type = "application/pdf"
            filename = f"monthly_cost_report_{month_str}.pdf"
        else:
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"monthly_cost_report_{month_str}.xlsx"

        return StreamingResponse(
            report_buffer,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")


@router.get("/reports/formats")
async def get_available_formats():
    """
    Get list of available report formats

    Returns information about supported report formats and their
    availability based on installed dependencies.
    """
    try:
        from services.ai_report_service import REPORTLAB_AVAILABLE, OPENPYXL_AVAILABLE

        return {
            "formats": [
                {
                    "name": "PDF",
                    "value": "pdf",
                    "available": REPORTLAB_AVAILABLE,
                    "description": "Professional formatted PDF report with tables and charts",
                    "mime_type": "application/pdf",
                    "file_extension": ".pdf"
                },
                {
                    "name": "Excel",
                    "value": "excel",
                    "available": OPENPYXL_AVAILABLE,
                    "description": "Excel spreadsheet with multiple sheets and data analysis",
                    "mime_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    "file_extension": ".xlsx"
                }
            ],
            "all_available": REPORTLAB_AVAILABLE and OPENPYXL_AVAILABLE,
            "message": "Install reportlab and openpyxl to enable all formats" if not (REPORTLAB_AVAILABLE and OPENPYXL_AVAILABLE) else "All formats available"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check formats: {str(e)}")
