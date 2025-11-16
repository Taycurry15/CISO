"""
SPRS Score Calculator
=====================
Implements the Supplier Performance Risk System (SPRS) scoring algorithm
for NIST 800-171 compliance assessment.

SPRS Score Range: -203 to 110

Scoring Rules:
- Base Score: 110 points (assumes all controls are met)
- Met: 0 deduction
- Partially Met: -1 point
- Not Met (with POA&M): -1 point
- Not Met (without POA&M): -3 points
- Not Assessed: -1 point
- Not Applicable: 0 deduction

Control Families (NIST 800-171):
- AC: Access Control
- AU: Audit and Accountability
- AT: Awareness and Training
- CM: Configuration Management
- IA: Identification and Authentication
- IR: Incident Response
- MA: Maintenance
- MP: Media Protection
- PS: Personnel Security
- PE: Physical Protection
- RA: Risk Assessment
- CA: Security Assessment
- SC: System and Communications Protection
- SI: System and Information Integrity
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncpg
import logging

logger = logging.getLogger(__name__)

# Control family mapping
CONTROL_FAMILIES = {
    'AC': 'Access Control',
    'AU': 'Audit and Accountability',
    'AT': 'Awareness and Training',
    'CM': 'Configuration Management',
    'IA': 'Identification and Authentication',
    'IR': 'Incident Response',
    'MA': 'Maintenance',
    'MP': 'Media Protection',
    'PS': 'Personnel Security',
    'PE': 'Physical Protection',
    'RA': 'Risk Assessment',
    'CA': 'Security Assessment',
    'SC': 'System and Communications Protection',
    'SI': 'System and Information Integrity'
}

# SPRS scoring weights
SCORE_WEIGHTS = {
    'Met': 0,
    'Partially Met': -1,
    'Not Met': -3,  # Without POA&M
    'Not Met (with POA&M)': -1,
    'Not Assessed': -1,
    'Not Applicable': 0
}

BASE_SCORE = 110


async def calculate_sprs_score(
    assessment_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Calculate SPRS score for an assessment based on control findings.

    Args:
        assessment_id: UUID of the assessment
        conn: Database connection

    Returns:
        Dictionary containing:
        - score: Overall SPRS score (-203 to 110)
        - total_controls: Total number of controls assessed
        - met_count: Number of controls met
        - partially_met_count: Number of controls partially met
        - not_met_count: Number of controls not met
        - not_assessed_count: Number of controls not assessed
        - not_applicable_count: Number of controls not applicable
        - family_breakdown: Scores by control family
        - control_details: Individual control scores
    """
    logger.info(f"Calculating SPRS score for assessment {assessment_id}")

    # Get all control findings for this assessment
    findings = await conn.fetch(
        """
        SELECT
            cf.control_id,
            cf.status,
            c.family,
            c.title,
            EXISTS(
                SELECT 1 FROM poam_items p
                WHERE p.finding_id = cf.id AND p.status != 'completed'
            ) as has_active_poam
        FROM control_findings cf
        JOIN controls c ON cf.control_id = c.id
        WHERE cf.assessment_id = $1
        ORDER BY cf.control_id
        """,
        assessment_id
    )

    # Get total number of controls in NIST 800-171 (should be 110)
    total_controls_in_framework = await conn.fetchval(
        "SELECT COUNT(*) FROM controls WHERE framework = 'NIST 800-171'"
    )

    if not findings:
        logger.warning(f"No findings found for assessment {assessment_id}")
        # If no findings, all controls are "Not Assessed"
        score = BASE_SCORE - (total_controls_in_framework * SCORE_WEIGHTS['Not Assessed'])
        return {
            'score': score,
            'total_controls': total_controls_in_framework or 110,
            'met_count': 0,
            'partially_met_count': 0,
            'not_met_count': 0,
            'not_assessed_count': total_controls_in_framework or 110,
            'not_applicable_count': 0,
            'family_breakdown': {},
            'control_details': []
        }

    # Initialize counters
    score = BASE_SCORE
    met_count = 0
    partially_met_count = 0
    not_met_count = 0
    not_assessed_count = 0
    not_applicable_count = 0

    # Family-level tracking
    family_scores = {}
    for family_code, family_name in CONTROL_FAMILIES.items():
        family_scores[family_code] = {
            'name': family_name,
            'score': 0,
            'total_controls': 0,
            'met': 0,
            'partially_met': 0,
            'not_met': 0,
            'not_assessed': 0,
            'not_applicable': 0
        }

    control_details = []

    # Process each finding
    for finding in findings:
        control_id = finding['control_id']
        status = finding['status']
        family = finding['family']
        title = finding['title']
        has_poam = finding['has_active_poam']

        # Determine score impact
        if status == 'Met':
            deduction = SCORE_WEIGHTS['Met']
            met_count += 1
            if family in family_scores:
                family_scores[family]['met'] += 1
        elif status == 'Partially Met':
            deduction = SCORE_WEIGHTS['Partially Met']
            partially_met_count += 1
            if family in family_scores:
                family_scores[family]['partially_met'] += 1
        elif status == 'Not Met':
            if has_poam:
                deduction = SCORE_WEIGHTS['Not Met (with POA&M)']
            else:
                deduction = SCORE_WEIGHTS['Not Met']
            not_met_count += 1
            if family in family_scores:
                family_scores[family]['not_met'] += 1
        elif status == 'Not Applicable':
            deduction = SCORE_WEIGHTS['Not Applicable']
            not_applicable_count += 1
            if family in family_scores:
                family_scores[family]['not_applicable'] += 1
        else:  # 'Not Assessed'
            deduction = SCORE_WEIGHTS['Not Assessed']
            not_assessed_count += 1
            if family in family_scores:
                family_scores[family]['not_assessed'] += 1

        score += deduction

        if family in family_scores:
            family_scores[family]['score'] += deduction
            family_scores[family]['total_controls'] += 1

        control_details.append({
            'control_id': control_id,
            'title': title,
            'status': status,
            'family': family,
            'deduction': deduction,
            'has_poam': has_poam
        })

    # Account for controls not yet assessed
    assessed_controls = len(findings)
    if assessed_controls < total_controls_in_framework:
        unassessed_controls = total_controls_in_framework - assessed_controls
        score += SCORE_WEIGHTS['Not Assessed'] * unassessed_controls
        not_assessed_count += unassessed_controls

    # Ensure score stays within bounds
    score = max(-203, min(110, score))

    logger.info(f"SPRS Score calculated: {score} for assessment {assessment_id}")

    return {
        'score': score,
        'total_controls': total_controls_in_framework or 110,
        'met_count': met_count,
        'partially_met_count': partially_met_count,
        'not_met_count': not_met_count,
        'not_assessed_count': not_assessed_count,
        'not_applicable_count': not_applicable_count,
        'family_breakdown': family_scores,
        'control_details': control_details,
        'calculation_date': datetime.utcnow().isoformat()
    }


