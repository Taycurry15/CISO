"""
PDF Summary Service

Generates executive summary PDFs from dashboard analytics.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image
from reportlab.platypus import KeepTogether
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart

logger = logging.getLogger(__name__)


class PDFSummaryService:
    """
    PDF Summary Service

    Generates executive summary PDFs with charts and metrics
    """

    def __init__(self):
        """Initialize PDF summary service"""
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1976D2'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

        # Heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1976D2'),
            spaceAfter=12,
            spaceBefore=12
        ))

        # Metric value style
        self.styles.add(ParagraphStyle(
            name='MetricValue',
            parent=self.styles['Normal'],
            fontSize=36,
            textColor=colors.HexColor('#4CAF50'),
            alignment=TA_CENTER,
            spaceAfter=6
        ))

        # Metric label style
        self.styles.add(ParagraphStyle(
            name='MetricLabel',
            parent=self.styles['Normal'],
            fontSize=12,
            textColor=colors.grey,
            alignment=TA_CENTER
        ))

    def generate_summary_pdf(
        self,
        overview: Dict[str, Any],
        compliance: Dict[str, Any],
        evidence_stats: Dict[str, Any],
        savings: Optional[Dict[str, Any]] = None,
        organization_name: str = "Organization",
        assessment_name: Optional[str] = None
    ) -> BytesIO:
        """
        Generate executive summary PDF

        Args:
            overview: Assessment overview metrics
            compliance: Control compliance metrics
            evidence_stats: Evidence statistics
            savings: Optional savings calculation
            organization_name: Organization name
            assessment_name: Optional assessment name

        Returns:
            BytesIO: PDF file
        """
        logger.info(f"Generating PDF summary for {organization_name}")

        # Create PDF buffer
        buffer = BytesIO()

        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18
        )

        # Build content
        story = []

        # Title page
        story.extend(self._create_title_page(organization_name, assessment_name))

        # Overview section
        story.append(PageBreak())
        story.extend(self._create_overview_section(overview))

        # Compliance section
        story.append(PageBreak())
        story.extend(self._create_compliance_section(compliance))

        # Evidence section
        story.append(Spacer(1, 0.5*inch))
        story.extend(self._create_evidence_section(evidence_stats))

        # Savings section (if provided)
        if savings:
            story.append(PageBreak())
            story.extend(self._create_savings_section(savings))

        # Build PDF
        doc.build(story)

        buffer.seek(0)
        logger.info("PDF summary generated successfully")

        return buffer

    def _create_title_page(
        self,
        organization_name: str,
        assessment_name: Optional[str]
    ) -> list:
        """Create title page"""
        elements = []

        # Spacer
        elements.append(Spacer(1, 2*inch))

        # Title
        title = Paragraph(
            "CMMC Assessment<br/>Executive Summary",
            self.styles['CustomTitle']
        )
        elements.append(title)

        elements.append(Spacer(1, 0.5*inch))

        # Organization
        org = Paragraph(
            organization_name,
            self.styles['Heading1']
        )
        elements.append(org)

        elements.append(Spacer(1, 0.25*inch))

        # Assessment name (if provided)
        if assessment_name:
            assessment = Paragraph(
                assessment_name,
                self.styles['Heading2']
            )
            elements.append(assessment)
            elements.append(Spacer(1, 0.25*inch))

        # Date
        date = Paragraph(
            f"Generated: {datetime.utcnow().strftime('%B %d, %Y')}",
            self.styles['Normal']
        )
        elements.append(date)

        return elements

    def _create_overview_section(self, overview: Dict[str, Any]) -> list:
        """Create overview section with key metrics"""
        elements = []

        # Section heading
        heading = Paragraph("Assessment Overview", self.styles['CustomHeading'])
        elements.append(heading)

        elements.append(Spacer(1, 0.25*inch))

        # Key metrics in a grid
        metrics_data = [
            [
                self._create_metric_box(
                    str(overview.get('total_assessments', 0)),
                    "Total Assessments"
                ),
                self._create_metric_box(
                    str(overview.get('active_assessments', 0)),
                    "Active Assessments"
                ),
                self._create_metric_box(
                    str(overview.get('completed_assessments', 0)),
                    "Completed"
                )
            ],
            [
                self._create_metric_box(
                    f"{overview.get('avg_completion_percentage', 0)}%",
                    "Avg Completion"
                ),
                self._create_metric_box(
                    f"{overview.get('avg_confidence_score', 0):.2f}",
                    "Avg Confidence"
                ),
                self._create_metric_box(
                    str(overview.get('total_evidence_collected', 0)),
                    "Evidence Collected"
                )
            ]
        ]

        metrics_table = Table(metrics_data, colWidths=[2.2*inch, 2.2*inch, 2.2*inch])
        metrics_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))

        elements.append(metrics_table)

        return elements

    def _create_metric_box(self, value: str, label: str) -> list:
        """Create a metric box with value and label"""
        return [
            Paragraph(value, self.styles['MetricValue']),
            Paragraph(label, self.styles['MetricLabel'])
        ]

    def _create_compliance_section(self, compliance: Dict[str, Any]) -> list:
        """Create compliance section with charts"""
        elements = []

        # Section heading
        heading = Paragraph("Control Compliance", self.styles['CustomHeading'])
        elements.append(heading)

        elements.append(Spacer(1, 0.25*inch))

        # Compliance percentage
        compliance_pct = compliance.get('compliance_percentage', 0)
        color = self._get_compliance_color(compliance_pct)

        compliance_text = Paragraph(
            f"<font color='{color}'>{compliance_pct}%</font> Controls Met",
            self.styles['Heading1']
        )
        elements.append(compliance_text)

        elements.append(Spacer(1, 0.25*inch))

        # Status breakdown table
        status_data = [
            ['Status', 'Count', 'Percentage'],
            [
                'Met',
                str(compliance.get('controls_met', 0)),
                f"{(compliance.get('controls_met', 0) / compliance.get('total_controls', 1) * 100):.1f}%"
            ],
            [
                'Not Met',
                str(compliance.get('controls_not_met', 0)),
                f"{(compliance.get('controls_not_met', 0) / compliance.get('total_controls', 1) * 100):.1f}%"
            ],
            [
                'Partially Met',
                str(compliance.get('controls_partial', 0)),
                f"{(compliance.get('controls_partial', 0) / compliance.get('total_controls', 1) * 100):.1f}%"
            ],
            [
                'Not Applicable',
                str(compliance.get('controls_na', 0)),
                f"{(compliance.get('controls_na', 0) / compliance.get('total_controls', 1) * 100):.1f}%"
            ]
        ]

        status_table = Table(status_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
        status_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(status_table)

        elements.append(Spacer(1, 0.5*inch))

        # Domain breakdown (if available)
        by_domain = compliance.get('by_domain', {})
        if by_domain:
            domain_heading = Paragraph("Compliance by Domain", self.styles['Heading3'])
            elements.append(domain_heading)
            elements.append(Spacer(1, 0.1*inch))

            # Create domain table
            domain_data = [['Domain', 'Total', 'Met', 'Not Met', 'Compliance %']]

            for domain, stats in sorted(by_domain.items()):
                domain_data.append([
                    domain,
                    str(stats.get('total', 0)),
                    str(stats.get('met', 0)),
                    str(stats.get('not_met', 0)),
                    f"{stats.get('compliance_pct', 0)}%"
                ])

            domain_table = Table(domain_data, colWidths=[1.2*inch, 1*inch, 1*inch, 1.2*inch, 1.2*inch])
            domain_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
            ]))

            elements.append(domain_table)

        return elements

    def _create_evidence_section(self, evidence_stats: Dict[str, Any]) -> list:
        """Create evidence section"""
        elements = []

        # Section heading
        heading = Paragraph("Evidence Collection", self.styles['CustomHeading'])
        elements.append(heading)

        elements.append(Spacer(1, 0.25*inch))

        # Evidence metrics
        total_evidence = evidence_stats.get('total_evidence', 0)
        total_size_mb = evidence_stats.get('total_size_bytes', 0) / (1024 * 1024)
        controls_with_evidence = evidence_stats.get('controls_with_evidence', 0)

        evidence_data = [
            ['Metric', 'Value'],
            ['Total Evidence Files', str(total_evidence)],
            ['Total Storage Used', f"{total_size_mb:.1f} MB"],
            ['Controls with Evidence', str(controls_with_evidence)],
            ['Evidence Types', str(evidence_stats.get('evidence_types', 0))]
        ]

        evidence_table = Table(evidence_data, colWidths=[3*inch, 2*inch])
        evidence_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ]))

        elements.append(evidence_table)

        return elements

    def _create_savings_section(self, savings: Dict[str, Any]) -> list:
        """Create savings section"""
        elements = []

        # Section heading
        heading = Paragraph("Cost & Time Savings", self.styles['CustomHeading'])
        elements.append(heading)

        elements.append(Spacer(1, 0.25*inch))

        # Key savings metrics
        hours_saved = savings.get('hours_saved', 0)
        cost_savings = savings.get('cost_savings', 0)

        savings_text = Paragraph(
            f"<font color='#4CAF50'>${cost_savings:,.2f}</font> saved ({hours_saved} hours)",
            self.styles['Heading1']
        )
        elements.append(savings_text)

        elements.append(Spacer(1, 0.25*inch))

        # Savings breakdown
        savings_data = [
            ['Component', 'Manual Hours', 'Automated Hours', 'Hours Saved'],
            [
                'Provider Inheritance',
                f"{savings.get('provider_inheritance_hours', 0):.1f}",
                '0.0',
                f"{savings.get('provider_inheritance_hours', 0):.1f}"
            ],
            [
                'AI Analysis',
                f"{savings.get('ai_analysis_hours', 0):.1f}",
                '0.1',
                f"{savings.get('ai_analysis_hours', 0) - 0.1:.1f}"
            ],
            [
                'Report Generation',
                f"{savings.get('report_generation_hours', 0):.1f}",
                '0.05',
                f"{savings.get('report_generation_hours', 0) - 0.05:.1f}"
            ],
            [
                'Total',
                f"{savings.get('manual_hours', 0):.1f}",
                f"{savings.get('automated_hours', 0):.1f}",
                f"{hours_saved:.1f}"
            ]
        ]

        savings_table = Table(savings_data, colWidths=[2.5*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        savings_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#E8F5E9')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))

        elements.append(savings_table)

        return elements

    def _get_compliance_color(self, compliance_pct: float) -> str:
        """Get color based on compliance percentage"""
        if compliance_pct >= 90:
            return '#4CAF50'  # Green
        elif compliance_pct >= 75:
            return '#8BC34A'  # Light green
        elif compliance_pct >= 50:
            return '#FFC107'  # Amber
        elif compliance_pct >= 25:
            return '#FF9800'  # Orange
        else:
            return '#F44336'  # Red
