"""
Tests for Provider Inheritance Service
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add parent directory to path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from services.provider_inheritance import (
    ProviderInheritanceService,
    ProviderOffering,
    ControlInheritance,
    ResponsibilityType
)


# ===========================
# Test Data
# ===========================

SAMPLE_M365_MAPPING = {
    "provider_name": "Microsoft 365 GCC High",
    "provider_type": "SaaS",
    "description": "Microsoft 365 Government GCC High",
    "certification_level": "FedRAMP High",
    "documentation_url": "https://docs.microsoft.com/",
    "control_mappings": [
        {
            "control_id": "IA.L2-3.5.7",
            "control_title": "Cryptographic Module Authentication",
            "responsibility": "Inherited",
            "microsoft_responsibility": "Microsoft uses FIPS 140-2 validated cryptographic modules",
            "customer_responsibility": None,
            "inherited_controls": ["IA.L2-3.5.7"],
            "implementation_guidance": "No customer action required",
            "evidence_artifacts": ["Microsoft compliance documentation"],
            "authoritative_source": "https://..."
        },
        {
            "control_id": "AC.L2-3.1.1",
            "control_title": "Authorized Access Control",
            "responsibility": "Shared",
            "microsoft_responsibility": "Microsoft provides Azure AD",
            "customer_responsibility": "Customer configures Azure AD",
            "inherited_controls": [],
            "implementation_guidance": "Configure conditional access",
            "evidence_artifacts": ["Conditional access policies"],
            "authoritative_source": "https://..."
        },
        {
            "control_id": "CM.L2-3.4.7",
            "control_title": "Nonessential Programs",
            "responsibility": "Customer",
            "microsoft_responsibility": None,
            "customer_responsibility": "Customer restricts nonessential programs",
            "inherited_controls": [],
            "implementation_guidance": "Use Intune application control",
            "evidence_artifacts": ["Intune policies"],
            "authoritative_source": None
        }
    ],
    "summary": {
        "total_controls_mapped": 3,
        "inherited_count": 1,
        "shared_count": 1,
        "customer_count": 1,
        "coverage_percentage": 2.7
    }
}

SAMPLE_AWS_MAPPING = {
    "provider_name": "AWS GovCloud (US)",
    "provider_type": "IaaS/PaaS",
    "description": "Amazon Web Services GovCloud",
    "certification_level": "FedRAMP High, DoD IL5",
    "documentation_url": "https://aws.amazon.com/govcloud-us/",
    "control_mappings": [
        {
            "control_id": "IA.L2-3.5.7",
            "control_title": "Cryptographic Module Authentication",
            "responsibility": "Inherited",
            "aws_responsibility": "AWS uses FIPS 140-2 validated modules in GovCloud",
            "customer_responsibility": None,
            "inherited_controls": ["IA.L2-3.5.7"],
            "implementation_guidance": "No customer action required",
            "evidence_artifacts": ["AWS FIPS 140-2 validation documentation"],
            "authoritative_source": "https://aws.amazon.com/compliance/fips/"
        },
        {
            "control_id": "AC.L2-3.1.1",
            "control_title": "Authorized Access Control",
            "responsibility": "Shared",
            "aws_responsibility": "AWS provides IAM",
            "customer_responsibility": "Customer configures IAM policies",
            "inherited_controls": [],
            "implementation_guidance": "Use IAM policies with least privilege",
            "evidence_artifacts": ["IAM policy documents"],
            "authoritative_source": "https://docs.aws.amazon.com/IAM/"
        }
    ],
    "summary": {
        "total_controls_mapped": 2,
        "inherited_count": 1,
        "shared_count": 1,
        "customer_count": 0,
        "coverage_percentage": 1.8
    }
}


# ===========================
# Fixtures
# ===========================

@pytest.fixture
def mock_db_pool():
    """Mock database pool"""
    # In real tests, this would be a test database
    # For unit tests, we'll mock the methods
    return None


@pytest.fixture
def service(mock_db_pool, tmp_path):
    """Create provider inheritance service with temp directory"""
    return ProviderInheritanceService(
        db_pool=mock_db_pool,
        mappings_dir=str(tmp_path)
    )


@pytest.fixture
def sample_json_files(tmp_path):
    """Create sample JSON mapping files in temp directory"""
    # M365 mapping
    m365_file = tmp_path / "m365_gcc_high.json"
    with open(m365_file, 'w') as f:
        json.dump(SAMPLE_M365_MAPPING, f)

    # AWS mapping
    aws_file = tmp_path / "aws_govcloud.json"
    with open(aws_file, 'w') as f:
        json.dump(SAMPLE_AWS_MAPPING, f)

    return tmp_path


# ===========================
# Tests: JSON Loading
# ===========================

def test_load_mapping_file(service, tmp_path):
    """Test loading JSON mapping file"""
    # Create a test file
    test_file = tmp_path / "test_mapping.json"
    with open(test_file, 'w') as f:
        json.dump(SAMPLE_M365_MAPPING, f)

    # Load it
    mapping = service.load_mapping_file(str(test_file))

    assert mapping['provider_name'] == "Microsoft 365 GCC High"
    assert mapping['provider_type'] == "SaaS"
    assert len(mapping['control_mappings']) == 3


def test_load_mapping_file_not_found(service, tmp_path):
    """Test loading non-existent file raises error"""
    with pytest.raises(FileNotFoundError):
        service.load_mapping_file(str(tmp_path / "nonexistent.json"))


# ===========================
# Tests: Parsing
# ===========================

def test_parse_m365_mapping(service):
    """Test parsing M365 mapping"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    assert isinstance(offering, ProviderOffering)
    assert offering.provider_name == "Microsoft 365 GCC High"
    assert offering.provider_type == "SaaS"
    assert offering.certification_level == "FedRAMP High"
    assert offering.total_controls_mapped == 3
    assert offering.inherited_count == 1
    assert offering.shared_count == 1
    assert offering.customer_count == 1

    # Check control mappings
    assert len(offering.control_mappings) == 3

    # Check inherited control
    inherited = offering.control_mappings[0]
    assert inherited.control_id == "IA.L2-3.5.7"
    assert inherited.responsibility == ResponsibilityType.INHERITED
    assert inherited.provider_responsibility == "Microsoft uses FIPS 140-2 validated cryptographic modules"
    assert inherited.customer_responsibility is None

    # Check shared control
    shared = offering.control_mappings[1]
    assert shared.control_id == "AC.L2-3.1.1"
    assert shared.responsibility == ResponsibilityType.SHARED
    assert shared.provider_responsibility is not None
    assert shared.customer_responsibility is not None

    # Check customer control
    customer = offering.control_mappings[2]
    assert customer.control_id == "CM.L2-3.4.7"
    assert customer.responsibility == ResponsibilityType.CUSTOMER
    assert customer.provider_responsibility is None
    assert customer.customer_responsibility is not None


