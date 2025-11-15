"""
Provider Inheritance Service
Manages cloud provider control inheritance (M365, Azure, AWS)
"""

import json
import logging
from typing import List, Dict, Optional, Any
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import asyncpg

logger = logging.getLogger(__name__)


class ResponsibilityType(str, Enum):
    """Control responsibility types"""
    INHERITED = "Inherited"
    SHARED = "Shared"
    CUSTOMER = "Customer"


@dataclass
class ControlInheritance:
    """Provider control inheritance details"""
    control_id: str
    control_title: str
    responsibility: ResponsibilityType
    provider_responsibility: Optional[str]
    customer_responsibility: Optional[str]
    inherited_controls: List[str]
    implementation_guidance: str
    evidence_artifacts: List[str]
    authoritative_source: Optional[str]


@dataclass
class ProviderOffering:
    """Cloud provider offering"""
    provider_name: str
    provider_type: str
    description: str
    certification_level: str
    documentation_url: str
    control_mappings: List[ControlInheritance]
    total_controls_mapped: int
    inherited_count: int
    shared_count: int
    customer_count: int
    coverage_percentage: float


class ProviderInheritanceService:
    """
    Service for managing provider inheritance mappings

    Handles:
    - Loading provider mappings from JSON files
    - Storing mappings in database
    - Retrieving inheritance info for controls
    - Calculating coverage statistics
    """

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        mappings_dir: Optional[str] = None
    ):
        """
        Initialize provider inheritance service

        Args:
            db_pool: Database connection pool
            mappings_dir: Directory containing provider mapping JSON files
        """
        self.db_pool = db_pool

        if mappings_dir is None:
            # Default to data/provider_mappings
            self.mappings_dir = Path(__file__).parent.parent.parent / "data" / "provider_mappings"
        else:
            self.mappings_dir = Path(mappings_dir)

        logger.info(f"Initialized ProviderInheritanceService with mappings dir: {self.mappings_dir}")

    def load_mapping_file(self, file_path: str) -> Dict[str, Any]:
        """
        Load provider mapping from JSON file

        Args:
            file_path: Path to JSON file

        Returns:
            Mapping dictionary
        """
        with open(file_path, 'r') as f:
            return json.load(f)

    def parse_mapping(self, mapping_data: Dict[str, Any]) -> ProviderOffering:
        """
        Parse mapping data into ProviderOffering

        Args:
            mapping_data: Raw mapping dictionary

        Returns:
            ProviderOffering object
        """
        control_mappings = []

        for control_map in mapping_data.get('control_mappings', []):
            # Determine provider and customer responsibility text
            if 'microsoft_responsibility' in control_map:
                provider_resp = control_map['microsoft_responsibility']
                customer_resp = control_map['customer_responsibility']
            elif 'azure_responsibility' in control_map:
                provider_resp = control_map['azure_responsibility']
                customer_resp = control_map['customer_responsibility']
            elif 'aws_responsibility' in control_map:
                provider_resp = control_map['aws_responsibility']
                customer_resp = control_map['customer_responsibility']
            else:
                provider_resp = None
                customer_resp = None

            control_mappings.append(ControlInheritance(
                control_id=control_map['control_id'],
                control_title=control_map['control_title'],
                responsibility=ResponsibilityType(control_map['responsibility']),
                provider_responsibility=provider_resp,
                customer_responsibility=customer_resp,
                inherited_controls=control_map.get('inherited_controls', []),
                implementation_guidance=control_map.get('implementation_guidance', ''),
                evidence_artifacts=control_map.get('evidence_artifacts', []),
                authoritative_source=control_map.get('authoritative_source')
            ))

        summary = mapping_data.get('summary', {})

        return ProviderOffering(
            provider_name=mapping_data['provider_name'],
            provider_type=mapping_data['provider_type'],
            description=mapping_data['description'],
            certification_level=mapping_data['certification_level'],
            documentation_url=mapping_data['documentation_url'],
            control_mappings=control_mappings,
            total_controls_mapped=summary.get('total_controls_mapped', len(control_mappings)),
            inherited_count=summary.get('inherited_count', 0),
            shared_count=summary.get('shared_count', 0),
            customer_count=summary.get('customer_count', 0),
            coverage_percentage=summary.get('coverage_percentage', 0.0)
        )

    async def import_provider_offering(
        self,
        provider_offering: ProviderOffering,
        organization_id: Optional[str] = None
    ) -> str:
        """
        Import provider offering into database

        Args:
            provider_offering: Provider offering to import
            organization_id: Organization ID (optional, for org-specific offerings)

        Returns:
            Provider offering ID
        """
        async with self.db_pool.acquire() as conn:
            # Insert provider offering
            offering_id = await conn.fetchval("""
                INSERT INTO provider_offerings (
                    provider_name,
                    offering_name,
                    authorization_type,
                    documentation_url
                )
                VALUES ($1, $2, $3, $4)
                RETURNING id
            """, provider_offering.provider_name,
                provider_offering.provider_type,
                provider_offering.certification_level,
                provider_offering.documentation_url)

            # Insert control mappings
            for control_map in provider_offering.control_mappings:
                await conn.execute("""
                    INSERT INTO provider_control_inheritance (
                        provider_offering_id,
                        control_id,
                        responsibility,
                        provider_narrative,
                        customer_narrative,
                        evidence_url,
                        implementation_guidance
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    ON CONFLICT DO NOTHING
                """, offering_id,
                    control_map.control_id,
                    control_map.responsibility.value,
                    control_map.provider_responsibility,
                    control_map.customer_responsibility,
                    control_map.authoritative_source,
                    control_map.implementation_guidance)

            logger.info(f"Imported provider offering: {provider_offering.provider_name} ({offering_id})")
            logger.info(f"  Total controls: {provider_offering.total_controls_mapped}")
            logger.info(f"  Inherited: {provider_offering.inherited_count}")
            logger.info(f"  Shared: {provider_offering.shared_count}")
            logger.info(f"  Customer: {provider_offering.customer_count}")

            return str(offering_id)

    async def import_all_mappings(self) -> Dict[str, str]:
        """
        Import all provider mappings from mappings directory

        Returns:
            Dictionary mapping provider name to offering ID
        """
        imported = {}

        # Find all JSON files in mappings directory
        if not self.mappings_dir.exists():
            logger.warning(f"Mappings directory not found: {self.mappings_dir}")
            return imported

        for json_file in self.mappings_dir.glob("*.json"):
            logger.info(f"Importing mapping from {json_file.name}")

            try:
                mapping_data = self.load_mapping_file(str(json_file))
                provider_offering = self.parse_mapping(mapping_data)
                offering_id = await self.import_provider_offering(provider_offering)

                imported[provider_offering.provider_name] = offering_id

            except Exception as e:
                logger.error(f"Error importing {json_file.name}: {e}", exc_info=True)

        logger.info(f"Imported {len(imported)} provider offerings")
        return imported

    async def get_control_inheritance(
        self,
        control_id: str,
        provider_name: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get provider inheritance for a control

        Args:
            control_id: Control ID
            provider_name: Filter by provider name (optional)

        Returns:
            List of inheritance mappings
        """
        async with self.db_pool.acquire() as conn:
            query = """
                SELECT
                    po.provider_name,
                    po.offering_name,
                    po.authorization_type,
                    pci.responsibility,
                    pci.provider_narrative,
                    pci.customer_narrative,
                    pci.implementation_guidance,
                    pci.evidence_url
                FROM provider_control_inheritance pci
                JOIN provider_offerings po ON pci.provider_offering_id = po.id
                WHERE pci.control_id = $1
            """

            params = [control_id]

            if provider_name:
                query += " AND po.provider_name = $2"
                params.append(provider_name)

            rows = await conn.fetch(query, *params)

            return [dict(row) for row in rows]

    async def get_inherited_controls(
        self,
        provider_name: str
    ) -> List[str]:
        """
        Get list of controls fully inherited from provider

        Args:
            provider_name: Provider name

        Returns:
            List of control IDs that are fully inherited
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT DISTINCT pci.control_id
                FROM provider_control_inheritance pci
                JOIN provider_offerings po ON pci.provider_offering_id = po.id
                WHERE po.provider_name = $1
                  AND pci.responsibility = 'Inherited'
            """, provider_name)

            return [row['control_id'] for row in rows]

    async def get_provider_coverage(
        self,
        provider_name: str
    ) -> Dict[str, Any]:
        """
        Get coverage statistics for a provider

        Args:
            provider_name: Provider name

        Returns:
            Coverage statistics
        """
        async with self.db_pool.acquire() as conn:
            # Get total CMMC L2 controls
            total_controls = await conn.fetchval("""
                SELECT COUNT(*) FROM controls WHERE cmmc_level = 2
            """)

            # Get mapped controls count
            mapped_controls = await conn.fetchval("""
                SELECT COUNT(DISTINCT pci.control_id)
                FROM provider_control_inheritance pci
                JOIN provider_offerings po ON pci.provider_offering_id = po.id
                WHERE po.provider_name = $1
            """, provider_name)

            # Get by responsibility type
            by_responsibility = await conn.fetch("""
                SELECT pci.responsibility, COUNT(*) as count
                FROM provider_control_inheritance pci
                JOIN provider_offerings po ON pci.provider_offering_id = po.id
                WHERE po.provider_name = $1
                GROUP BY pci.responsibility
            """, provider_name)

            responsibility_counts = {row['responsibility']: row['count'] for row in by_responsibility}

            return {
                'provider_name': provider_name,
                'total_cmmc_controls': total_controls,
                'mapped_controls': mapped_controls,
                'coverage_percentage': (mapped_controls / total_controls * 100) if total_controls > 0 else 0,
                'inherited_count': responsibility_counts.get('Inherited', 0),
                'shared_count': responsibility_counts.get('Shared', 0),
                'customer_count': responsibility_counts.get('Customer', 0)
            }

    async def get_all_providers(self) -> List[Dict[str, Any]]:
        """
        Get list of all providers in database

        Returns:
            List of provider offerings
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id,
                    provider_name,
                    offering_name,
                    authorization_type,
                    documentation_url,
                    created_at
                FROM provider_offerings
                ORDER BY provider_name
            """)

            providers = []

            for row in rows:
                # Get coverage for this provider
                coverage = await self.get_provider_coverage(row['provider_name'])

                providers.append({
                    'id': str(row['id']),
                    'provider_name': row['provider_name'],
                    'offering_name': row['offering_name'],
                    'authorization_type': row['authorization_type'],
                    'documentation_url': row['documentation_url'],
                    'created_at': row['created_at'],
                    **coverage
                })

            return providers

    async def calculate_assessment_savings(
        self,
        assessment_id: str,
        provider_names: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate time/effort savings from provider inheritance

        Args:
            assessment_id: Assessment ID
            provider_names: List of provider names being used

        Returns:
            Savings statistics
        """
        async with self.db_pool.acquire() as conn:
            # Get total controls in assessment
            total_controls = await conn.fetchval("""
                SELECT COUNT(DISTINCT cf.control_id)
                FROM control_findings cf
                WHERE cf.assessment_id = $1
            """, assessment_id)

            if total_controls == 0:
                # No findings yet, use all CMMC L2 controls
                total_controls = 110

            # Count inherited and shared controls
            inherited_controls = set()
            shared_controls = set()

            for provider_name in provider_names:
                inherited = await self.get_inherited_controls(provider_name)
                inherited_controls.update(inherited)

                # Get shared controls
                rows = await conn.fetch("""
                    SELECT DISTINCT pci.control_id
                    FROM provider_control_inheritance pci
                    JOIN provider_offerings po ON pci.provider_offering_id = po.id
                    WHERE po.provider_name = $1
                      AND pci.responsibility = 'Shared'
                """, provider_name)

                shared_controls.update([row['control_id'] for row in rows])

            # Calculate savings
            # Inherited: 100% time saved
            # Shared: 50% time saved (split responsibility)
            inherited_count = len(inherited_controls)
            shared_only = len(shared_controls - inherited_controls)

            # Assume each control takes 2 hours to assess manually
            hours_per_control = 2

            time_saved_inherited = inherited_count * hours_per_control
            time_saved_shared = shared_only * hours_per_control * 0.5

            total_time_saved = time_saved_inherited + time_saved_shared
            total_time_without_provider = total_controls * hours_per_control

            percentage_saved = (total_time_saved / total_time_without_provider * 100) if total_time_without_provider > 0 else 0

            return {
                'total_controls': total_controls,
                'inherited_controls': inherited_count,
                'shared_controls': shared_only,
                'customer_controls': total_controls - inherited_count - shared_only,
                'hours_saved': round(total_time_saved, 1),
                'percentage_saved': round(percentage_saved, 1),
                'estimated_cost_savings': round(total_time_saved * 200, 2)  # Assume $200/hour assessor rate
            }


# Helper functions
async def import_providers_from_files(db_pool: asyncpg.Pool, mappings_dir: Optional[str] = None) -> Dict[str, str]:
    """
    Convenience function to import all provider mappings

    Args:
        db_pool: Database pool
        mappings_dir: Directory with JSON files (optional)

    Returns:
        Dictionary of imported providers
    """
    service = ProviderInheritanceService(db_pool, mappings_dir)
    return await service.import_all_mappings()
