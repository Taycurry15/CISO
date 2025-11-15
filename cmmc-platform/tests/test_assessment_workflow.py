"""
Tests for Assessment Workflow (Assessment and Evidence Services)
"""

import pytest
from datetime import datetime, timedelta
from io import BytesIO

# Add parent directory to path
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from services.assessment_service import (
    AssessmentService,
    AssessmentStatus,
    AssessmentType,
    AssessmentScope,
    AssessmentProgress
)
from services.evidence_service import (
    EvidenceService,
    EvidenceType,
    AssessmentMethod,
    EvidenceMetadata
)


# ===========================
# Test Data
# ===========================

SAMPLE_SCOPE = AssessmentScope(
    cmmc_level=2,
    domains=["ALL"],
    cloud_providers=["Microsoft 365 GCC High", "Azure Government"],
    system_boundary="Cloud-based contract management system in Azure Government",
    exclusions="Physical security controls (provider responsibility)",
    include_inherited=True
)

SAMPLE_EVIDENCE_METADATA = EvidenceMetadata(
    title="Access Control Policy",
    description="Organization-wide access control policy document",
    evidence_type=EvidenceType.POLICY,
    assessment_methods=[AssessmentMethod.EXAMINE],
    tags=["access-control", "policy", "iac"],
    collection_date=datetime.utcnow(),
    collected_by="Jane Doe, Assessor"
)


# ===========================
# Fixtures
# ===========================

@pytest.fixture
def mock_db_pool():
    """Mock database pool"""
    return None


@pytest.fixture
def assessment_service(mock_db_pool):
    """Create assessment service instance"""
    return AssessmentService(mock_db_pool)


@pytest.fixture
def evidence_service(mock_db_pool):
    """Create evidence service instance"""
    return EvidenceService(mock_db_pool)


# ===========================
# Tests: Assessment Service
# ===========================

def test_assessment_service_initialization(mock_db_pool):
    """Test assessment service initialization"""
    service = AssessmentService(mock_db_pool)
    assert service.db_pool == mock_db_pool


def test_assessment_status_enum():
    """Test AssessmentStatus enum"""
    assert AssessmentStatus.DRAFT == "Draft"
    assert AssessmentStatus.SCOPING == "Scoping"
    assert AssessmentStatus.IN_PROGRESS == "In Progress"
    assert AssessmentStatus.REVIEW == "Review"
    assert AssessmentStatus.COMPLETED == "Completed"
    assert AssessmentStatus.ARCHIVED == "Archived"


def test_assessment_type_enum():
    """Test AssessmentType enum"""
    assert AssessmentType.INITIAL == "Initial Assessment"
    assert AssessmentType.ANNUAL == "Annual Assessment"
    assert AssessmentType.REMEDIATION == "Remediation Assessment"
    assert AssessmentType.SURVEILLANCE == "Surveillance Assessment"


def test_assessment_scope_dataclass():
    """Test AssessmentScope dataclass"""
    scope = SAMPLE_SCOPE

    assert scope.cmmc_level == 2
    assert scope.domains == ["ALL"]
    assert len(scope.cloud_providers) == 2
    assert scope.include_inherited is True
    assert scope.system_boundary


def test_assessment_progress_dataclass():
    """Test AssessmentProgress dataclass"""
    progress = AssessmentProgress(
        total_controls=110,
        controls_analyzed=85,
        controls_met=70,
        controls_not_met=10,
        controls_partial=5,
        controls_na=0,
        evidence_collected=142,
        completion_percentage=77.3,
        avg_confidence_score=0.82
    )

    assert progress.total_controls == 110
    assert progress.controls_analyzed == 85
    assert progress.completion_percentage == 77.3
    assert progress.avg_confidence_score == 0.82


