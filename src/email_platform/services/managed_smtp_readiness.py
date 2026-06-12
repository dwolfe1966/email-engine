from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import ManagedSmtpReadinessCheck
from email_platform.schemas.contracts import (
    ManagedSmtpReadinessCheckCreate,
    ManagedSmtpReadinessSummaryRead,
)


class ManagedSmtpReadinessService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, payload: ManagedSmtpReadinessCheckCreate) -> ManagedSmtpReadinessCheck:
        status = payload.status.strip().lower()
        if status not in {'ok', 'warning', 'failed'}:
            raise ValueError('status must be ok, warning, or failed')
        check = ManagedSmtpReadinessCheck(
            source=payload.source.strip() or 'managed_smtp_mta_smoke',
            check_type=payload.check_type.strip() or 'mta_smoke',
            status=status,
            domain=payload.domain.strip().lower() if payload.domain else None,
            host=payload.host.strip().lower() if payload.host else None,
            summary=payload.summary.strip()[:500] if payload.summary else None,
            result_json=payload.result_json,
            created_at=datetime.utcnow(),
        )
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        return check

    def list_checks(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        status: str | None = None,
        domain: str | None = None,
        host: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ManagedSmtpReadinessCheck]:
        statement = self._statement(
            source=source,
            check_type=check_type,
            status=status,
            domain=domain,
            host=host,
        ).order_by(ManagedSmtpReadinessCheck.created_at.desc())
        return list(self.db.scalars(statement.limit(limit).offset(offset)).all())

    def count_checks(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        status: str | None = None,
        domain: str | None = None,
        host: str | None = None,
    ) -> int:
        statement = self._statement(
            source=source,
            check_type=check_type,
            status=status,
            domain=domain,
            host=host,
            count=True,
        )
        return self.db.scalar(statement) or 0

    def summary(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        domain: str | None = None,
        host: str | None = None,
    ) -> ManagedSmtpReadinessSummaryRead:
        latest_check = self._latest_check(
            source=source,
            check_type=check_type,
            domain=domain,
            host=host,
        )
        latest_success = self._latest_check(
            source=source,
            check_type=check_type,
            status='ok',
            domain=domain,
            host=host,
        )
        return ManagedSmtpReadinessSummaryRead(
            total_count=self.count_checks(
                source=source,
                check_type=check_type,
                domain=domain,
                host=host,
            ),
            ok_count=self.count_checks(
                source=source,
                check_type=check_type,
                status='ok',
                domain=domain,
                host=host,
            ),
            warning_count=self.count_checks(
                source=source,
                check_type=check_type,
                status='warning',
                domain=domain,
                host=host,
            ),
            failed_count=self.count_checks(
                source=source,
                check_type=check_type,
                status='failed',
                domain=domain,
                host=host,
            ),
            latest_check=latest_check,
            latest_success=latest_success,
        )

    def _latest_check(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        status: str | None = None,
        domain: str | None = None,
        host: str | None = None,
    ) -> ManagedSmtpReadinessCheck | None:
        statement = self._statement(
            source=source,
            check_type=check_type,
            status=status,
            domain=domain,
            host=host,
        ).order_by(ManagedSmtpReadinessCheck.created_at.desc())
        return self.db.scalars(statement.limit(1)).first()

    def _statement(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        status: str | None = None,
        domain: str | None = None,
        host: str | None = None,
        count: bool = False,
    ):
        statement = (
            select(func.count()).select_from(ManagedSmtpReadinessCheck)
            if count
            else select(ManagedSmtpReadinessCheck)
        )
        if source:
            statement = statement.where(ManagedSmtpReadinessCheck.source == source)
        if check_type:
            statement = statement.where(ManagedSmtpReadinessCheck.check_type == check_type)
        if status:
            statement = statement.where(ManagedSmtpReadinessCheck.status == status.lower())
        if domain:
            statement = statement.where(ManagedSmtpReadinessCheck.domain == domain.lower())
        if host:
            statement = statement.where(ManagedSmtpReadinessCheck.host == host.lower())
        return statement
