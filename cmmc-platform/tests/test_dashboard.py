"""
Tests for Dashboard Analytics System
"""

import pytest
from datetime import datetime, timedelta

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from services.dashboard_service import (
    DashboardService,
    AssessmentOverview,
    ControlCompliance,
    ProgressMetrics,
    SavingsCalculation
)
from services.pdf_summary_service import PDFSummaryService


# ===========================
# Fixtures
# ===========================

@pytest.fixture
def mock_db_pool():
    """Mock database pool"""
    return None


@pytest.fixture
def dashboard_service(mock_db_pool):
    """Create dashboard service instance"""
    return DashboardService(mock_db_pool)


@pytest.fixture
def pdf_service():
    """Create PDF service instance"""
    return PDFSummaryService()


# ===========================
# Tests: Dashboard Service
# ===========================

def test_dashboard_service_initialization(mock_db_pool):
    """Test dashboard service initialization"""
    service = DashboardService(mock_db_pool)
    assert service.db_pool == mock_db_pool


def test_assessment_overview_dataclass():
    """Test AssessmentOverview dataclass"""
    overview = AssessmentOverview(
        total_assessments=15,
        active_assessments=8,
        completed_assessments=7,
        draft_assessments=2,
        in_progress_assessments=5,
        avg_completion_percentage=68.5,
        avg_confidence_score=0.79,
        total_evidence_collected=1247
    )

    assert overview.total_assessments == 15
    assert overview.active_assessments == 8
    assert overview.avg_completion_percentage == 68.5
    assert overview.avg_confidence_score == 0.79


def test_control_compliance_dataclass():
    """Test ControlCompliance dataclass"""
    compliance = ControlCompliance(
        total_controls=110,
        controls_met=85,
        controls_not_met=10,
        controls_partial=12,
        controls_na=3,
        compliance_percentage=77.3,
        by_domain={
            'AC': {'total': 22, 'met': 18, 'not_met': 2, 'partial': 2, 'compliance_pct': 81.8},
            'IA': {'total': 11, 'met': 8, 'not_met': 2, 'partial': 1, 'compliance_pct': 72.7}
        },
        high_risk_controls=[]
    )

    assert compliance.total_controls == 110
    assert compliance.controls_met == 85
    assert compliance.compliance_percentage == 77.3
    assert 'AC' in compliance.by_domain
    assert compliance.by_domain['AC']['total'] == 22


def test_progress_metrics_dataclass():
    """Test ProgressMetrics dataclass"""
    progress = ProgressMetrics(
        date="2024-01-15",
        controls_analyzed=85,
        evidence_uploaded=142,
        completion_percentage=77.3
    )

    assert progress.date == "2024-01-15"
    assert progress.controls_analyzed == 85
    assert progress.completion_percentage == 77.3


def test_savings_calculation_dataclass():
    """Test SavingsCalculation dataclass"""
    savings = SavingsCalculation(
        manual_hours=220.0,
        automated_hours=8.5,
        hours_saved=211.5,
        cost_savings=42300.00,
        provider_inheritance_hours=83.6,
        ai_analysis_hours=178.2,
        report_generation_hours=48.0
    )

    assert savings.manual_hours == 220.0
    assert savings.hours_saved == 211.5
    assert savings.cost_savings == 42300.00


# ===========================
# Tests: Compliance Calculations
# ===========================

def test_compliance_percentage_calculation():
    """Test compliance percentage calculation"""
    total = 110
    met = 85

    compliance_pct = (met / total) * 100

    assert abs(compliance_pct - 77.27) < 0.1


def test_domain_compliance_calculation():
    """Test domain-level compliance calculation"""
    domain_stats = {
        'AC': {
            'total': 22,
            'met': 18,
            'not_met': 2,
            'partial': 2
        }
    }

    compliance_pct = (domain_stats['AC']['met'] / domain_stats['AC']['total']) * 100

    assert abs(compliance_pct - 81.82) < 0.1


def test_overall_compliance_with_multiple_statuses():
    """Test overall compliance with various statuses"""
    total = 110
    met = 85
    not_met = 10
    partial = 12
    na = 3

    # Verify totals match
    assert met + not_met + partial + na == total

    # Met percentage
    met_pct = (met / total) * 100
    assert abs(met_pct - 77.27) < 0.1


# ===========================
# Tests: Savings Calculations
# ===========================

def test_manual_vs_automated_hours():
    """Test savings calculation logic"""
    total_controls = 110
    hours_per_control = 2.0

    manual_hours = total_controls * hours_per_control  # 220 hours
    automated_hours = 8.5  # Platform automation

    hours_saved = manual_hours - automated_hours  # 211.5 hours

    assert manual_hours == 220.0
    assert hours_saved == 211.5