async def save_sprs_score(
    assessment_id: str,
    score_data: Dict[str, Any],
    conn: asyncpg.Connection
) -> str:
    """
    Save SPRS score to database.

    Args:
        assessment_id: UUID of the assessment
        score_data: Score calculation results from calculate_sprs_score()
        conn: Database connection

    Returns:
        UUID of the created sprs_scores record
    """
    # Create details JSONB
    details = {
        'total_controls': score_data['total_controls'],
        'met_count': score_data['met_count'],
        'partially_met_count': score_data['partially_met_count'],
        'not_met_count': score_data['not_met_count'],
        'not_assessed_count': score_data['not_assessed_count'],
        'not_applicable_count': score_data['not_applicable_count'],
        'family_breakdown': score_data['family_breakdown'],
        'calculation_date': score_data['calculation_date']
    }

    # Insert into database
    score_id = await conn.fetchval(
        """
        INSERT INTO sprs_scores (assessment_id, score, details)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        assessment_id,
        score_data['score'],
        details
    )

    logger.info(f"SPRS score saved: {score_id} for assessment {assessment_id}")

    return score_id


async def get_sprs_score_history(
    assessment_id: str,
    conn: asyncpg.Connection
) -> List[Dict[str, Any]]:
    """
    Get historical SPRS scores for an assessment.

    Args:
        assessment_id: UUID of the assessment
        conn: Database connection

    Returns:
        List of historical scores with timestamps
    """
    scores = await conn.fetch(
        """
        SELECT id, score, calculation_date, details
        FROM sprs_scores
        WHERE assessment_id = $1
        ORDER BY calculation_date DESC
        """,
        assessment_id
    )

    return [
        {
            'id': str(score['id']),
            'score': score['score'],
            'calculation_date': score['calculation_date'].isoformat(),
            'details': score['details']
        }
        for score in scores
    ]


async def get_sprs_score_trend(
    assessment_id: str,
    conn: asyncpg.Connection
) -> Dict[str, Any]:
    """
    Get SPRS score trend analysis.

    Args:
        assessment_id: UUID of the assessment
        conn: Database connection

    Returns:
        Trend analysis including current score, previous score, and improvement rate
    """
    scores = await get_sprs_score_history(assessment_id, conn)

    if not scores:
        return {
            'current_score': None,
            'previous_score': None,
            'score_change': 0,
            'improvement_rate': 0,
            'trend': 'no_data'
        }

    current = scores[0]
    previous = scores[1] if len(scores) > 1 else None

    score_change = 0
    improvement_rate = 0.0
    trend = 'stable'

    if previous:
        score_change = current['score'] - previous['score']
        if previous['score'] != 0:
            improvement_rate = (score_change / abs(previous['score'])) * 100

        if score_change > 0:
            trend = 'improving'
        elif score_change < 0:
            trend = 'declining'

    return {
        'current_score': current['score'],
        'previous_score': previous['score'] if previous else None,
        'score_change': score_change,
        'improvement_rate': round(improvement_rate, 2),
        'trend': trend,
        'calculation_date': current['calculation_date'],
        'total_calculations': len(scores)
    }
