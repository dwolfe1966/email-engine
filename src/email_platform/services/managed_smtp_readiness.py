from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.models.entities import ManagedSmtpReadinessCheck
from email_platform.schemas.contracts import (
    ManagedSmtpReadinessAlertsRead,
    ManagedSmtpReadinessCheckCreate,
    ManagedSmtpReadinessNotificationRead,
    ManagedSmtpReadinessSummaryRead,
    ManagedSmtpReadinessTrendRead,
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

    def trend(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        domain: str | None = None,
        host: str | None = None,
        limit: int = 20,
    ) -> ManagedSmtpReadinessTrendRead:
        checks = self.list_checks(
            source=source,
            check_type=check_type,
            domain=domain,
            host=host,
            limit=limit,
            offset=0,
        )
        sample_size = len(checks)
        ok_count = sum(1 for check in checks if check.status == 'ok')
        warning_count = sum(1 for check in checks if check.status == 'warning')
        failed_count = sum(1 for check in checks if check.status == 'failed')
        latest_window = checks[: max(1, sample_size // 2)] if checks else []
        previous_window = checks[len(latest_window) :] if checks else []
        latest_failure_rate = self._failure_rate(latest_window)
        previous_failure_rate = self._failure_rate(previous_window)
        failure_rate = ((warning_count + failed_count) / sample_size) if sample_size else 0.0
        trend = self._trend_label(latest_failure_rate, previous_failure_rate, sample_size)
        alert_status, alert_reasons = self._trend_alert(checks, trend, failure_rate)
        return ManagedSmtpReadinessTrendRead(
            sample_size=sample_size,
            ok_count=ok_count,
            warning_count=warning_count,
            failed_count=failed_count,
            ok_rate=(ok_count / sample_size) if sample_size else 0.0,
            failure_rate=failure_rate,
            trend=trend,
            alert_status=alert_status,
            alert_reasons=alert_reasons,
            latest_window_failure_rate=latest_failure_rate,
            previous_window_failure_rate=previous_failure_rate,
            recent_checks=checks,
        )

    def alerts(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        domain: str | None = None,
        host: str | None = None,
        limit: int = 20,
    ) -> ManagedSmtpReadinessAlertsRead:
        trend = self.trend(
            source=source,
            check_type=check_type,
            domain=domain,
            host=host,
            limit=limit,
        )
        alert_checks = [check for check in trend.recent_checks if check.status != 'ok']
        return ManagedSmtpReadinessAlertsRead(
            alert_status=trend.alert_status,
            alert_reasons=trend.alert_reasons,
            alert_count=len(alert_checks),
            trend=trend,
            alert_checks=alert_checks,
        )

    def notification(
        self,
        *,
        source: str | None = None,
        check_type: str | None = None,
        domain: str | None = None,
        host: str | None = None,
        limit: int = 20,
    ) -> ManagedSmtpReadinessNotificationRead:
        alerts = self.alerts(
            source=source,
            check_type=check_type,
            domain=domain,
            host=host,
            limit=limit,
        )
        latest_alert = alerts.alert_checks[0] if alerts.alert_checks else None
        scope = self._notification_scope(domain=domain, host=host, check_type=check_type)
        primary_reason = alerts.alert_reasons[0] if alerts.alert_reasons else 'No readiness alert reason available.'
        severity = alerts.alert_status if alerts.alert_status in {'critical', 'warning'} else 'info'
        should_notify = severity in {'critical', 'warning'} and alerts.alert_count > 0
        title = f'Managed SMTP readiness {severity}: {scope}'
        if latest_alert:
            message = (
                f'{primary_reason} Latest alert evidence is {latest_alert.status} '
                f'for {latest_alert.host or latest_alert.domain or scope}.'
            )
        else:
            message = primary_reason
        return ManagedSmtpReadinessNotificationRead(
            should_notify=should_notify,
            severity=severity,
            title=title,
            message=message,
            dedupe_key=self._notification_dedupe_key(alerts.alert_status, latest_alert, scope),
            alert_status=alerts.alert_status,
            alert_reasons=alerts.alert_reasons,
            alert_count=alerts.alert_count,
            latest_alert_check=latest_alert,
            alerts=alerts,
        )

    def _failure_rate(self, checks: list[ManagedSmtpReadinessCheck]) -> float:
        if not checks:
            return 0.0
        failed = sum(1 for check in checks if check.status != 'ok')
        return failed / len(checks)

    def _trend_label(
        self,
        latest_failure_rate: float,
        previous_failure_rate: float,
        sample_size: int,
    ) -> str:
        if sample_size < 4:
            return 'insufficient_data'
        if latest_failure_rate < previous_failure_rate:
            return 'improving'
        if latest_failure_rate > previous_failure_rate:
            return 'regressing'
        return 'stable'

    def _trend_alert(
        self,
        checks: list[ManagedSmtpReadinessCheck],
        trend: str,
        failure_rate: float,
    ) -> tuple[str, list[str]]:
        sample_size = len(checks)
        if sample_size < 4:
            return 'unknown', ['Not enough readiness checks to classify trend.']

        status = 'ok'
        reasons: list[str] = []
        latest_check = checks[0] if checks else None
        if latest_check and latest_check.status == 'failed':
            status = 'critical'
            reasons.append('Latest readiness check failed.')
        if failure_rate >= 0.5:
            status = 'critical'
            reasons.append('At least half of recent readiness checks need review.')
        elif failure_rate > 0:
            status = 'warning' if status == 'ok' else status
            reasons.append('Recent readiness checks include warning or failed results.')
        if trend == 'regressing':
            status = 'warning' if status == 'ok' else status
            reasons.append('Recent readiness failure rate is increasing.')

        if not reasons:
            reasons.append('Recent readiness checks are passing.')
        return status, reasons

    def _notification_scope(
        self,
        *,
        domain: str | None = None,
        host: str | None = None,
        check_type: str | None = None,
    ) -> str:
        parts = [part for part in [host, domain, check_type] if part]
        return ' / '.join(parts) if parts else 'all managed SMTP checks'

    def _notification_dedupe_key(
        self,
        alert_status: str,
        latest_alert: ManagedSmtpReadinessCheck | None,
        scope: str,
    ) -> str:
        if latest_alert:
            return f'managed-smtp-readiness:{alert_status}:{latest_alert.id}'
        return f'managed-smtp-readiness:{alert_status}:{scope}'

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