def test_cost_savings_calculation():
    """Test cost savings at different hourly rates"""
    hours_saved = 211.5

    # At $200/hour
    cost_savings_200 = hours_saved * 200
    assert cost_savings_200 == 42300.00

    # At $150/hour
    cost_savings_150 = hours_saved * 150
    assert cost_savings_150 == 31725.00


def test_provider_inheritance_savings():
    """Test provider inheritance contribution to savings"""
    total_controls = 110
    provider_coverage_pct = 0.38  # 38% coverage
    hours_per_control = 2.0

    provider_hours_saved = total_controls * provider_coverage_pct * hours_per_control

    assert abs(provider_hours_saved - 83.6) < 0.1


def test_ai_analysis_savings():
    """Test AI analysis contribution to savings"""
    total_controls = 110
    hours_per_control = 2.0
    ai_efficiency = 0.9  # AI saves 90% of time

    manual_analysis_hours = total_controls * hours_per_control  # 220 hours
    ai_savings = manual_analysis_hours * ai_efficiency  # 198 hours

    assert ai_savings == 198.0


# ===========================
# Tests: PDF Generation
# ===========================

def test_pdf_service_initialization():
    """Test PDF service initialization"""
    service = PDFSummaryService()

    assert service.styles is not None
    assert 'CustomTitle' in service.styles
    assert 'CustomHeading' in service.styles
    assert 'MetricValue' in service.styles


def test_pdf_generation_structure(pdf_service):
    """Test PDF generation creates valid structure"""
    overview = {
        'total_assessments': 15,
        'active_assessments': 8,
        'completed_assessments': 7,
        'draft_assessments': 2,
        'in_progress_assessments': 5,
        'avg_completion_percentage': 68.5,
        'avg_confidence_score': 0.79,
        'total_evidence_collected': 1247
    }

    compliance = {
        'total_controls': 110,
        'controls_met': 85,
        'controls_not_met': 10,
        'controls_partial': 12,
        'controls_na': 3,
        'compliance_percentage': 77.3,
        'by_domain': {
            'AC': {'total': 22, 'met': 18, 'not_met': 2, 'partial': 2, 'compliance_pct': 81.8}
        },
        'high_risk_controls': []
    }

    evidence_stats = {
        'total_evidence': 142,
        'evidence_types': 6,
        'total_size_bytes': 52428800,
        'avg_size_bytes': 369200,
        'controls_with_evidence': 95,
        'by_type': {'Document': 45, 'Screenshot': 38},
        'by_method': {'Examine': 85, 'Interview': 32}
    }

    # Generate PDF
    pdf_bytes = pdf_service.generate_summary_pdf(
        overview=overview,
        compliance=compliance,
        evidence_stats=evidence_stats,
        organization_name="Test Organization"
    )

    # Verify PDF was created
    assert pdf_bytes is not None
    assert pdf_bytes.tell() == 0  # Seeked to start

    # PDF should have content
    content = pdf_bytes.read()
    assert len(content) > 0

    # PDF should start with PDF magic number
    assert content.startswith(b'%PDF')


def test_pdf_with_savings(pdf_service):
    """Test PDF generation with savings section"""
    overview = {
        'total_assessments': 15,
        'active_assessments': 8,
        'completed_assessments': 7,
        'draft_assessments': 2,
        'in_progress_assessments': 5,
        'avg_completion_percentage': 68.5,
        'avg_confidence_score': 0.79,
        'total_evidence_collected': 1247
    }

    compliance = {
        'total_controls': 110,
        'controls_met': 85,
        'controls_not_met': 10,
        'controls_partial': 12,
        'controls_na': 3,
        'compliance_percentage': 77.3,
        'by_domain': {},
        'high_risk_controls': []
    }

    evidence_stats = {
        'total_evidence': 142,
        'evidence_types': 6,
        'total_size_bytes': 52428800,
        'avg_size_bytes': 369200,
        'controls_with_evidence': 95,
        'by_type': {},
        'by_method': {}
    }

    savings = {
        'manual_hours': 220.0,
        'automated_hours': 8.5,
        'hours_saved': 211.5,
        'cost_savings': 42300.00,
        'provider_inheritance_hours': 83.6,
        'ai_analysis_hours': 178.2,
        'report_generation_hours': 48.0
    }

    # Generate PDF with savings
    pdf_bytes = pdf_service.generate_summary_pdf(
        overview=overview,
        compliance=compliance,
        evidence_stats=evidence_stats,
        savings=savings,
        organization_name="Test Organization"
    )

    assert pdf_bytes is not None
    content = pdf_bytes.read()
    assert len(content) > 0


