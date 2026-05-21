import base64
import hashlib
import hmac
from uuid import UUID

from sqlalchemy.orm import Session

from email_platform.models.entities import EmailEvent, EmailEventType, EmailSendRecord
from email_platform.schemas.contracts import EventCreate, JsonObject
from email_platform.services.events import EventService


class TrackingService:
    def __init__(self, db: Session, secret: str) -> None:
        self.db = db
        self.secret = secret

    def get_send_record(self, send_record_id: UUID) -> EmailSendRecord | None:
        return self.db.get(EmailSendRecord, send_record_id)

    def create_token(self, send_record_id: UUID) -> str:
        raw_id = str(send_record_id)
        digest = hmac.new(
            self.secret.encode('utf-8'), raw_id.encode('utf-8'), hashlib.sha256
        ).digest()
        signature = base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')
        return f'{raw_id}.{signature}'

    def verify_token(self, token: str) -> UUID:
        try:
            raw_id, signature = token.rsplit('.', 1)
            send_record_id = UUID(raw_id)
        except ValueError as exc:
            raise ValueError('Invalid tracking token') from exc

        expected = self.create_token(send_record_id).rsplit('.', 1)[1]
        if not hmac.compare_digest(signature, expected):
            raise ValueError('Invalid tracking token')
        return send_record_id

    def record_open(self, token: str, metadata: JsonObject | None = None) -> EmailEvent:
        return self._record(token, EmailEventType.opened, metadata or {})

    def record_click(self, token: str, metadata: JsonObject | None = None) -> EmailEvent:
        return self._record(token, EmailEventType.clicked, metadata or {})

    def _record(
        self, token: str, event_type: EmailEventType, metadata: JsonObject
    ) -> EmailEvent:
        send_record_id = self.verify_token(token)
        send_record = self.get_send_record(send_record_id)
        if not send_record:
            raise ValueError('Send record not found')

        event = EventService(self.db).record_no_commit(
            EventCreate(
                contact_id=send_record.contact_id,
                campaign_id=send_record.campaign_id,
                event_type=event_type,
                provider_message_id=send_record.provider_message_id,
                metadata_json={
                    'send_record_id': str(send_record.id),
                    'send_job_id': str(send_record.send_job_id),
                    **metadata,
                },
            )
        )
        self.db.commit()
        self.db.refresh(event)
        return event