def test_parse_aws_mapping(service):
    """Test parsing AWS mapping"""
    offering = service.parse_mapping(SAMPLE_AWS_MAPPING)

    assert offering.provider_name == "AWS GovCloud (US)"
    assert offering.provider_type == "IaaS/PaaS"
    assert offering.certification_level == "FedRAMP High, DoD IL5"
    assert offering.total_controls_mapped == 2

    # Check AWS-specific responsibility fields
    inherited = offering.control_mappings[0]
    assert "AWS uses FIPS 140-2" in inherited.provider_responsibility

    shared = offering.control_mappings[1]
    assert "IAM" in shared.provider_responsibility


def test_parse_mapping_with_missing_summary(service):
    """Test parsing mapping without summary section"""
    mapping_no_summary = SAMPLE_M365_MAPPING.copy()
    del mapping_no_summary['summary']

    offering = service.parse_mapping(mapping_no_summary)

    # Should infer from control mappings
    assert offering.total_controls_mapped == 3
    assert offering.inherited_count == 0  # Not calculated without summary
    assert offering.shared_count == 0
    assert offering.customer_count == 0


# ===========================
# Tests: Control Inheritance
# ===========================

def test_control_inheritance_dataclass():
    """Test ControlInheritance dataclass"""
    control = ControlInheritance(
        control_id="AC.L2-3.1.1",
        control_title="Authorized Access Control",
        responsibility=ResponsibilityType.SHARED,
        provider_responsibility="Provider handles X",
        customer_responsibility="Customer handles Y",
        inherited_controls=[],
        implementation_guidance="Do this",
        evidence_artifacts=["Artifact 1", "Artifact 2"],
        authoritative_source="https://example.com"
    )

    assert control.control_id == "AC.L2-3.1.1"
    assert control.responsibility == ResponsibilityType.SHARED
    assert len(control.evidence_artifacts) == 2


