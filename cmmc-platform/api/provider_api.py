"""
Provider Inheritance API
RESTful endpoints for managing cloud provider control inheritance
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from pydantic import BaseModel, Field
import asyncpg

from services.provider_inheritance import (
    ProviderInheritanceService,
    ProviderOffering,
    ControlInheritance,
    ResponsibilityType
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


# ===========================
# Request/Response Models
# ===========================

class ImportMappingsRequest(BaseModel):
    """Request to import provider mappings"""
    mappings_dir: Optional[str] = Field(
        None,
        description="Custom directory path for JSON mappings (optional)"
    )


class ImportMappingsResponse(BaseModel):
    """Response from import operation"""
    success: bool
    providers_imported: Dict[str, str] = Field(
        description="Map of provider name to offering ID"
    )
    total_imported: int
    message: str


class ProviderSummary(BaseModel):
    """Provider summary with coverage stats"""
    id: str
    provider_name: str
    offering_name: str
    authorization_type: str
    documentation_url: str
    total_cmmc_controls: int
    mapped_controls: int
    coverage_percentage: float
    inherited_count: int
    shared_count: int
    customer_count: int


class ControlInheritanceDetail(BaseModel):
    """Detailed control inheritance info"""
    provider_name: str
    offering_name: str
    authorization_type: str
    responsibility: str
    provider_narrative: Optional[str]
    customer_narrative: Optional[str]
    implementation_guidance: Optional[str]
    evidence_url: Optional[str]


class ProviderControlsResponse(BaseModel):
    """Response with provider controls"""
    provider_name: str
    total_controls: int
    inherited_controls: List[str]
    shared_controls: List[str]
    customer_controls: List[str]
    coverage_percentage: float


class AssessmentSavingsRequest(BaseModel):
    """Request to calculate assessment savings"""
    provider_names: List[str] = Field(
        description="List of provider names being used (e.g., ['Microsoft 365 GCC High', 'Azure Government'])"
    )


class AssessmentSavingsResponse(BaseModel):
    """Assessment savings calculation"""
    assessment_id: str
    providers_used: List[str]
    total_controls: int
    inherited_controls: int
    shared_controls: int
    customer_controls: int
    hours_saved: float
    percentage_saved: float
    estimated_cost_savings: float = Field(
        description="Estimated cost savings in USD at $200/hour assessor rate"
    )
    message: str


# ===========================
# Dependency Injection
# ===========================

async def get_db_pool() -> asyncpg.Pool:
    """Get database connection pool (to be injected)"""
    # This will be provided by main app dependency injection
    # For now, placeholder
    raise NotImplementedError("Database pool dependency not configured")


async def get_provider_service(
    db_pool: asyncpg.Pool = Depends(get_db_pool)
) -> ProviderInheritanceService:
    """Get provider inheritance service instance"""
    return ProviderInheritanceService(db_pool)


# ===========================
# API Endpoints
# ===========================

@router.post("/import", response_model=ImportMappingsResponse)
async def import_provider_mappings(
    request: ImportMappingsRequest = Body(default=ImportMappingsRequest()),
    service: ProviderInheritanceService = Depends(get_provider_service)
):
    """
    Import all provider mappings from JSON files

    Loads provider offerings from data/provider_mappings directory
    and imports them into the database.

    **Returns:**
    - Map of provider names to offering IDs
    - Total number of providers imported

    **Example:**
    ```json
    POST /api/v1/providers/import
    {
      "mappings_dir": null  // Uses default directory
    }
    ```
    """
    try:
        logger.info(f"Importing provider mappings from: {request.mappings_dir or 'default directory'}")

        # Override mappings directory if provided
        if request.mappings_dir:
            service.mappings_dir = request.mappings_dir

        imported = await service.import_all_mappings()

        return ImportMappingsResponse(
            success=True,
            providers_imported=imported,
            total_imported=len(imported),
            message=f"Successfully imported {len(imported)} provider offerings"
        )

    except Exception as e:
        logger.error(f"Error importing provider mappings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")


@router.get("", response_model=List[ProviderSummary])
async def list_providers(
    service: ProviderInheritanceService = Depends(get_provider_service)
):
    """
    List all cloud providers with coverage statistics

    Returns summary information for all imported provider offerings
    including control coverage and responsibility breakdown.

    **Returns:**
    - List of providers with coverage stats

    **Example:**
    ```json
    GET /api/v1/providers
    [
      {
        "id": "uuid",
        "provider_name": "Microsoft 365 GCC High",
        "offering_name": "SaaS",
        "authorization_type": "FedRAMP High",
        "documentation_url": "https://...",
        "total_cmmc_controls": 110,
        "mapped_controls": 21,
        "coverage_percentage": 19.1,
        "inherited_count": 7,
        "shared_count": 12,
        "customer_count": 2
      }
    ]
    ```
    """
    try:
        providers = await service.get_all_providers()

        return [
            ProviderSummary(
                id=p['id'],
                provider_name=p['provider_name'],
                offering_name=p['offering_name'],
                authorization_type=p['authorization_type'],
                documentation_url=p['documentation_url'],
                total_cmmc_controls=p['total_cmmc_controls'],
                mapped_controls=p['mapped_controls'],
                coverage_percentage=p['coverage_percentage'],
                inherited_count=p['inherited_count'],
                shared_count=p['shared_count'],
                customer_count=p['customer_count']
            )
            for p in providers
        ]

    except Exception as e:
        logger.error(f"Error listing providers: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list providers: {str(e)}")


@router.get("/{provider_name}/controls", response_model=ProviderControlsResponse)
async def get_provider_controls(
    provider_name: str,
    service: ProviderInheritanceService = Depends(get_provider_service)
):
    """
    Get all controls for a specific provider

    Returns breakdown of controls by responsibility type
    (Inherited, Shared, Customer) for the specified provider.

    **Parameters:**
    - provider_name: Provider name (e.g., "Microsoft 365 GCC High")

    **Returns:**
    - Lists of control IDs by responsibility type

    **Example:**
    ```json
    GET /api/v1/providers/Microsoft%20365%20GCC%20High/controls
    {
      "provider_name": "Microsoft 365 GCC High",
      "total_controls": 21,
      "inherited_controls": ["IA.L2-3.5.7", ...],
      "shared_controls": ["AC.L2-3.1.1", ...],
      "customer_controls": ["CM.L2-3.4.7", ...],
      "coverage_percentage": 19.1
    }
    ```
    """
    try:
        # Get coverage stats
        coverage = await service.get_provider_coverage(provider_name)

        if coverage['mapped_controls'] == 0:
            raise HTTPException(
                status_code=404,
                detail=f"Provider not found: {provider_name}"
            )

        # Get inherited controls
        inherited = await service.get_inherited_controls(provider_name)

        # Get all controls for this provider to separate by type
        async with service.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT pci.control_id, pci.responsibility
                FROM provider_control_inheritance pci
                JOIN provider_offerings po ON pci.provider_offering_id = po.id
                WHERE po.provider_name = $1
                ORDER BY pci.control_id
            """, provider_name)

        shared_controls = [
            row['control_id'] for row in rows
            if row['responsibility'] == 'Shared'
        ]

        customer_controls = [
            row['control_id'] for row in rows
            if row['responsibility'] == 'Customer'
        ]

        return ProviderControlsResponse(
            provider_name=provider_name,
            total_controls=len(rows),
            inherited_controls=inherited,
            shared_controls=shared_controls,
            customer_controls=customer_controls,
            coverage_percentage=coverage['coverage_percentage']
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting provider controls: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get provider controls: {str(e)}")


@router.get("/control/{control_id}", response_model=List[ControlInheritanceDetail])
async def get_control_inheritance(
    control_id: str,
    provider_name: Optional[str] = Query(None, description="Filter by provider name"),
    service: ProviderInheritanceService = Depends(get_provider_service)
):
    """
    Get provider inheritance information for a specific control

    Returns inheritance details from all providers (or a specific provider)
    that have mapped this control.

    **Parameters:**
    - control_id: CMMC control ID (e.g., "AC.L2-3.1.1")
    - provider_name: Optional filter by provider name

    **Returns:**
    - List of inheritance mappings for the control

    **Example:**
    ```json
    GET /api/v1/providers/control/AC.L2-3.1.1
    [
      {
        "provider_name": "Microsoft 365 GCC High",
        "offering_name": "SaaS",
        "authorization_type": "FedRAMP High",
        "responsibility": "Shared",
        "provider_narrative": "Microsoft provides Azure AD for identity and access management...",
        "customer_narrative": "Customer configures conditional access policies...",
        "implementation_guidance": "Configure Azure AD conditional access...",
        "evidence_url": "https://..."
      }
    ]
    ```
    """
    try:
        inheritance_data = await service.get_control_inheritance(
            control_id=control_id,
            provider_name=provider_name
        )

        if not inheritance_data:
            raise HTTPException(
                status_code=404,
                detail=f"No inheritance data found for control: {control_id}"
            )

        return [
            ControlInheritanceDetail(
                provider_name=item['provider_name'],
                offering_name=item['offering_name'],
                authorization_type=item['authorization_type'],
                responsibility=item['responsibility'],
                provider_narrative=item['provider_narrative'],
                customer_narrative=item['customer_narrative'],
                implementation_guidance=item['implementation_guidance'],
                evidence_url=item['evidence_url']
            )
            for item in inheritance_data
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting control inheritance: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get control inheritance: {str(e)}")


@router.post("/assessment/{assessment_id}/savings", response_model=AssessmentSavingsResponse)
async def calculate_assessment_savings(
    assessment_id: str,
    request: AssessmentSavingsRequest,
    service: ProviderInheritanceService = Depends(get_provider_service)
):
    """
    Calculate time and cost savings from provider inheritance

    Analyzes the assessment's controls and calculates how much time/effort
    can be saved by leveraging cloud provider inheritance and shared responsibility.

    **Calculation:**
    - Inherited controls: 100% time saved (2 hours per control)
    - Shared controls: 50% time saved (1 hour per control)
    - Customer controls: 0% time saved (full 2 hours per control)

    **Parameters:**
    - assessment_id: UUID of the assessment
    - provider_names: List of cloud providers being used

    **Returns:**
    - Detailed savings breakdown

    **Example:**
    ```json
    POST /api/v1/providers/assessment/uuid/savings
    {
      "provider_names": ["Microsoft 365 GCC High", "Azure Government"]
    }

    Response:
    {
      "assessment_id": "uuid",
      "providers_used": ["Microsoft 365 GCC High", "Azure Government"],
      "total_controls": 110,
      "inherited_controls": 8,
      "shared_controls": 25,
      "customer_controls": 77,
      "hours_saved": 28.5,
      "percentage_saved": 12.9,
      "estimated_cost_savings": 5700.00,
      "message": "Using 2 cloud providers can save 28.5 hours (12.9%) on assessment"
    }
    ```
    """
    try:
        if not request.provider_names:
            raise HTTPException(
                status_code=400,
                detail="At least one provider name must be specified"
            )

        savings = await service.calculate_assessment_savings(
            assessment_id=assessment_id,
            provider_names=request.provider_names
        )

        return AssessmentSavingsResponse(
            assessment_id=assessment_id,
            providers_used=request.provider_names,
            total_controls=savings['total_controls'],
            inherited_controls=savings['inherited_controls'],
            shared_controls=savings['shared_controls'],
            customer_controls=savings['customer_controls'],
            hours_saved=savings['hours_saved'],
            percentage_saved=savings['percentage_saved'],
            estimated_cost_savings=savings['estimated_cost_savings'],
            message=f"Using {len(request.provider_names)} cloud provider(s) can save "
                   f"{savings['hours_saved']} hours ({savings['percentage_saved']}%) on assessment"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating assessment savings: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to calculate savings: {str(e)}")


@router.get("/coverage/summary", response_model=Dict[str, Any])
async def get_coverage_summary(
    service: ProviderInheritanceService = Depends(get_provider_service)
):
    """
    Get overall provider coverage summary across all providers

    Returns aggregated statistics showing combined coverage from all
    imported cloud providers.

    **Returns:**
    - Total providers
    - Unique controls covered
    - Coverage breakdown by responsibility type

    **Example:**
    ```json
    GET /api/v1/providers/coverage/summary
    {
      "total_providers": 3,
      "total_cmmc_controls": 110,
      "unique_controls_covered": 42,
      "overall_coverage_percentage": 38.2,
      "by_provider": {
        "Microsoft 365 GCC High": {
          "mapped_controls": 21,
          "inherited": 7,
          "shared": 12,
          "customer": 2
        },
        ...
      },
      "aggregate_counts": {
        "total_inherited": 9,
        "total_shared": 35,
        "total_customer": 5
      }
    }
    ```
    """
    try:
        async with service.db_pool.acquire() as conn:
            # Total providers
            total_providers = await conn.fetchval(
                "SELECT COUNT(*) FROM provider_offerings"
            )

            # Total CMMC L2 controls
            total_controls = await conn.fetchval(
                "SELECT COUNT(*) FROM controls WHERE cmmc_level = 2"
            )

            # Unique controls covered across all providers
            unique_covered = await conn.fetchval("""
                SELECT COUNT(DISTINCT control_id)
                FROM provider_control_inheritance
            """)

            # Get breakdown by provider
            providers = await service.get_all_providers()

            by_provider = {}
            total_inherited = 0
            total_shared = 0
            total_customer = 0

            for provider in providers:
                by_provider[provider['provider_name']] = {
                    'mapped_controls': provider['mapped_controls'],
                    'inherited': provider['inherited_count'],
                    'shared': provider['shared_count'],
                    'customer': provider['customer_count']
                }

                total_inherited += provider['inherited_count']
                total_shared += provider['shared_count']
                total_customer += provider['customer_count']

            return {
                'total_providers': total_providers,
                'total_cmmc_controls': total_controls,
                'unique_controls_covered': unique_covered,
                'overall_coverage_percentage': round((unique_covered / total_controls * 100) if total_controls > 0 else 0, 1),
                'by_provider': by_provider,
                'aggregate_counts': {
                    'total_inherited': total_inherited,
                    'total_shared': total_shared,
                    'total_customer': total_customer
                }
            }

    except Exception as e:
        logger.error(f"Error getting coverage summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get coverage summary: {str(e)}")
