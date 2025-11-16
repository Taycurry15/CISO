"""
Assessment Scheduling System
============================
Comprehensive scheduling for assessments, meetings, and milestones.

Features:
- Assessment calendar management
- Assessor availability tracking
- Meeting scheduling (kickoff, interviews, closeout)
- Milestone tracking
- Automated reminders
- Resource allocation
- Conflict detection
- Integration with calendar systems (Google Calendar, Outlook)
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, date, time, timedelta
from pydantic import BaseModel, EmailStr
from enum import Enum
import asyncpg
import logging
import json

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Scheduled event types."""
    KICKOFF_MEETING = "kickoff_meeting"
    PLANNING_SESSION = "planning_session"
    INTERVIEW = "interview"
    EVIDENCE_REVIEW = "evidence_review"
    ONSITE_VISIT = "onsite_visit"
    CLOSEOUT_MEETING = "closeout_meeting"
    MILESTONE = "milestone"


class EventStatus(str, Enum):
    """Event status."""
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELED = "canceled"
    RESCHEDULED = "rescheduled"


class RecurrencePattern(str, Enum):
    """Recurrence patterns."""
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================

class ScheduleEventRequest(BaseModel):
    """Schedule event request."""
    assessment_id: str
    event_type: EventType
    title: str
    description: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    location: Optional[str] = None
    virtual_meeting_url: Optional[str] = None
    attendees: List[str]  # User IDs or emails
    reminder_minutes: int = 60  # Remind 60 minutes before


class UpdateEventRequest(BaseModel):
    """Update event request."""
    title: Optional[str] = None
    description: Optional[str] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    location: Optional[str] = None
    status: Optional[EventStatus] = None


class AssessorAvailability(BaseModel):
    """Assessor availability."""
    assessor_id: str
    date: date
    start_time: time
    end_time: time
    is_available: bool = True


class MilestoneRequest(BaseModel):
    """Milestone creation request."""
    assessment_id: str
    milestone_name: str
    target_date: date
    description: Optional[str] = None


# =============================================================================
# ASSESSMENT SCHEDULING SERVICE
# =============================================================================

