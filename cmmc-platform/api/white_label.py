"""
White-Labeling System
=====================
White-label customization for MSPs and enterprise customers.

Features:
- Custom branding (logo, colors, fonts)
- Custom domain mapping
- Email template customization
- Custom terminology
- Portal customization
- Report branding
- Removes platform branding
"""

from typing import Dict, List, Any, Optional
from pydantic import BaseModel, HttpUrl
import asyncpg
import logging
import json

logger = logging.getLogger(__name__)


class BrandingColors(BaseModel):
    """Brand color scheme."""
    primary: str = "#1a73e8"  # Primary brand color
    secondary: str = "#34a853"  # Secondary color
    accent: str = "#fbbc04"  # Accent color
    background: str = "#ffffff"  # Background color
    text: str = "#202124"  # Text color
    text_secondary: str = "#5f6368"  # Secondary text color


class BrandingConfig(BaseModel):
    """Complete branding configuration."""
    company_name: str
    logo_url: Optional[HttpUrl] = None
    favicon_url: Optional[HttpUrl] = None
    colors: BrandingColors
    custom_domain: Optional[str] = None
    support_email: Optional[str] = None
    support_url: Optional[HttpUrl] = None


class EmailTemplateConfig(BaseModel):
    """Email template customization."""
    header_logo_url: Optional[HttpUrl] = None
    footer_text: Optional[str] = None
    signature: Optional[str] = None
    from_name: Optional[str] = None
    from_email: Optional[str] = None


class TerminologyCustomization(BaseModel):
    """Custom terminology for white-label deployments."""
    assessment_singular: str = "Assessment"
    assessment_plural: str = "Assessments"
    control_singular: str = "Control"
    control_plural: str = "Controls"
    evidence_singular: str = "Evidence"
    evidence_plural: str = "Evidence"
    organization_singular: str = "Organization"
    organization_plural: str = "Organizations"