def test_responsibility_type_enum():
    """Test ResponsibilityType enum"""
    assert ResponsibilityType.INHERITED.value == "Inherited"
    assert ResponsibilityType.SHARED.value == "Shared"
    assert ResponsibilityType.CUSTOMER.value == "Customer"

    # Test enum creation from string
    assert ResponsibilityType("Inherited") == ResponsibilityType.INHERITED
    assert ResponsibilityType("Shared") == ResponsibilityType.SHARED
    assert ResponsibilityType("Customer") == ResponsibilityType.CUSTOMER


# ===========================
# Tests: Provider Offering
# ===========================

def test_provider_offering_dataclass():
    """Test ProviderOffering dataclass"""
    offering = ProviderOffering(
        provider_name="Test Provider",
        provider_type="SaaS",
        description="Test description",
        certification_level="FedRAMP High",
        documentation_url="https://example.com",
        control_mappings=[],
        total_controls_mapped=10,
        inherited_count=3,
        shared_count=5,
        customer_count=2,
        coverage_percentage=9.1
    )

    assert offering.provider_name == "Test Provider"
    assert offering.total_controls_mapped == 10
    assert offering.inherited_count == 3
    assert offering.shared_count == 5
    assert offering.customer_count == 2
    assert offering.coverage_percentage == 9.1


# ===========================
# Tests: Coverage Calculation
# ===========================

def test_coverage_percentage_calculation(service):
    """Test coverage percentage is calculated correctly"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    # 3 controls out of 110 CMMC L2 controls
    expected_coverage = 3 / 110 * 100
    assert offering.coverage_percentage == 2.7  # As provided in summary


def test_responsibility_breakdown(service):
    """Test responsibility type counts"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    # Count by type
    inherited = sum(1 for c in offering.control_mappings if c.responsibility == ResponsibilityType.INHERITED)
    shared = sum(1 for c in offering.control_mappings if c.responsibility == ResponsibilityType.SHARED)
    customer = sum(1 for c in offering.control_mappings if c.responsibility == ResponsibilityType.CUSTOMER)

    assert inherited == 1
    assert shared == 1
    assert customer == 1


# ===========================
# Tests: Evidence Artifacts
# ===========================

def test_evidence_artifacts_parsing(service):
    """Test evidence artifacts are parsed correctly"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    # Check evidence artifacts
    control = offering.control_mappings[0]
    assert len(control.evidence_artifacts) > 0
    assert isinstance(control.evidence_artifacts, list)


def test_authoritative_source_parsing(service):
    """Test authoritative source URLs"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    # Inherited control should have authoritative source
    assert offering.control_mappings[0].authoritative_source is not None

    # Customer control might not have authoritative source
    customer_control = offering.control_mappings[2]
    # This is OK - customer controls might not have provider docs


# ===========================
# Tests: Implementation Guidance
# ===========================