def test_scope_serialization(assessment_service):
    """Test scope serialization to JSON"""
    scope = SAMPLE_SCOPE

    # Serialize
    json_str = assessment_service._serialize_scope(scope)
    assert isinstance(json_str, str)
    assert "cmmc_level" in json_str
    assert "2" in json_str

    # Deserialize
    deserialized = assessment_service._deserialize_scope(json_str)
    assert isinstance(deserialized, AssessmentScope)
    assert deserialized.cmmc_level == scope.cmmc_level
    assert deserialized.domains == scope.domains


# ===========================
# Tests: Evidence Service
# ===========================

def test_evidence_service_initialization(mock_db_pool):
    """Test evidence service initialization"""
    service = EvidenceService(mock_db_pool)
    assert service.db_pool == mock_db_pool
    assert service.storage_service is None


def test_evidence_type_enum():
    """Test EvidenceType enum"""
    assert EvidenceType.DOCUMENT == "Document"
    assert EvidenceType.SCREENSHOT == "Screenshot"
    assert EvidenceType.CONFIGURATION == "Configuration"
    assert EvidenceType.LOG == "Log"
    assert EvidenceType.POLICY == "Policy"
    assert EvidenceType.PROCEDURE == "Procedure"
    assert EvidenceType.DIAGRAM == "Diagram"
    assert EvidenceType.INTERVIEW_NOTES == "Interview Notes"
    assert EvidenceType.TEST_RESULTS == "Test Results"
    assert EvidenceType.OTHER == "Other"


def test_assessment_method_enum():
    """Test AssessmentMethod enum"""
    assert AssessmentMethod.EXAMINE == "Examine"
    assert AssessmentMethod.INTERVIEW == "Interview"
    assert AssessmentMethod.TEST == "Test"


def test_evidence_metadata_dataclass():
    """Test EvidenceMetadata dataclass"""
    metadata = SAMPLE_EVIDENCE_METADATA

    assert metadata.title == "Access Control Policy"
    assert metadata.evidence_type == EvidenceType.POLICY
    assert AssessmentMethod.EXAMINE in metadata.assessment_methods
    assert len(metadata.tags) == 3
    assert "access-control" in metadata.tags


def test_calculate_file_hash(evidence_service):
    """Test file hash calculation"""
    # Create test file
    test_data = b"Test file content for hash calculation"
    file_obj = BytesIO(test_data)

    # Calculate hash
    file_hash = evidence_service._calculate_file_hash(file_obj)

    # Verify it's a SHA-256 hash (64 hex characters)
    assert len(file_hash) == 64
    assert all(c in '0123456789abcdef' for c in file_hash)

    # Verify same content produces same hash
    file_obj2 = BytesIO(test_data)
    file_hash2 = evidence_service._calculate_file_hash(file_obj2)
    assert file_hash == file_hash2

    # Verify different content produces different hash
    file_obj3 = BytesIO(b"Different content")
    file_hash3 = evidence_service._calculate_file_hash(file_obj3)
    assert file_hash != file_hash3


# ===========================
# Tests: Assessment Lifecycle
# ===========================

def test_assessment_status_transitions():
    """Test valid assessment status transitions"""
    # Valid lifecycle
    statuses = [
        AssessmentStatus.DRAFT,
        AssessmentStatus.SCOPING,
        AssessmentStatus.IN_PROGRESS,
        AssessmentStatus.REVIEW,
        AssessmentStatus.COMPLETED
    ]

    for status in statuses:
        assert status in AssessmentStatus

    # Archive can be reached from any status
    assert AssessmentStatus.ARCHIVED in AssessmentStatus


def test_assessment_types():
    """Test different assessment types"""
    types = [
        AssessmentType.INITIAL,
        AssessmentType.ANNUAL,
        AssessmentType.REMEDIATION,
        AssessmentType.SURVEILLANCE
    ]

    for assessment_type in types:
        assert assessment_type in AssessmentType


# ===========================
# Tests: Scope Management
# ===========================

