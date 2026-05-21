import smtplib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from email_platform.core.settings import Settings


@dataclass(frozen=True)
class EmailMessage:
    to_email: str
    from_email: str
    subject: str
    html_body: str
    text_body: str | None = None


@dataclass(frozen=True)
class EmailDeliveryResult:
    provider: str
    provider_message_id: str | None
    status_code: int


class EmailProvider(ABC):
    @abstractmethod
    def send(self, message: EmailMessage) -> EmailDeliveryResult:
        raise NotImplementedError


class ConsoleEmailProvider(EmailProvider):
    def send(self, message: EmailMessage) -> EmailDeliveryResult:
        print(f'[console-email] to={message.to_email} subject={message.subject}')
        return EmailDeliveryResult(provider='console', provider_message_id=None, status_code=200)


class SendGridEmailProvider(EmailProvider):
    def __init__(self, api_key: str) -> None:
        self.client = SendGridAPIClient(api_key)

    def send(self, message: EmailMessage) -> EmailDeliveryResult:
        mail = Mail(
            from_email=message.from_email,
            to_emails=message.to_email,
            subject=message.subject,
            html_content=message.html_body,
            plain_text_content=message.text_body,
        )
        response = self.client.send(mail)
        return EmailDeliveryResult(
            provider='sendgrid',
            provider_message_id=response.headers.get('X-Message-Id'),
            status_code=response.status_code,
        )


class SmtpEmailProvider(EmailProvider):
    def __init__(self, settings: Settings) -> None:
        if not settings.smtp_host:
            raise ValueError('SMTP_HOST is required for smtp provider')
        self.settings = settings

    def send(self, message: EmailMessage) -> EmailDeliveryResult:
        if not self.settings.smtp_host:
            raise ValueError('SMTP_HOST is required for smtp provider')
        mime = MIMEMultipart('alternative')
        mime['Subject'] = message.subject
        mime['From'] = message.from_email
        mime['To'] = message.to_email
        if message.text_body:
            mime.attach(MIMEText(message.text_body, 'plain'))
        mime.attach(MIMEText(message.html_body, 'html'))

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as server:
            if self.settings.smtp_use_tls:
                server.starttls()
            if self.settings.smtp_username and self.settings.smtp_password:
                server.login(self.settings.smtp_username, self.settings.smtp_password)
            server.sendmail(message.from_email, [message.to_email], mime.as_string())
        return EmailDeliveryResult(provider='smtp', provider_message_id=None, status_code=250)


def build_email_provider(settings: Settings) -> EmailProvider:
    if settings.email_provider == 'console':
        return ConsoleEmailProvider()
    if settings.email_provider == 'sendgrid':
        if not settings.sendgrid_api_key:
            raise ValueError('SENDGRID_API_KEY is required for sendgrid provider')
        return SendGridEmailProvider(settings.sendgrid_api_key)
    if settings.email_provider == 'smtp':
        return SmtpEmailProvider(settings)
    raise ValueError(f'Unsupported EMAIL_PROVIDER={settings.email_provider}')