class WhiteLabelService:
    """White-label customization service."""

    def __init__(self, conn: asyncpg.Connection):
        """Initialize white-label service."""
        self.conn = conn

    async def get_branding(
        self,
        organization_id: str
    ) -> Dict[str, Any]:
        """
        Get white-label branding configuration.

        Args:
            organization_id: Organization UUID

        Returns:
            Branding configuration
        """
        branding = await self.conn.fetchrow(
            """
            SELECT
                company_name, logo_url, favicon_url, colors,
                custom_domain, support_email, support_url,
                enabled, created_at, updated_at
            FROM white_label_branding
            WHERE organization_id = $1
            """,
            organization_id
        )

        if not branding:
            # Return default branding
            return {
                "enabled": False,
                "company_name": "CMMC Compliance Platform",
                "colors": BrandingColors().dict(),
                "custom_domain": None
            }

        return {
            "enabled": branding['enabled'],
            "company_name": branding['company_name'],
            "logo_url": branding['logo_url'],
            "favicon_url": branding['favicon_url'],
            "colors": branding['colors'] if branding['colors'] else BrandingColors().dict(),
            "custom_domain": branding['custom_domain'],
            "support_email": branding['support_email'],
            "support_url": branding['support_url'],
            "created_at": branding['created_at'].isoformat(),
            "updated_at": branding['updated_at'].isoformat()
        }

    async def update_branding(
        self,
        organization_id: str,
        config: BrandingConfig,
        updated_by: str
    ) -> Dict[str, Any]:
        """
        Update white-label branding.

        Args:
            organization_id: Organization UUID
            config: Branding configuration
            updated_by: User making the update

        Returns:
            Updated branding configuration
        """
        # Check if organization has white-label access
        subscription = await self.conn.fetchrow(
            """
            SELECT plan FROM subscriptions
            WHERE organization_id = $1
            AND status = 'active'
            ORDER BY created_at DESC
            LIMIT 1
            """,
            organization_id
        )

        if not subscription or subscription['plan'] not in ['professional', 'enterprise']:
            raise ValueError("White-labeling requires Professional or Enterprise plan")

        # Upsert branding configuration
        await self.conn.execute(
            """
            INSERT INTO white_label_branding
            (organization_id, company_name, logo_url, favicon_url, colors,
             custom_domain, support_email, support_url, enabled)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, TRUE)
            ON CONFLICT (organization_id)
            DO UPDATE SET
                company_name = $2,
                logo_url = $3,
                favicon_url = $4,
                colors = $5,
                custom_domain = $6,
                support_email = $7,
                support_url = $8,
                enabled = TRUE,
                updated_at = NOW()
            """,
            organization_id,
            config.company_name,
            str(config.logo_url) if config.logo_url else None,
            str(config.favicon_url) if config.favicon_url else None,
            json.dumps(config.colors.dict()),
            config.custom_domain,
            config.support_email,
            str(config.support_url) if config.support_url else None
        )

        # Log the update
        await self.conn.execute(
            """
            INSERT INTO audit_log (table_name, operation, record_id, changed_by, changed_data)
            VALUES ('white_label_branding', 'UPDATE', $1, $2, $3)
            """,
            organization_id,
            updated_by,
            json.dumps(config.dict())
        )

        logger.info(f"White-label branding updated for organization {organization_id}")

        return await self.get_branding(organization_id)

    async def get_email_templates(
        self,
        organization_id: str
    ) -> Dict[str, Any]:
        """Get custom email templates."""
        templates = await self.conn.fetchrow(
            """
            SELECT header_logo_url, footer_text, signature, from_name, from_email
            FROM email_templates
            WHERE organization_id = $1
            """,
            organization_id
        )

        if not templates:
            return EmailTemplateConfig().dict()

        return {
            "header_logo_url": templates['header_logo_url'],
            "footer_text": templates['footer_text'],
            "signature": templates['signature'],
            "from_name": templates['from_name'],
            "from_email": templates['from_email']
        }

    async def update_email_templates(
        self,
        organization_id: str,
        config: EmailTemplateConfig,
        updated_by: str
    ) -> Dict[str, Any]:
        """Update email template customization."""
        await self.conn.execute(
            """
            INSERT INTO email_templates
            (organization_id, header_logo_url, footer_text, signature, from_name, from_email)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (organization_id)
            DO UPDATE SET
                header_logo_url = $2,
                footer_text = $3,
                signature = $4,
                from_name = $5,
                from_email = $6,
                updated_at = NOW()
            """,
            organization_id,
            str(config.header_logo_url) if config.header_logo_url else None,
            config.footer_text,
            config.signature,
            config.from_name,
            config.from_email
        )

        logger.info(f"Email templates updated for organization {organization_id}")

        return await self.get_email_templates(organization_id)

    async def get_terminology(
        self,
        organization_id: str
    ) -> Dict[str, Any]:
        """Get custom terminology."""
        terminology = await self.conn.fetchrow(
            """
            SELECT terminology FROM white_label_branding
            WHERE organization_id = $1
            """,
            organization_id
        )

        if not terminology or not terminology['terminology']:
            return TerminologyCustomization().dict()

        return terminology['terminology']

    async def update_terminology(
        self,
        organization_id: str,
        config: TerminologyCustomization,
        updated_by: str
    ) -> Dict[str, Any]:
        """Update custom terminology."""
        await self.conn.execute(
            """
            UPDATE white_label_branding
            SET terminology = $1, updated_at = NOW()
            WHERE organization_id = $2
            """,
            json.dumps(config.dict()),
            organization_id
        )

        logger.info(f"Terminology updated for organization {organization_id}")

        return config.dict()

    async def generate_custom_report(
        self,
        organization_id: str,
        assessment_id: str,
        report_type: str
    ) -> bytes:
        """
        Generate branded report with white-label customization.

        Args:
            organization_id: Organization UUID
            assessment_id: Assessment UUID
            report_type: Type of report

        Returns:
            Generated report bytes
        """
        # Get branding
        branding = await self.get_branding(organization_id)

        # Generate report with custom branding
        # This would integrate with report generation library
        # For now, return placeholder

        logger.info(f"Generating branded {report_type} report for {organization_id}")

        # In production:
        # - Apply custom logo to header
        # - Use brand colors throughout
        # - Apply custom footer
        # - Remove platform branding

        return b"Custom branded report content"

    async def get_custom_css(
        self,
        organization_id: str
    ) -> str:
        """
        Generate custom CSS for white-label portal.

        Args:
            organization_id: Organization UUID

        Returns:
            Custom CSS string
        """
        branding = await self.get_branding(organization_id)

        if not branding['enabled']:
            return ""

        colors = branding['colors']

        css = f"""
        /* White-Label Custom Branding */
        :root {{
            --primary-color: {colors['primary']};
            --secondary-color: {colors['secondary']};
            --accent-color: {colors['accent']};
            --background-color: {colors['background']};
            --text-color: {colors['text']};
            --text-secondary-color: {colors['text_secondary']};
        }}

        .navbar-brand img {{
            content: url('{branding.get('logo_url', '')}');
            max-height: 40px;
        }}

        .btn-primary {{
            background-color: var(--primary-color);
            border-color: var(--primary-color);
        }}

        .btn-primary:hover {{
            background-color: color-mix(in srgb, var(--primary-color) 90%, black);
            border-color: color-mix(in srgb, var(--primary-color) 90%, black);
        }}

        .text-primary {{
            color: var(--primary-color) !important;
        }}

        .bg-primary {{
            background-color: var(--primary-color) !important;
        }}

        a {{
            color: var(--primary-color);
        }}

        a:hover {{
            color: color-mix(in srgb, var(--primary-color) 80%, black);
        }}
        """

        return css