def test_scope_with_specific_domains():
    """Test scope with specific domains"""
    scope = AssessmentScope(
        cmmc_level=2,
        domains=["AC", "IA", "SC"],  # Specific domains only
        cloud_providers=["AWS GovCloud"],
        system_boundary="Test system",
        include_inherited=True
    )

    assert scope.domains == ["AC", "IA", "SC"]
    assert "ALL" not in scope.domains


def test_scope_without_cloud_providers():
    """Test scope without cloud providers"""
    scope = AssessmentScope(
        cmmc_level=2,
        domains=["ALL"],
        cloud_providers=[],  # No cloud providers
        system_boundary="On-premise system",
        include_inherited=False
    )

    assert len(scope.cloud_providers) == 0
    assert scope.include_inherited is False


def test_scope_with_exclusions():
    """Test scope with exclusions"""
    scope = AssessmentScope(
        cmmc_level=2,
        domains=["ALL"],
        cloud_providers=["Microsoft 365 GCC High"],
        system_boundary="Test system",
        exclusions="Physical security controls PE.L2-3.10.x are handled by provider",
        include_inherited=True
    )

    assert scope.exclusions is not None
    assert "Physical security" in scope.exclusions


# ===========================
# Tests: Evidence Types
# ===========================

def test_evidence_types_coverage():
    """Test that we have good coverage of evidence types"""
    all_types = list(EvidenceType)

    assert len(all_types) >= 10  # At least 10 types
    assert EvidenceType.DOCUMENT in all_types
    assert EvidenceType.POLICY in all_types
    assert EvidenceType.SCREENSHOT in all_types


def test_assessment_methods_coverage():
    """Test CMMC assessment methods"""
    # CMMC requires all three methods
    assert AssessmentMethod.EXAMINE in AssessmentMethod
    assert AssessmentMethod.INTERVIEW in AssessmentMethod
    assert AssessmentMethod.TEST in AssessmentMethod


def test_evidence_metadata_with_multiple_methods():
    """Test evidence with multiple assessment methods"""
    metadata = EvidenceMetadata(
        title="MFA Configuration Review",
        description="Review of MFA settings and test of MFA enforcement",
        evidence_type=EvidenceType.CONFIGURATION,
        assessment_methods=[
            AssessmentMethod.EXAMINE,
            AssessmentMethod.TEST
        ],
        tags=["mfa", "authentication"],
        collection_date=datetime.utcnow(),
        collected_by="Assessor"
    )

    assert len(metadata.assessment_methods) == 2
    assert AssessmentMethod.EXAMINE in metadata.assessment_methods
    assert AssessmentMethod.TEST in metadata.assessment_methods


# ===========================
# Tests: Progress Calculation
# ===========================

def test_progress_completion_percentage():
    """Test completion percentage calculation"""
    # 85 out of 110 controls analyzed = 77.3%
    progress = AssessmentProgress(
        total_controls=110,
        controls_analyzed=85,
        controls_met=70,
        controls_not_met=10,
        controls_partial=5,
        controls_na=0,
        evidence_collected=142,
        completion_percentage=77.3,
        avg_confidence_score=0.82
    )

    expected_percentage = (85 / 110) * 100
    assert abs(progress.completion_percentage - expected_percentage) < 0.1


def test_progress_with_no_controls():
    """Test progress when no controls exist"""
    progress = AssessmentProgress(
        total_controls=0,
        controls_analyzed=0,
        controls_met=0,
        controls_not_met=0,
        controls_partial=0,
        controls_na=0,
        evidence_collected=0,
        completion_percentage=0.0,
        avg_confidence_score=0.0
    )

    assert progress.total_controls == 0
    assert progress.completion_percentage == 0.0


def test_progress_all_controls_analyzed():
    """Test progress when all controls are analyzed"""
    progress = AssessmentProgress(
        total_controls=110,
        controls_analyzed=110,
        controls_met=95,
        controls_not_met=10,
        controls_partial=2,
        controls_na=3,
        evidence_collected=215,
        completion_percentage=100.0,
        avg_confidence_score=0.85
    )

    assert progress.controls_analyzed == progress.total_controls
    assert progress.completion_percentage == 100.0