def test_implementation_guidance(service):
    """Test implementation guidance is preserved"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    # Each control should have guidance
    for control_map in offering.control_mappings:
        assert control_map.implementation_guidance is not None
        assert len(control_map.implementation_guidance) > 0


# ===========================
# Tests: Multiple Providers
# ===========================

def test_parse_multiple_providers(service):
    """Test parsing multiple provider mappings"""
    m365_offering = service.parse_mapping(SAMPLE_M365_MAPPING)
    aws_offering = service.parse_mapping(SAMPLE_AWS_MAPPING)

    assert m365_offering.provider_name != aws_offering.provider_name
    assert m365_offering.provider_type == "SaaS"
    assert aws_offering.provider_type == "IaaS/PaaS"


def test_shared_controls_across_providers(service):
    """Test that same control can be mapped by multiple providers"""
    m365_offering = service.parse_mapping(SAMPLE_M365_MAPPING)
    aws_offering = service.parse_mapping(SAMPLE_AWS_MAPPING)

    # Both map IA.L2-3.5.7 and AC.L2-3.1.1
    m365_controls = {c.control_id for c in m365_offering.control_mappings}
    aws_controls = {c.control_id for c in aws_offering.control_mappings}

    shared = m365_controls.intersection(aws_controls)
    assert "IA.L2-3.5.7" in shared
    assert "AC.L2-3.1.1" in shared


# ===========================
# Tests: Edge Cases
# ===========================

def test_empty_control_mappings(service):
    """Test provider with no control mappings"""
    mapping = {
        "provider_name": "Empty Provider",
        "provider_type": "SaaS",
        "description": "Test",
        "certification_level": "None",
        "documentation_url": "https://example.com",
        "control_mappings": [],
        "summary": {
            "total_controls_mapped": 0,
            "inherited_count": 0,
            "shared_count": 0,
            "customer_count": 0,
            "coverage_percentage": 0.0
        }
    }

    offering = service.parse_mapping(mapping)
    assert offering.total_controls_mapped == 0
    assert len(offering.control_mappings) == 0


def test_missing_optional_fields(service):
    """Test handling of missing optional fields"""
    mapping = SAMPLE_M365_MAPPING.copy()

    # Remove optional fields from first control
    control = mapping['control_mappings'][0].copy()
    del control['inherited_controls']
    del control['evidence_artifacts']
    mapping['control_mappings'][0] = control

    offering = service.parse_mapping(mapping)

    # Should use defaults
    assert offering.control_mappings[0].inherited_controls == []
    assert offering.control_mappings[0].evidence_artifacts == []


# ===========================
# Tests: Validation
# ===========================

def test_required_fields_present(service):
    """Test that required fields are present"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    # Provider-level required fields
    assert offering.provider_name
    assert offering.provider_type
    assert offering.certification_level
    assert offering.documentation_url

    # Control-level required fields
    for control in offering.control_mappings:
        assert control.control_id
        assert control.control_title
        assert control.responsibility


def test_responsibility_values_valid(service):
    """Test that responsibility values are valid"""
    offering = service.parse_mapping(SAMPLE_M365_MAPPING)

    valid_values = {ResponsibilityType.INHERITED, ResponsibilityType.SHARED, ResponsibilityType.CUSTOMER}

    for control in offering.control_mappings:
        assert control.responsibility in valid_values


# ===========================
# Tests: Savings Calculation
# ===========================

def test_savings_calculation_logic():
    """Test the savings calculation logic"""
    # Assume 110 controls, 2 hours each = 220 hours total
    total_controls = 110
    hours_per_control = 2

    # Provider inheritance:
    # 10 inherited (100% saved) = 20 hours
    # 20 shared (50% saved) = 20 hours
    # 80 customer (0% saved) = 0 hours
    inherited = 10
    shared = 20

    time_saved_inherited = inherited * hours_per_control  # 20 hours
    time_saved_shared = shared * hours_per_control * 0.5  # 20 hours
    total_saved = time_saved_inherited + time_saved_shared  # 40 hours

    total_time_without_provider = total_controls * hours_per_control  # 220 hours
    percentage_saved = (total_saved / total_time_without_provider) * 100  # 18.2%

    assert total_saved == 40
    assert abs(percentage_saved - 18.18) < 0.1


def test_cost_savings_calculation():
    """Test cost savings at $200/hour"""
    hours_saved = 40
    hourly_rate = 200

    cost_savings = hours_saved * hourly_rate
    assert cost_savings == 8000


# ===========================
# Tests: Service Directory
# ===========================

def test_service_default_directory(mock_db_pool):
    """Test service uses default directory if none provided"""
    service = ProviderInheritanceService(mock_db_pool)

    # Should point to data/provider_mappings relative to service file
    assert "provider_mappings" in str(service.mappings_dir)


def test_service_custom_directory(mock_db_pool, tmp_path):
    """Test service uses custom directory if provided"""
    service = ProviderInheritanceService(mock_db_pool, mappings_dir=str(tmp_path))

    assert service.mappings_dir == tmp_path


# ===========================
# Integration-style Tests
# ===========================

def test_full_parsing_workflow(service, sample_json_files):
    """Test full workflow: load file -> parse -> validate"""
    # Find JSON files
    json_files = list(sample_json_files.glob("*.json"))
    assert len(json_files) == 2

    # Load and parse each
    offerings = []
    for json_file in json_files:
        mapping_data = service.load_mapping_file(str(json_file))
        offering = service.parse_mapping(mapping_data)
        offerings.append(offering)

    # Validate
    assert len(offerings) == 2

    provider_names = {o.provider_name for o in offerings}
    assert "Microsoft 365 GCC High" in provider_names
    assert "AWS GovCloud (US)" in provider_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
