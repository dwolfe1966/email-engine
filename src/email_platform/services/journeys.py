from datetime import datetime, timedelta
from typing import cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session, selectinload

from email_platform.models.entities import (
    Campaign,
    CampaignSendJob,
    Contact,
    EmailSendRecord,
    EmailSendStatus,
    Journey,
    JourneyEnrollment,
    JourneyEnrollmentStatus,
    JourneyStep,
    JourneyStepExecution,
    JourneyStepExecutionStatus,
    JourneyStepType,
    SendJobStatus,
)
from email_platform.schemas.contracts import (
    JourneyCreate,
    JourneyEnrollmentCreate,
    JourneyProcessRead,
    JourneyStepCreate,
    JourneyStepUpdate,
    JourneyUpdate,
)
from email_platform.services.audiences import AudienceService
from email_platform.services.suppressions import SuppressionService


class JourneyService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: JourneyCreate) -> Journey:
        journey = Journey(**payload.model_dump())
        self.db.add(journey)
        self.db.commit()
        return self.get(journey.id) or journey

    def list_items(self, limit: int = 100, offset: int = 0) -> list[Journey]:
        statement = (
            select(Journey)
            .options(selectinload(Journey.steps))
            .order_by(Journey.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(self.db.scalars(statement).all())

    def count(self) -> int:
        return self.db.scalar(select(func.count()).select_from(Journey)) or 0

    def get(self, journey_id: UUID) -> Journey | None:
        statement = (
            select(Journey)
            .options(selectinload(Journey.steps))
            .where(Journey.id == journey_id)
        )
        return self.db.scalar(statement)

    def update(self, journey_id: UUID, payload: JourneyUpdate) -> Journey | None:
        journey = self.get(journey_id)
        if not journey:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(journey, key, value)
        self.db.commit()
        return self.get(journey_id)

    def delete(self, journey_id: UUID) -> bool:
        journey = self.get(journey_id)
        if not journey:
            return False
        self.db.execute(
            delete(JourneyStepExecution).where(JourneyStepExecution.journey_id == journey_id)
        )
        self.db.execute(
            delete(JourneyEnrollment).where(JourneyEnrollment.journey_id == journey_id)
        )
        self.db.delete(journey)
        self.db.commit()
        return True

    def create_step(self, journey_id: UUID, payload: JourneyStepCreate) -> JourneyStep | None:
        if not self.get(journey_id):
            return None
        step = JourneyStep(journey_id=journey_id, **payload.model_dump())
        self.db.add(step)
        self.db.commit()
        self.db.refresh(step)
        return step

    def get_step(self, step_id: UUID) -> JourneyStep | None:
        return self.db.get(JourneyStep, step_id)

    def update_step(self, step_id: UUID, payload: JourneyStepUpdate) -> JourneyStep | None:
        step = self.get_step(step_id)
        if not step:
            return None
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(step, key, value)
        self.db.commit()
        self.db.refresh(step)
        return step

    def delete_step(self, step_id: UUID) -> bool:
        step = self.get_step(step_id)
        if not step:
            return False
        self.db.execute(delete(JourneyStepExecution).where(JourneyStepExecution.step_id == step_id))
        self.db.execute(
            delete(JourneyEnrollment).where(JourneyEnrollment.current_step_id == step_id)
        )
        self.db.delete(step)
        self.db.commit()
        return True

    def enroll(
        self,
        journey_id: UUID,
        payload: JourneyEnrollmentCreate,
    ) -> JourneyEnrollment | None:
        journey = self.get(journey_id)
        contact = self.db.get(Contact, payload.contact_id)
        if not journey or not contact:
            return None

        existing = self.db.scalar(
            select(JourneyEnrollment).where(
                JourneyEnrollment.journey_id == journey_id,
                JourneyEnrollment.contact_id == payload.contact_id,
            )
        )
        first_step = self._first_step(journey)
        due_at = self._due_at_for_step(first_step)
        if existing:
            existing.status = JourneyEnrollmentStatus.active
            existing.current_step_id = first_step.id if first_step else None
            existing.variables = cast(dict[str, object], payload.variables)
            existing.due_at = due_at
            existing.exited_at = None
            existing.last_error = None
            self.db.commit()
            self.db.refresh(existing)
            return existing

        enrollment = JourneyEnrollment(
            journey_id=journey.id,
            contact_id=contact.id,
            current_step_id=first_step.id if first_step else None,
            status=(
                JourneyEnrollmentStatus.active
                if first_step
                else JourneyEnrollmentStatus.completed
            ),
            variables=cast(dict[str, object], payload.variables),
            due_at=due_at,
            exited_at=None if first_step else datetime.utcnow(),
        )
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def list_enrollments(
        self,
        journey_id: UUID | None = None,
        status: JourneyEnrollmentStatus | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JourneyEnrollment]:
        statement = select(JourneyEnrollment).order_by(JourneyEnrollment.created_at.desc())
        if journey_id:
            statement = statement.where(JourneyEnrollment.journey_id == journey_id)
        if status:
            statement = statement.where(JourneyEnrollment.status == status)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_enrollments(
        self,
        journey_id: UUID | None = None,
        status: JourneyEnrollmentStatus | None = None,
    ) -> int:
        statement = select(func.count()).select_from(JourneyEnrollment)
        if journey_id:
            statement = statement.where(JourneyEnrollment.journey_id == journey_id)
        if status:
            statement = statement.where(JourneyEnrollment.status == status)
        return self.db.scalar(statement) or 0

    def list_executions(
        self,
        enrollment_id: UUID | None = None,
        journey_id: UUID | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JourneyStepExecution]:
        statement = select(JourneyStepExecution).order_by(
            JourneyStepExecution.executed_at.desc()
        )
        if enrollment_id:
            statement = statement.where(JourneyStepExecution.enrollment_id == enrollment_id)
        if journey_id:
            statement = statement.where(JourneyStepExecution.journey_id == journey_id)
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_executions(
        self,
        enrollment_id: UUID | None = None,
        journey_id: UUID | None = None,
    ) -> int:
        statement = select(func.count()).select_from(JourneyStepExecution)
        if enrollment_id:
            statement = statement.where(JourneyStepExecution.enrollment_id == enrollment_id)
        if journey_id:
            statement = statement.where(JourneyStepExecution.journey_id == journey_id)
        return self.db.scalar(statement) or 0

    def process_due(
        self,
        limit: int = 25,
        journey_id: UUID | None = None,
    ) -> JourneyProcessRead:
        enrollments = self._claim_due(limit=limit, journey_id=journey_id)
        completed_count = 0
        failed_count = 0
        queued_send_count = 0
        enrollment_ids: list[str] = []

        for enrollment in enrollments:
            enrollment_ids.append(str(enrollment.id))
            try:
                queued_send_count += self._process_enrollment(enrollment)
                completed_count += 1
            except Exception as exc:  # noqa: BLE001
                enrollment.status = JourneyEnrollmentStatus.failed
                enrollment.last_error = str(exc)
                failed_count += 1
                self._record_execution(
                    enrollment=enrollment,
                    step=enrollment.current_step,
                    status=JourneyStepExecutionStatus.failed,
                    metadata={'source': 'journey_processor'},
                    error_message=str(exc),
                )

        self.db.commit()
        return JourneyProcessRead(
            claimed_count=len(enrollments),
            completed_count=completed_count,
            failed_count=failed_count,
            queued_send_count=queued_send_count,
            enrollment_ids=enrollment_ids,
        )

    def _claim_due(self, limit: int, journey_id: UUID | None = None) -> list[JourneyEnrollment]:
        now = datetime.utcnow()
        statement = (
            select(JourneyEnrollment)
            .options(
                selectinload(JourneyEnrollment.contact),
                selectinload(JourneyEnrollment.current_step),
                selectinload(JourneyEnrollment.journey).selectinload(Journey.steps),
            )
            .where(JourneyEnrollment.status == JourneyEnrollmentStatus.active)
            .where(JourneyEnrollment.due_at <= now)
            .order_by(JourneyEnrollment.due_at.asc())
            .limit(limit)
        )
        if journey_id:
            statement = statement.where(JourneyEnrollment.journey_id == journey_id)
        return list(self.db.scalars(statement).all())

    def _process_enrollment(self, enrollment: JourneyEnrollment) -> int:
        step = enrollment.current_step
        if not step:
            self._complete_enrollment(enrollment)
            return 0
        if self._should_exit(enrollment):
            enrollment.status = JourneyEnrollmentStatus.exited
            enrollment.exited_at = datetime.utcnow()
            self._record_execution(
                enrollment=enrollment,
                step=step,
                status=JourneyStepExecutionStatus.skipped,
                metadata={'reason': 'exit_rule_matched'},
            )
            return 0

        queued_send_count = 0
        send_record_id: UUID | None = None
        metadata: dict[str, object] = {'step_type': step.step_type.value}
        if step.step_type == JourneyStepType.send_email:
            send_record_id = self._queue_email(enrollment, step)
            queued_send_count = 1
            metadata['send_record_id'] = str(send_record_id)
        elif step.step_type == JourneyStepType.update_contact:
            self._update_contact(enrollment, step)
        elif step.step_type == JourneyStepType.branch:
            metadata['branch'] = 'evaluated'
        elif step.step_type == JourneyStepType.webhook:
            metadata['webhook'] = 'recorded'

        self._record_execution(
            enrollment=enrollment,
            step=step,
            status=JourneyStepExecutionStatus.completed,
            send_record_id=send_record_id,
            metadata=metadata,
        )
        self._advance(enrollment, step)
        return queued_send_count

    def _queue_email(self, enrollment: JourneyEnrollment, step: JourneyStep) -> UUID:
        campaign_id = self._uuid_config(step, 'campaign_id')
        template_id = self._uuid_config(step, 'template_id')
        if not template_id:
            raise ValueError('send_email step requires template_id')
        if not self.db.get(Campaign, campaign_id) and campaign_id is not None:
            raise ValueError('send_email step campaign not found')
        if SuppressionService(self.db).is_suppressed(enrollment.contact.email):
            status = EmailSendStatus.suppressed
        elif enrollment.contact.is_unsubscribed:
            status = EmailSendStatus.suppressed
        else:
            status = EmailSendStatus.queued

        job = CampaignSendJob(
            campaign_id=campaign_id,
            status=SendJobStatus.queued,
            audience_rule_tree={},
            requested_count=1,
            queued_count=1 if status == EmailSendStatus.queued else 0,
            suppressed_count=1 if status == EmailSendStatus.suppressed else 0,
            metadata_json={
                'source': 'journey_processor',
                'journey_id': str(enrollment.journey_id),
                'enrollment_id': str(enrollment.id),
                'step_id': str(step.id),
                'campaign_id': str(campaign_id) if campaign_id else None,
            },
        )
        self.db.add(job)
        self.db.flush()
        send_record = EmailSendRecord(
            campaign_id=campaign_id,
            send_job_id=job.id,
            contact_id=enrollment.contact_id,
            template_id=template_id,
            status=status,
            to_email=enrollment.contact.email,
            variables=self._variables(enrollment, step),
        )
        self.db.add(send_record)
        self.db.flush()
        return send_record.id

    def _update_contact(self, enrollment: JourneyEnrollment, step: JourneyStep) -> None:
        attributes = step.config.get('attributes')
        if isinstance(attributes, dict):
            enrollment.contact.attributes = {
                **enrollment.contact.attributes,
                **cast(dict[str, object], attributes),
            }
        is_unsubscribed = step.config.get('is_unsubscribed')
        if isinstance(is_unsubscribed, bool):
            enrollment.contact.is_unsubscribed = is_unsubscribed

    def _advance(self, enrollment: JourneyEnrollment, step: JourneyStep) -> None:
        next_step = self._next_step(enrollment.journey, step)
        if not next_step:
            self._complete_enrollment(enrollment)
            return
        enrollment.current_step_id = next_step.id
        enrollment.due_at = self._due_at_for_step(next_step)
        enrollment.last_error = None

    def _complete_enrollment(self, enrollment: JourneyEnrollment) -> None:
        enrollment.status = JourneyEnrollmentStatus.completed
        enrollment.current_step_id = None
        enrollment.due_at = None
        enrollment.exited_at = datetime.utcnow()
        enrollment.last_error = None

    def _record_execution(
        self,
        enrollment: JourneyEnrollment,
        step: JourneyStep | None,
        status: JourneyStepExecutionStatus,
        metadata: dict[str, object],
        send_record_id: UUID | None = None,
        error_message: str | None = None,
    ) -> None:
        if not step:
            return
        self.db.add(
            JourneyStepExecution(
                enrollment_id=enrollment.id,
                journey_id=enrollment.journey_id,
                step_id=step.id,
                contact_id=enrollment.contact_id,
                status=status,
                send_record_id=send_record_id,
                metadata_json=metadata,
                error_message=error_message,
            )
        )

    def _first_step(self, journey: Journey) -> JourneyStep | None:
        return min(journey.steps, key=lambda step: step.position, default=None)

    def _next_step(self, journey: Journey, current_step: JourneyStep) -> JourneyStep | None:
        later_steps = [step for step in journey.steps if step.position > current_step.position]
        return min(later_steps, key=lambda step: step.position, default=None)

    def _due_at_for_step(self, step: JourneyStep | None) -> datetime | None:
        if not step:
            return None
        if step.step_type == JourneyStepType.wait:
            seconds = step.config.get('wait_seconds', 0)
            if isinstance(seconds, int | float):
                return datetime.utcnow() + timedelta(seconds=max(float(seconds), 0))
        return datetime.utcnow()

    def _should_exit(self, enrollment: JourneyEnrollment) -> bool:
        if not enrollment.journey.exit_rule_tree:
            return False
        return AudienceService(self.db)._matches(  # noqa: SLF001
            enrollment.contact,
            enrollment.journey.exit_rule_tree,
        )

    def _variables(
        self,
        enrollment: JourneyEnrollment,
        step: JourneyStep,
    ) -> dict[str, object]:
        step_variables = step.config.get('variables')
        return {
            'email': enrollment.contact.email,
            'first_name': enrollment.contact.first_name,
            'last_name': enrollment.contact.last_name,
            'source': enrollment.contact.source,
            'attributes': enrollment.contact.attributes,
            **enrollment.contact.attributes,
            **enrollment.variables,
            **(cast(dict[str, object], step_variables) if isinstance(step_variables, dict) else {}),
        }

    def _uuid_config(self, step: JourneyStep, key: str) -> UUID | None:
        value = step.config.get(key)
        if isinstance(value, UUID):
            return value
        if isinstance(value, str) and value:
            return UUID(value)
        return None