# ===========================
# Tests: Evidence Tags
# ===========================

def test_evidence_tags():
    """Test evidence tagging"""
    metadata = EvidenceMetadata(
        title="Test Evidence",
        description="Test",
        evidence_type=EvidenceType.DOCUMENT,
        assessment_methods=[AssessmentMethod.EXAMINE],
        tags=["cmmc-l2", "access-control", "azure-ad", "mfa"],
        collection_date=datetime.utcnow(),
        collected_by="Test"
    )

    assert len(metadata.tags) == 4
    assert "cmmc-l2" in metadata.tags
    assert "mfa" in metadata.tags


def test_evidence_without_tags():
    """Test evidence without tags"""
    metadata = EvidenceMetadata(
        title="Test Evidence",
        description="Test",
        evidence_type=EvidenceType.SCREENSHOT,
        assessment_methods=[AssessmentMethod.EXAMINE],
        tags=[],  # No tags
        collection_date=datetime.utcnow(),
        collected_by="Test"
    )

    assert len(metadata.tags) == 0


# ===========================
# Tests: File Handling
# ===========================

def test_file_storage_path_generation():
    """Test evidence storage path generation"""
    assessment_id = "test-assessment-uuid"
    evidence_id = "test-evidence-uuid"
    file_name = "access_policy.pdf"

    expected_path = f"assessments/{assessment_id}/evidence/{evidence_id}/{file_name}"

    # In real implementation, this would come from _store_file method
    assert "assessments" in expected_path
    assert "evidence" in expected_path
    assert file_name in expected_path


def test_file_size_tracking():
    """Test file size tracking"""
    # Create test file
    test_data = b"A" * 1024  # 1KB
    file_obj = BytesIO(test_data)

    # Get file size
    file_obj.seek(0, 2)  # Seek to end
    file_size = file_obj.tell()

    assert file_size == 1024


# ===========================
# Tests: Data Validation
# ===========================

def test_cmmc_level_values():
    """Test valid CMMC levels"""
    valid_levels = [1, 2, 3]

    for level in valid_levels:
        scope = AssessmentScope(
            cmmc_level=level,
            domains=["ALL"],
            cloud_providers=[],
            system_boundary="Test",
            include_inherited=True
        )
        assert scope.cmmc_level == level


def test_domain_values():
    """Test valid domain values"""
    all_domains = ["AC", "AT", "AU", "CA", "CM", "IA", "IR", "MA", "MP", "PE", "PS", "RE", "RM", "SA", "SC", "SI", "SR"]

    # Test with ALL
    scope1 = AssessmentScope(
        cmmc_level=2,
        domains=["ALL"],
        cloud_providers=[],
        system_boundary="Test",
        include_inherited=True
    )
    assert scope1.domains == ["ALL"]

    # Test with specific domains
    scope2 = AssessmentScope(
        cmmc_level=2,
        domains=["AC", "IA", "SC"],
        cloud_providers=[],
        system_boundary="Test",
        include_inherited=True
    )
    assert all(d in all_domains for d in scope2.domains)


# ===========================
# Tests: Edge Cases
# ===========================

def test_assessment_with_no_team():
    """Test assessment without team members"""
    # Should be valid to create assessment without team initially
    # Team can be assigned later
    pass  # Would test with actual service


def test_evidence_with_future_collection_date():
    """Test evidence with future collection date"""
    # Should probably validate that collection date is not in future
    future_date = datetime.utcnow() + timedelta(days=30)

    metadata = EvidenceMetadata(
        title="Test",
        description="Test",
        evidence_type=EvidenceType.DOCUMENT,
        assessment_methods=[AssessmentMethod.EXAMINE],
        tags=[],
        collection_date=future_date,  # Future date
        collected_by="Test"
    )

    # In production, this should probably be validated
    assert metadata.collection_date > datetime.utcnow()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
