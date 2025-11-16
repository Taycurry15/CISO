# CMMC Compliance Platform - API Endpoint Reference

**Version**: 1.0
**Base URL**: `https://api.cmmc-platform.example.com/api/v1`
**Authentication**: Bearer Token (JWT) or API Key

---

## Table of Contents

1. [Authentication & User Management](#authentication--user-management)
2. [Organization Onboarding](#organization-onboarding)
3. [Customer Portal](#customer-portal)
4. [Billing & Subscriptions](#billing--subscriptions)
5. [White-Labeling](#white-labeling)
6. [C3PAO Workflow](#c3pao-workflow)
7. [Assessment Scheduling](#assessment-scheduling)
8. [SPRS Calculator](#sprs-calculator)
9. [Monitoring Dashboard](#monitoring-dashboard)
10. [Assessments & Controls](#assessments--controls)
11. [Evidence Management](#evidence-management)
12. [POA&M Management](#poam-management)
13. [SSP Generation](#ssp-generation)
14. [Integrations](#integrations)

---

## Authentication & User Management

### Login
```http
POST /api/v1/auth/login
```
**Description**: Authenticate user and receive JWT token
**Auth Required**: No
**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```
**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "full_name": "John Doe",
    "role": "admin",
    "organization_id": "org-uuid"
  }
}
```

### Register User
```http
POST /api/v1/auth/register
```
**Description**: Create new user account
**Auth Required**: Admin
**Request Body**:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePassword123!",
  "full_name": "Jane Smith",
  "role": "assessor",
  "organization_id": "org-uuid"
}
```

### Create API Key
```http
POST /api/v1/auth/api-keys
```
**Description**: Generate API key for programmatic access
**Auth Required**: Admin
**Request Body**:
```json
{
  "name": "Integration API Key",
  "expires_days": 365
}
```

### Get Current User
```http
GET /api/v1/auth/me
```
**Description**: Get authenticated user details
**Auth Required**: Yes

---

## Organization Onboarding

### Start Onboarding
```http
POST /api/v1/onboarding/start
```
**Description**: Initiate new organization onboarding workflow
**Auth Required**: No
**Request Body**:
```json
{
  "organization_name": "Acme Defense Corp",
  "organization_type": "defense_prime",
  "admin_email": "admin@acme.com",
  "admin_name": "John Smith",
  "admin_password": "SecurePass123!",
  "cmmc_level": 2,
  "enable_integrations": true,
  "integration_types": ["splunk", "azure"]
}
```

### Get Onboarding Status
```http
GET /api/v1/onboarding/{onboarding_id}/status
```
**Description**: Check onboarding workflow progress
**Auth Required**: Yes

---

## Customer Portal

### Get Organization Profile
```http
GET /api/v1/portal/organization
```
**Description**: Retrieve organization profile details
**Auth Required**: Yes

### Update Organization Profile
```http
PUT /api/v1/portal/organization
```
**Description**: Update organization information
**Auth Required**: Admin
**Request Body**:
```json
{
  "name": "Acme Defense Corp",
  "industry": "aerospace",
  "organization_type": "defense_prime",
  "address": "123 Defense Way, Arlington, VA 22201",
  "phone": "+1-555-0100",
  "contact_email": "contact@acme.com"
}
```

### Get Team Members
```http
GET /api/v1/portal/team
```
**Description**: List all team members
**Auth Required**: Yes

### Invite Team Member
```http
POST /api/v1/portal/team/invite
```
**Description**: Send invitation to new team member
**Auth Required**: Admin
**Request Body**:
```json
{
  "email": "newmember@acme.com",
  "full_name": "Alice Johnson",
  "role": "assessor"
}
```

### Remove Team Member
```http
DELETE /api/v1/portal/team/{user_id}
```
**Description**: Remove team member from organization
**Auth Required**: Admin

### Create Assessment
```http
POST /api/v1/portal/assessments
```
**Description**: Create new self-service assessment
**Auth Required**: Yes
**Request Body**:
```json
{
  "name": "Q1 2025 CMMC Assessment",
  "cmmc_level": 2,
  "assessment_type": "self",
  "target_completion_date": "2025-03-31"
}
```

### List Assessments
```http
GET /api/v1/portal/assessments
```
**Description**: Get all assessments for organization
**Auth Required**: Yes
**Query Parameters**:
- `status`: Filter by status (in_progress, completed)
- `limit`: Number of results (default: 50)

### Get Notification Preferences
```http
GET /api/v1/portal/preferences
```
**Description**: Retrieve notification settings
**Auth Required**: Yes

### Update Notification Preferences
```http
PUT /api/v1/portal/preferences
```
**Description**: Update notification settings
**Auth Required**: Yes
**Request Body**:
```json
{
  "email_notifications": true,
  "notification_types": ["evidence_due", "poam_overdue", "assessment_complete"],
  "digest_frequency": "daily"
}
```

### Generate Report
```http
POST /api/v1/portal/reports/generate
```
**Description**: Request report generation
**Auth Required**: Yes
**Request Body**:
```json
{
  "assessment_id": "assessment-uuid",
  "report_type": "ssp",
  "format": "pdf"
}
```

### Get Activity History
```http
GET /api/v1/portal/activity
```
**Description**: Retrieve organization activity feed
**Auth Required**: Yes
**Query Parameters**:
- `limit`: Number of results (default: 50)
- `offset`: Pagination offset

---

## Billing & Subscriptions

### Create Subscription
```http
POST /api/v1/billing/subscriptions
```
**Description**: Start new subscription
**Auth Required**: Admin
**Request Body**:
```json
{
  "plan": "professional",
  "billing_interval": "annual",
  "payment_method_id": "pm_stripe_id",
  "trial_days": 14
}
```

### Get Subscription
```http
GET /api/v1/billing/subscription
```
**Description**: Get current subscription details
**Auth Required**: Yes
**Response**:
```json
{
  "id": "sub-uuid",
  "plan": "professional",
  "plan_name": "Professional",
  "billing_interval": "annual",
  "status": "active",
  "price": 7990.00,
  "current_period_end": "2026-01-15T00:00:00Z",
  "features": ["5 active assessments", "Up to 25 users", "API access"],
  "limits": {
    "assessments": 5,
    "users": 25,
    "max_cmmc_level": 3
  },
  "usage": {
    "assessments": 2,
    "users": 8,
    "storage_gb": 12.5
  }
}
```

### Update Subscription
```http
PUT /api/v1/billing/subscription
```
**Description**: Upgrade/downgrade subscription
**Auth Required**: Admin
**Request Body**:
```json
{
  "plan": "enterprise",
  "billing_interval": "annual"
}
```

### Cancel Subscription
```http
DELETE /api/v1/billing/subscription
```
**Description**: Cancel subscription
**Auth Required**: Admin
**Query Parameters**:
- `immediate`: true/false (cancel now vs. end of period)

### Get Invoices
```http
GET /api/v1/billing/invoices
```
**Description**: List billing invoices
**Auth Required**: Admin
**Query Parameters**:
- `limit`: Number of results (default: 12)

### Stripe Webhook
```http
POST /api/v1/billing/webhook
```
**Description**: Handle Stripe webhook events
**Auth Required**: No (Stripe signature verification)

---

## White-Labeling

### Get Branding
```http
GET /api/v1/white-label/branding
```
**Description**: Retrieve white-label branding configuration
**Auth Required**: Yes

### Update Branding
```http
PUT /api/v1/white-label/branding
```
**Description**: Configure white-label branding
**Auth Required**: Admin
**Requirements**: Professional or Enterprise plan
**Request Body**:
```json
{
  "company_name": "SecureComp Solutions",
  "logo_url": "https://cdn.example.com/logo.png",
  "favicon_url": "https://cdn.example.com/favicon.ico",
  "colors": {
    "primary": "#0066cc",
    "secondary": "#00cc66",
    "accent": "#ff9900",
    "background": "#ffffff",
    "text": "#333333",
    "text_secondary": "#666666"
  },
  "custom_domain": "compliance.securecomp.com",
  "support_email": "support@securecomp.com"
}
```

### Get Email Templates
```http
GET /api/v1/white-label/email-templates
```
**Description**: Retrieve custom email templates
**Auth Required**: Yes

### Update Email Templates
```http
PUT /api/v1/white-label/email-templates
```
**Description**: Configure custom email templates
**Auth Required**: Admin
**Request Body**:
```json
{
  "header_logo_url": "https://cdn.example.com/email-logo.png",
  "footer_text": "© 2025 SecureComp Solutions",
  "signature": "SecureComp Compliance Team",
  "from_name": "SecureComp Compliance",
  "from_email": "compliance@securecomp.com"
}
```

### Get Terminology
```http
GET /api/v1/white-label/terminology
```
**Description**: Retrieve custom terminology
**Auth Required**: Yes

### Update Terminology
```http
PUT /api/v1/white-label/terminology
```
**Description**: Configure custom terminology
**Auth Required**: Admin
**Request Body**:
```json
{
  "assessment_singular": "Audit",
  "assessment_plural": "Audits",
  "control_singular": "Requirement",
  "control_plural": "Requirements"
}
```

### Get Custom CSS
```http
GET /api/v1/white-label/custom.css
```
**Description**: Get dynamically generated CSS for white-label portal
**Auth Required**: No (public endpoint)
**Query Parameters**:
- `org_id`: Organization UUID

---

## C3PAO Workflow

### Register C3PAO
```http
POST /api/v1/c3pao/register
```
**Description**: Register C3PAO organization
**Auth Required**: Admin
**Request Body**:
```json
{
  "organization_name": "CyberAssess C3PAO",
  "certification_number": "C3PAO-2024-001",
  "accreditation_body": "CMMC-AB",
  "contact_email": "info@cyberassess.com",
  "contact_phone": "+1-555-0200",
  "lead_assessor_name": "Dr. Sarah Chen",
  "lead_assessor_email": "schen@cyberassess.com"
}
```

### Get C3PAO Details
```http
GET /api/v1/c3pao/{c3pao_id}
```
**Description**: Retrieve C3PAO organization details
**Auth Required**: Yes

### Assign Assessment to C3PAO
```http
POST /api/v1/c3pao/assessments/assign
```
**Description**: Assign client assessment to C3PAO
**Auth Required**: Admin
**Request Body**:
```json
{
  "client_organization_id": "client-org-uuid",
  "assessment_id": "assessment-uuid",
  "c3pao_organization_id": "c3pao-uuid",
  "lead_assessor_id": "assessor-uuid",
  "planned_start_date": "2025-02-01",
  "planned_end_date": "2025-04-30",
  "scope_notes": "CMMC Level 2 certification assessment"
}
```

### Update Assessment Phase
```http
PUT /api/v1/c3pao/assessments/{c3pao_assessment_id}/phase
```
**Description**: Advance assessment to next phase
**Auth Required**: C3PAO Assessor
**Request Body**:
```json
{
  "phase": "evidence_review",
  "notes": "Planning complete, proceeding to evidence review"
}
```
**Phases**: scoping → planning → evidence_review → onsite_assessment → finding_validation → report_writing → report_review → final_approval → completed

### Review Finding
```http
POST /api/v1/c3pao/findings/review
```
**Description**: C3PAO assessor review of finding
**Auth Required**: C3PAO Assessor
**Request Body**:
```json
{
  "finding_id": "finding-uuid",
  "validation_status": "approved",
  "assessor_comments": "Evidence is sufficient and control is properly implemented",
  "evidence_sufficiency": true,
  "remediation_required": false
}
```

### Get Findings for Review
```http
GET /api/v1/c3pao/assessments/{c3pao_assessment_id}/findings
```
**Description**: List findings pending C3PAO review
**Auth Required**: C3PAO Assessor
**Query Parameters**:
- `status`: Filter by finding status

### Generate Assessment Report
```http
POST /api/v1/c3pao/assessments/{c3pao_assessment_id}/report
```
**Description**: Generate C3PAO assessment report
**Auth Required**: C3PAO Lead Assessor
**Request Body**:
```json
{
  "report_type": "final"
}
```

### Approve Report
```http
POST /api/v1/c3pao/reports/{report_id}/approve
```
**Description**: Approve final assessment report
**Auth Required**: C3PAO Quality Reviewer

### Send Client Update
```http
POST /api/v1/c3pao/assessments/{c3pao_assessment_id}/communicate
```
**Description**: Send update to client organization
**Auth Required**: C3PAO Assessor
**Request Body**:
```json
{
  "subject": "Assessment Progress Update",
  "message": "We have completed the evidence review phase..."
}
```

---

## Assessment Scheduling

### Schedule Event
```http
POST /api/v1/scheduling/events
```
**Description**: Schedule assessment event
**Auth Required**: Assessor
**Request Body**:
```json
{
  "assessment_id": "assessment-uuid",
  "event_type": "interview",
  "title": "IT Manager Interview - Access Control",
  "description": "Interview regarding access control procedures",
  "start_time": "2025-02-15T14:00:00Z",
  "end_time": "2025-02-15T15:30:00Z",
  "location": "Virtual (Zoom)",
  "attendees": [
    {
      "user_id": "user-uuid-1",
      "required": true
    }
  ],
  "send_reminders": true
}
```
**Event Types**: kickoff_meeting, planning_session, interview, evidence_review, onsite_visit, closeout_meeting, milestone

### Get Event
```http
GET /api/v1/scheduling/events/{event_id}
```
**Description**: Retrieve event details
**Auth Required**: Yes

### Update Event
```http
PUT /api/v1/scheduling/events/{event_id}
```
**Description**: Update scheduled event
**Auth Required**: Event creator or Admin

### Delete Event
```http
DELETE /api/v1/scheduling/events/{event_id}
```
**Description**: Cancel scheduled event
**Auth Required**: Event creator or Admin

### Get Assessment Calendar
```http
GET /api/v1/scheduling/calendar/assessment/{assessment_id}
```
**Description**: View all events for an assessment
**Auth Required**: Yes
**Query Parameters**:
- `start_date`: Filter start (ISO 8601)
- `end_date`: Filter end (ISO 8601)

### Get My Calendar
```http
GET /api/v1/scheduling/calendar/my
```
**Description**: View personal calendar (all assessments)
**Auth Required**: Yes
**Query Parameters**:
- `start_date`: Filter start (ISO 8601)
- `end_date`: Filter end (ISO 8601)

### Set Assessor Availability
```http
POST /api/v1/scheduling/availability
```
**Description**: Set availability for scheduling
**Auth Required**: Assessor
**Request Body**:
```json
{
  "start_time": "2025-02-15T09:00:00Z",
  "end_time": "2025-02-15T17:00:00Z",
  "available": true,
  "notes": "Available all day except lunch (12-1pm)"
}
```

### Get Available Assessors
```http
GET /api/v1/scheduling/availability/available
```
**Description**: Find available assessors for time range
**Auth Required**: Yes
**Query Parameters**:
- `start_time`: Required (ISO 8601)
- `end_time`: Required (ISO 8601)
- `assessment_id`: Optional filter

### Create Milestone
```http
POST /api/v1/scheduling/milestones
```
**Description**: Create assessment milestone
**Auth Required**: Admin
**Request Body**:
```json
{
  "assessment_id": "assessment-uuid",
  "milestone_name": "Evidence Collection Complete",
  "target_date": "2025-03-15",
  "description": "All evidence artifacts collected and uploaded"
}
```

### Complete Milestone
```http
POST /api/v1/scheduling/milestones/{milestone_id}/complete
```
**Description**: Mark milestone as completed
**Auth Required**: Assessor

### Get Assessment Milestones
```http
GET /api/v1/scheduling/milestones/assessment/{assessment_id}
```
**Description**: List all milestones for assessment
**Auth Required**: Yes

---

## SPRS Calculator

### Calculate SPRS Score
```http
POST /api/v1/sprs/calculate/{assessment_id}
```
**Description**: Calculate NIST 800-171 SPRS score
**Auth Required**: Yes
**Response**:
```json
{
  "assessment_id": "assessment-uuid",
  "total_score": 98,
  "base_score": 110,
  "deductions": -12,
  "breakdown": {
    "AC": {"score": 3, "total_controls": 22, "met": 20, "not_met": 2},
    "AT": {"score": 0, "total_controls": 6, "met": 6, "not_met": 0}
  },
  "calculated_at": "2025-01-15T10:30:00Z"
}
```

### Get SPRS History
```http
GET /api/v1/sprs/history/{assessment_id}
```
**Description**: Get historical SPRS scores
**Auth Required**: Yes
**Query Parameters**:
- `limit`: Number of results (default: 10)

### Get SPRS Trend
```http
GET /api/v1/sprs/trend/{assessment_id}
```
**Description**: Analyze SPRS score trend
**Auth Required**: Yes
**Response**:
```json
{
  "trend": "improving",
  "change": 5,
  "current_score": 98,
  "previous_score": 93,
  "percentage_change": 5.4
}
```

---

## Monitoring Dashboard

### Get Dashboard Summary
```http
GET /api/v1/monitoring/dashboard/{organization_id}
```
**Description**: High-level organization compliance metrics
**Auth Required**: Yes
**Response**:
```json
{
  "organization_id": "org-uuid",
  "active_assessments": 3,
  "total_controls": 330,
  "compliant_controls": 280,
  "non_compliant_controls": 35,
  "compliance_percentage": 84.8,
  "active_poams": 12,
  "overdue_poams": 2,
  "active_integrations": 4,
  "recent_alerts": 3,
  "last_sync": "2025-01-15T10:00:00Z"
}
```

### Get Control Compliance Overview
```http
GET /api/v1/monitoring/compliance/{assessment_id}
```
**Description**: Detailed control compliance breakdown by family
**Auth Required**: Yes

### Get Recent Activity
```http
GET /api/v1/monitoring/activity/{organization_id}
```
**Description**: Audit trail of recent actions
**Auth Required**: Yes
**Query Parameters**:
- `limit`: Number of results (default: 50)

### Get Integration Status
```http
GET /api/v1/monitoring/integrations/{organization_id}
```
**Description**: Health status of all integrations
**Auth Required**: Yes

### Get Risk Metrics
```http
GET /api/v1/monitoring/risk/{assessment_id}
```
**Description**: Risk distribution and scoring
**Auth Required**: Yes

### Get Recent Alerts
```http
GET /api/v1/monitoring/alerts/{organization_id}
```
**Description**: Active compliance alerts
**Auth Required**: Yes
**Query Parameters**:
- `severity`: Filter by severity (high, medium, low)
- `limit`: Number of results (default: 20)

---

## Assessments & Controls

### Create Assessment
```http
POST /api/v1/assessments
```
**Description**: Create new CMMC assessment
**Auth Required**: Admin
**Request Body**:
```json
{
  "name": "Q1 2025 CMMC Level 2 Assessment",
  "organization_id": "org-uuid",
  "cmmc_level": 2,
  "assessment_type": "self",
  "target_date": "2025-03-31"
}
```

### Get Assessment
```http
GET /api/v1/assessments/{assessment_id}
```
**Description**: Retrieve assessment details
**Auth Required**: Yes

### List Assessments
```http
GET /api/v1/assessments
```
**Description**: List all assessments for organization
**Auth Required**: Yes
**Query Parameters**:
- `organization_id`: Required
- `status`: Filter by status
- `cmmc_level`: Filter by CMMC level

### Get Controls
```http
GET /api/v1/controls
```
**Description**: List CMMC controls
**Auth Required**: Yes
**Query Parameters**:
- `cmmc_level`: Filter by level (1, 2, 3)
- `family`: Filter by family (AC, AT, AU, etc.)

### Update Control Status
```http
PUT /api/v1/controls/{control_id}/status
```
**Description**: Update control implementation status
**Auth Required**: Assessor
**Request Body**:
```json
{
  "assessment_id": "assessment-uuid",
  "status": "Met",
  "assessor_narrative": "Control is properly implemented with documented procedures",
  "implementation_details": "Access control policy documented and enforced via Active Directory"
}
```

---

## Evidence Management

### Upload Evidence
```http
POST /api/v1/evidence/upload
```
**Description**: Upload evidence artifact
**Auth Required**: Yes
**Content-Type**: multipart/form-data
**Request Body**:
- `file`: File upload
- `assessment_id`: Assessment UUID
- `control_id`: Control ID
- `evidence_type`: document, screenshot, log, policy, etc.
- `description`: Evidence description

### List Evidence
```http
GET /api/v1/evidence
```
**Description**: List evidence for assessment/control
**Auth Required**: Yes
**Query Parameters**:
- `assessment_id`: Required
- `control_id`: Optional filter

### Download Evidence
```http
GET /api/v1/evidence/{evidence_id}/download
```
**Description**: Download evidence file
**Auth Required**: Yes

### Delete Evidence
```http
DELETE /api/v1/evidence/{evidence_id}
```
**Description**: Delete evidence artifact
**Auth Required**: Admin or evidence uploader

---

## POA&M Management

### Create POA&M
```http
POST /api/v1/poams
```
**Description**: Create Plan of Action & Milestones
**Auth Required**: Assessor
**Request Body**:
```json
{
  "assessment_id": "assessment-uuid",
  "control_id": "AC.L2-3.1.1",
  "weakness_description": "MFA not enabled for all users",
  "remediation_plan": "Enable MFA for all users via Azure AD",
  "resources_required": "Azure AD Premium licenses",
  "scheduled_completion_date": "2025-02-28",
  "milestones": [
    {
      "description": "Procure Azure AD licenses",
      "target_date": "2025-02-07"
    },
    {
      "description": "Configure MFA policies",
      "target_date": "2025-02-14"
    }
  ]
}
```

### Update POA&M
```http
PUT /api/v1/poams/{poam_id}
```
**Description**: Update POA&M details
**Auth Required**: Assessor

### Complete POA&M
```http
POST /api/v1/poams/{poam_id}/complete
```
**Description**: Mark POA&M as completed
**Auth Required**: Assessor
**Request Body**:
```json
{
  "completion_notes": "MFA successfully enabled for all 250 users",
  "verification_evidence_id": "evidence-uuid"
}
```

### List POA&Ms
```http
GET /api/v1/poams
```
**Description**: List POA&Ms
**Auth Required**: Yes
**Query Parameters**:
- `assessment_id`: Required
- `status`: Filter by status (open, in_progress, completed)
- `overdue`: true/false

---

## SSP Generation

### Generate SSP
```http
POST /api/v1/ssp/generate/{assessment_id}
```
**Description**: Generate System Security Plan
**Auth Required**: Admin
**Request Body**:
```json
{
  "format": "docx",
  "include_poams": true,
  "include_evidence_summary": true
}
```

### Download SSP
```http
GET /api/v1/ssp/{ssp_id}/download
```
**Description**: Download generated SSP
**Auth Required**: Yes

---

## Integrations

### Configure Integration
```http
POST /api/v1/integrations/configure
```
**Description**: Configure external integration
**Auth Required**: Admin
**Request Body**:
```json
{
  "integration_type": "splunk",
  "config": {
    "hec_url": "https://splunk.example.com:8088/services/collector",
    "hec_token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "index": "cmmc_compliance"
  }
}
```

### Sync Integration
```http
POST /api/v1/integrations/{integration_id}/sync
```
**Description**: Trigger manual sync
**Auth Required**: Integration role or Admin

### Get Integration Status
```http
GET /api/v1/integrations/{integration_id}/status
```
**Description**: Check integration health
**Auth Required**: Yes

---

## Error Responses

All endpoints return standard error responses:

### 400 Bad Request
```json
{
  "detail": "Validation error: email is required"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 429 Too Many Requests
```json
{
  "detail": "Rate limit exceeded"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Rate Limiting

- **Authenticated requests**: 1000 requests/hour
- **Unauthenticated requests**: 60 requests/hour
- **File uploads**: 100 requests/hour

---

## Pagination

Endpoints that return lists support pagination:

**Query Parameters**:
- `limit`: Number of results (default: 50, max: 100)
- `offset`: Number of results to skip (default: 0)

**Response Format**:
```json
{
  "total": 150,
  "limit": 50,
  "offset": 0,
  "data": [...]
}
```

---

## Webhook Events

For real-time updates, configure webhooks:

**Available Events**:
- `assessment.created`
- `assessment.completed`
- `control.status_updated`
- `evidence.uploaded`
- `poam.created`
- `poam.overdue`
- `ssp.generated`
- `integration.sync_completed`
- `integration.sync_failed`

---

## Support

**API Documentation**: https://docs.cmmc-platform.example.com
**Support Email**: api-support@cmmc-platform.example.com
**Status Page**: https://status.cmmc-platform.example.com
