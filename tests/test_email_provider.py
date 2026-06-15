from types import SimpleNamespace

from email_platform.providers import email as email_module
from email_platform.providers.email import EmailMessage, SmtpEmailProvider


class FakeSmtp:
    instances = []

    def __init__(self, host, port) -> None:
        self.host = host
        self.port = port
        self.started_tls = False
        self.login_args = None
        self.sent = None
        self.__class__.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def starttls(self) -> None:
        self.started_tls = True

    def login(self, username, password) -> None:
        self.login_args = (username, password)

    def sendmail(self, envelope_from, recipients, message) -> None:
        self.sent = (envelope_from, recipients, message)


def test_smtp_email_provider_supports_managed_smtp_submission_endpoint(monkeypatch) -> None:
    FakeSmtp.instances = []
    monkeypatch.setattr(email_module.smtplib, 'SMTP', FakeSmtp)
    settings = SimpleNamespace(
        smtp_host='default.example.com',
        smtp_port=587,
        smtp_use_tls=True,
        smtp_username='submission-user',
        smtp_password='submission-password',
    )
    provider = SmtpEmailProvider(
        settings,
        host='mta-001.example.com',
        port=2525,
        provider_name='managed_smtp',
    )

    result = provider.send(
        EmailMessage(
            to_email='recipient@example.com',
            from_email='sender@example.com',
            subject='Managed SMTP test',
            html_body='<p>Hello</p>',
            text_body='Hello',
            envelope_from='bounces@example.com',
        )
    )

    smtp = FakeSmtp.instances[0]
    assert smtp.host == 'mta-001.example.com'
    assert smtp.port == 2525
    assert smtp.started_tls is True
    assert smtp.login_args == ('submission-user', 'submission-password')
    assert smtp.sent is not None
    assert smtp.sent[0] == 'bounces@example.com'
    assert smtp.sent[1] == ['recipient@example.com']
    assert result.provider == 'managed_smtp'
    assert result.status_code == 250