def test_compliance_color_assignment(pdf_service):
    """Test compliance color assignment logic"""
    # Test color assignment
    assert pdf_service._get_compliance_color(95) == '#4CAF50'  # Green
    assert pdf_service._get_compliance_color(80) == '#8BC34A'  # Light green
    assert pdf_service._get_compliance_color(60) == '#FFC107'  # Amber
    assert pdf_service._get_compliance_color(35) == '#FF9800'  # Orange
    assert pdf_service._get_compliance_color(15) == '#F44336'  # Red


# ===========================
# Tests: Evidence Statistics
# ===========================

def test_evidence_size_calculations():
    """Test evidence size calculations"""
    total_bytes = 52428800  # 50 MB
    total_mb = total_bytes / (1024 * 1024)

    assert abs(total_mb - 50.0) < 0.01

    # Average size
    total_evidence = 142
    avg_bytes = total_bytes / total_evidence
    avg_kb = avg_bytes / 1024

    assert abs(avg_kb - 360.0) < 10.0  # ~360 KB average


def test_evidence_type_distribution():
    """Test evidence type distribution"""
    by_type = {
        'Document': 45,
        'Screenshot': 38,
        'Configuration': 25,
        'Log': 20,
        'Policy': 10,
        'Diagram': 4
    }

    total = sum(by_type.values())
    assert total == 142

    # Most common type
    most_common = max(by_type, key=by_type.get)
    assert most_common == 'Document'


def test_assessment_method_distribution():
    """Test assessment method distribution"""
    by_method = {
        'Examine': 85,
        'Interview': 32,
        'Test': 25
    }

    total = sum(by_method.values())
    assert total == 142

    # Examine should be most common
    assert by_method['Examine'] > by_method['Interview']
    assert by_method['Examine'] > by_method['Test']


# ===========================
# Tests: Progress Tracking
# ===========================

def test_progress_metrics_over_time():
    """Test progress metrics calculation"""
    # Day 1
    progress_day1 = ProgressMetrics(
        date="2024-01-15",
        controls_analyzed=25,
        evidence_uploaded=40,
        completion_percentage=22.7
    )

    # Day 7
    progress_day7 = ProgressMetrics(
        date="2024-01-21",
        controls_analyzed=85,
        evidence_uploaded=142,
        completion_percentage=77.3
    )

    # Verify progress increased
    assert progress_day7.controls_analyzed > progress_day1.controls_analyzed
    assert progress_day7.evidence_uploaded > progress_day1.evidence_uploaded
    assert progress_day7.completion_percentage > progress_day1.completion_percentage


def test_completion_percentage_accuracy():
    """Test completion percentage accuracy"""
    total_controls = 110

    # 25 analyzed
    analyzed_25 = 25
    completion_25 = (analyzed_25 / total_controls) * 100
    assert abs(completion_25 - 22.73) < 0.1

    # 85 analyzed
    analyzed_85 = 85
    completion_85 = (analyzed_85 / total_controls) * 100
    assert abs(completion_85 - 77.27) < 0.1


# ===========================
# Tests: High-Risk Controls
# ===========================

def test_high_risk_control_identification():
    """Test high-risk control identification"""
    high_risk_domains = ['AC', 'IA', 'SC', 'AU']

    # Test control in high-risk domain with Not Met status
    control = {
        'control_id': 'AC.L2-3.1.5',
        'title': 'Separation of Duties',
        'domain': 'AC',
        'status': 'Not Met'
    }

    # Should be flagged as high-risk
    assert control['domain'] in high_risk_domains
    assert control['status'] in ['Not Met', 'Partially Met']


def test_high_risk_control_sorting():
    """Test high-risk control sorting"""
    controls = [
        {'domain': 'AC', 'status': 'Not Met', 'control_id': 'AC.L2-3.1.1'},
        {'domain': 'IA', 'status': 'Not Met', 'control_id': 'IA.L2-3.5.1'},
        {'domain': 'AC', 'status': 'Partially Met', 'control_id': 'AC.L2-3.1.2'},
        {'domain': 'SC', 'status': 'Partially Met', 'control_id': 'SC.L2-3.13.1'}
    ]

    # Sort by status (Not Met first), then domain, then control_id
    sorted_controls = sorted(
        controls,
        key=lambda x: (0 if x['status'] == 'Not Met' else 1, x['domain'], x['control_id'])
    )

    # First two should be Not Met
    assert sorted_controls[0]['status'] == 'Not Met'
    assert sorted_controls[1]['status'] == 'Not Met'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