class AssessmentSchedulingService:
    """Assessment scheduling service."""

    def __init__(self, conn: asyncpg.Connection):
        """Initialize scheduling service."""
        self.conn = conn

    # =========================================================================
    # EVENT SCHEDULING
    # =========================================================================

    async def schedule_event(
        self,
        request: ScheduleEventRequest,
        scheduled_by: str
    ) -> Dict[str, Any]:
        """
        Schedule an assessment event.

        Args:
            request: Event scheduling request
            scheduled_by: User scheduling the event

        Returns:
            Scheduled event details
        """
        # Verify assessment exists
        assessment = await self.conn.fetchval(
            "SELECT id FROM assessments WHERE id = $1",
            request.assessment_id
        )

        if not assessment:
            raise ValueError("Assessment not found")

        # Check for conflicts
        conflicts = await self._check_conflicts(
            request.attendees,
            request.start_datetime,
            request.end_datetime
        )

        if conflicts:
            logger.warning(f"Scheduling conflicts detected: {len(conflicts)} conflicts")

        # Create event
        event_id = await self.conn.fetchval(
            """
            INSERT INTO scheduled_events
            (assessment_id, event_type, title, description,
             start_datetime, end_datetime, location, virtual_meeting_url,
             scheduled_by, status, reminder_minutes)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 'scheduled', $10)
            RETURNING id
            """,
            request.assessment_id,
            request.event_type.value,
            request.title,
            request.description,
            request.start_datetime,
            request.end_datetime,
            request.location,
            request.virtual_meeting_url,
            scheduled_by,
            request.reminder_minutes
        )

        # Add attendees
        for attendee in request.attendees:
            await self.conn.execute(
                """
                INSERT INTO event_attendees
                (event_id, user_id, response_status)
                VALUES ($1, $2, 'pending')
                """,
                event_id,
                attendee
            )

        # Schedule reminder
        await self._schedule_reminder(
            event_id,
            request.start_datetime,
            request.reminder_minutes
        )

        logger.info(f"Event scheduled: {event_id}")

        # In production, send calendar invites

        return {
            "event_id": str(event_id),
            "assessment_id": request.assessment_id,
            "event_type": request.event_type.value,
            "title": request.title,
            "start_datetime": request.start_datetime.isoformat(),
            "end_datetime": request.end_datetime.isoformat(),
            "attendees_count": len(request.attendees),
            "conflicts": conflicts
        }

    async def _check_conflicts(
        self,
        attendees: List[str],
        start_datetime: datetime,
        end_datetime: datetime
    ) -> List[Dict[str, Any]]:
        """Check for scheduling conflicts."""
        conflicts = []

        for attendee_id in attendees:
            conflicting_events = await self.conn.fetch(
                """
                SELECT
                    se.id, se.title, se.start_datetime, se.end_datetime
                FROM scheduled_events se
                JOIN event_attendees ea ON se.id = ea.event_id
                WHERE ea.user_id = $1
                AND se.status NOT IN ('canceled', 'completed')
                AND (
                    (se.start_datetime <= $2 AND se.end_datetime >= $2)
                    OR (se.start_datetime <= $3 AND se.end_datetime >= $3)
                    OR (se.start_datetime >= $2 AND se.end_datetime <= $3)
                )
                """,
                attendee_id,
                start_datetime,
                end_datetime
            )

            for conflict in conflicting_events:
                conflicts.append({
                    "attendee_id": attendee_id,
                    "conflicting_event_id": str(conflict['id']),
                    "conflicting_event_title": conflict['title'],
                    "conflict_start": conflict['start_datetime'].isoformat(),
                    "conflict_end": conflict['end_datetime'].isoformat()
                })

        return conflicts

    async def _schedule_reminder(
        self,
        event_id: str,
        event_start: datetime,
        reminder_minutes: int
    ):
        """Schedule event reminder."""
        reminder_time = event_start - timedelta(minutes=reminder_minutes)

        await self.conn.execute(
            """
            INSERT INTO event_reminders
            (event_id, reminder_datetime, sent)
            VALUES ($1, $2, FALSE)
            """,
            event_id,
            reminder_time
        )

    async def get_event(
        self,
        event_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get event details."""
        event = await self.conn.fetchrow(
            """
            SELECT
                id, assessment_id, event_type, title, description,
                start_datetime, end_datetime, location, virtual_meeting_url,
                status, scheduled_by, created_at
            FROM scheduled_events
            WHERE id = $1
            """,
            event_id
        )

        if not event:
            return None

        # Get attendees
        attendees = await self.conn.fetch(
            """
            SELECT
                ea.user_id, ea.response_status,
                u.email, u.full_name
            FROM event_attendees ea
            LEFT JOIN users u ON ea.user_id = u.id
            WHERE ea.event_id = $1
            """,
            event_id
        )

        return {
            "id": str(event['id']),
            "assessment_id": str(event['assessment_id']),
            "event_type": event['event_type'],
            "title": event['title'],
            "description": event['description'],
            "start_datetime": event['start_datetime'].isoformat(),
            "end_datetime": event['end_datetime'].isoformat(),
            "location": event['location'],
            "virtual_meeting_url": event['virtual_meeting_url'],
            "status": event['status'],
            "attendees": [
                {
                    "user_id": str(attendee['user_id']),
                    "email": attendee['email'],
                    "full_name": attendee['full_name'],
                    "response_status": attendee['response_status']
                }
                for attendee in attendees
            ]
        }

    async def update_event(
        self,
        event_id: str,
        update: UpdateEventRequest,
        updated_by: str
    ) -> Dict[str, Any]:
        """Update scheduled event."""
        # Build update query
        updates = {}
        if update.title:
            updates['title'] = update.title
        if update.description:
            updates['description'] = update.description
        if update.start_datetime:
            updates['start_datetime'] = update.start_datetime
        if update.end_datetime:
            updates['end_datetime'] = update.end_datetime
        if update.location:
            updates['location'] = update.location
        if update.status:
            updates['status'] = update.status.value

        if not updates:
            return await self.get_event(event_id)

        set_clause = ', '.join([f"{k} = ${i+2}" for i, k in enumerate(updates.keys())])
        values = [event_id] + list(updates.values())

        await self.conn.execute(
            f"UPDATE scheduled_events SET {set_clause}, updated_at = NOW() WHERE id = $1",
            *values
        )

        logger.info(f"Event updated: {event_id}")

        # In production, send update notifications

        return await self.get_event(event_id)

    async def cancel_event(
        self,
        event_id: str,
        canceled_by: str,
        reason: Optional[str] = None
    ) -> bool:
        """Cancel scheduled event."""
        await self.conn.execute(
            """
            UPDATE scheduled_events
            SET status = 'canceled', updated_at = NOW()
            WHERE id = $1
            """,
            event_id
        )

        # Log cancellation
        await self.conn.execute(
            """
            INSERT INTO audit_log (table_name, operation, record_id, changed_by, changed_data)
            VALUES ('scheduled_events', 'CANCEL', $1, $2, $3)
            """,
            event_id,
            canceled_by,
            json.dumps({"reason": reason})
        )

        logger.info(f"Event canceled: {event_id}")

        # In production, send cancellation notifications

        return True

    # =========================================================================
    # CALENDAR VIEWS
    # =========================================================================

    async def get_assessment_calendar(
        self,
        assessment_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get calendar view for assessment."""
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = start_date + timedelta(days=90)

        events = await self.conn.fetch(
            """
            SELECT
                id, event_type, title, start_datetime, end_datetime,
                location, virtual_meeting_url, status
            FROM scheduled_events
            WHERE assessment_id = $1
            AND start_datetime::date BETWEEN $2 AND $3
            ORDER BY start_datetime ASC
            """,
            assessment_id,
            start_date,
            end_date
        )

        return [
            {
                "id": str(event['id']),
                "event_type": event['event_type'],
                "title": event['title'],
                "start": event['start_datetime'].isoformat(),
                "end": event['end_datetime'].isoformat(),
                "location": event['location'],
                "virtual_url": event['virtual_meeting_url'],
                "status": event['status']
            }
            for event in events
        ]

    async def get_user_calendar(
        self,
        user_id: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Get calendar view for user."""
        if not start_date:
            start_date = date.today()
        if not end_date:
            end_date = start_date + timedelta(days=30)

        events = await self.conn.fetch(
            """
            SELECT
                se.id, se.assessment_id, se.event_type, se.title,
                se.start_datetime, se.end_datetime,
                se.location, se.virtual_meeting_url, se.status,
                ea.response_status
            FROM scheduled_events se
            JOIN event_attendees ea ON se.id = ea.event_id
            WHERE ea.user_id = $1
            AND se.start_datetime::date BETWEEN $2 AND $3
            AND se.status NOT IN ('canceled')
            ORDER BY se.start_datetime ASC
            """,
            user_id,
            start_date,
            end_date
        )

        return [
            {
                "id": str(event['id']),
                "assessment_id": str(event['assessment_id']),
                "event_type": event['event_type'],
                "title": event['title'],
                "start": event['start_datetime'].isoformat(),
                "end": event['end_datetime'].isoformat(),
                "location": event['location'],
                "virtual_url": event['virtual_meeting_url'],
                "status": event['status'],
                "my_response": event['response_status']
            }
            for event in events
        ]

    # =========================================================================
    # ASSESSOR AVAILABILITY
    # =========================================================================

    async def set_availability(
        self,
        availability: AssessorAvailability
    ) -> Dict[str, Any]:
        """Set assessor availability."""
        availability_id = await self.conn.fetchval(
            """
            INSERT INTO assessor_availability
            (assessor_id, availability_date, start_time, end_time, is_available)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (assessor_id, availability_date)
            DO UPDATE SET
                start_time = $3,
                end_time = $4,
                is_available = $5,
                updated_at = NOW()
            RETURNING id
            """,
            availability.assessor_id,
            availability.date,
            availability.start_time,
            availability.end_time,
            availability.is_available
        )

        return {
            "availability_id": str(availability_id),
            "assessor_id": availability.assessor_id,
            "date": availability.date.isoformat(),
            "available": availability.is_available
        }

    async def get_available_assessors(
        self,
        date: date,
        start_time: time,
        end_time: time
    ) -> List[Dict[str, Any]]:
        """Get available assessors for a time slot."""
        assessors = await self.conn.fetch(
            """
            SELECT
                aa.assessor_id,
                u.email, u.full_name,
                aa.start_time, aa.end_time
            FROM assessor_availability aa
            JOIN users u ON aa.assessor_id = u.id
            WHERE aa.availability_date = $1
            AND aa.is_available = TRUE
            AND aa.start_time <= $2
            AND aa.end_time >= $3
            AND NOT EXISTS (
                SELECT 1 FROM scheduled_events se
                JOIN event_attendees ea ON se.id = ea.event_id
                WHERE ea.user_id = aa.assessor_id
                AND se.start_datetime::date = $1
                AND se.status NOT IN ('canceled', 'completed')
                AND (
                    (se.start_datetime::time <= $2 AND se.end_datetime::time >= $2)
                    OR (se.start_datetime::time <= $3 AND se.end_datetime::time >= $3)
                )
            )
            """,
            date,
            start_time,
            end_time
        )

        return [
            {
                "assessor_id": str(assessor['assessor_id']),
                "email": assessor['email'],
                "full_name": assessor['full_name'],
                "available_from": assessor['start_time'].isoformat(),
                "available_until": assessor['end_time'].isoformat()
            }
            for assessor in assessors
        ]

    # =========================================================================
    # MILESTONES
    # =========================================================================

    async def create_milestone(
        self,
        request: MilestoneRequest,
        created_by: str
    ) -> Dict[str, Any]:
        """Create assessment milestone."""
        milestone_id = await self.conn.fetchval(
            """
            INSERT INTO assessment_milestones
            (assessment_id, milestone_name, target_date, description, status, created_by)
            VALUES ($1, $2, $3, $4, 'pending', $5)
            RETURNING id
            """,
            request.assessment_id,
            request.milestone_name,
            request.target_date,
            request.description,
            created_by
        )

        logger.info(f"Milestone created: {milestone_id}")

        return {
            "milestone_id": str(milestone_id),
            "assessment_id": request.assessment_id,
            "milestone_name": request.milestone_name,
            "target_date": request.target_date.isoformat(),
            "status": "pending"
        }

    async def complete_milestone(
        self,
        milestone_id: str,
        completed_by: str
    ) -> Dict[str, Any]:
        """Mark milestone as complete."""
        await self.conn.execute(
            """
            UPDATE assessment_milestones
            SET status = 'completed', completed_date = NOW(), completed_by = $1
            WHERE id = $2
            """,
            completed_by,
            milestone_id
        )

        logger.info(f"Milestone completed: {milestone_id}")

        return {
            "milestone_id": milestone_id,
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat()
        }

    async def get_milestones(
        self,
        assessment_id: str
    ) -> List[Dict[str, Any]]:
        """Get all milestones for assessment."""
        milestones = await self.conn.fetch(
            """
            SELECT
                id, milestone_name, target_date, description,
                status, completed_date, created_at
            FROM assessment_milestones
            WHERE assessment_id = $1
            ORDER BY target_date ASC
            """,
            assessment_id
        )

        return [
            {
                "id": str(milestone['id']),
                "milestone_name": milestone['milestone_name'],
                "target_date": milestone['target_date'].isoformat(),
                "description": milestone['description'],
                "status": milestone['status'],
                "completed_date": milestone['completed_date'].isoformat() if milestone['completed_date'] else None,
                "created_at": milestone['created_at'].isoformat()
            }
            for milestone in milestones
        ]
