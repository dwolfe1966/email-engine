from types import SimpleNamespace
from uuid import uuid4

from email_platform.providers.email import EmailDeliveryResult
from email_platform.services.sending import SendingService


class FakeProvider:
    def __init__(self) -> None:
        self.message = None

    def send(self, message):
        self.message = message
        return EmailDeliveryResult(
            provider='fake',
            provider_message_id='msg_123',
            status_code=202,
        )


class FakeTemplateService:
    def __init__(self, template_id):
        self.template_id = template_id
        self.render_context = None

    def get(self, template_id):
        if template_id != self.template_id:
            return None
        return SimpleNamespace(id=template_id)

    def variables_for_template(self, template_id):
        if template_id != self.template_id:
            return None
        return SimpleNamespace(
            sample_variables={
                'first_name': 'Sample',
                'order_number': 'SM-1001',
                'order_items': [
                    {'name': 'Starter plan', 'quantity': 1, 'total': '$49.00'}
                ],
            }
        )

    def render(self, template, variables):
        self.render_context = variables
        rows = ''.join(
            f'<tr><td>{item["name"]}</td><td>{item["total"]}</td></tr>'
            for item in variables['order_items']
        )
        return (
            f'Receipt for {variables["order_number"]}',
            f'<table>{rows}</table><p>Hello {variables["first_name"]}</p>',
            None,
        )


def test_template_test_send_merges_sample_variables_before_rendering() -> None:
    template_id = uuid4()
    provider = FakeProvider()
    template_service = FakeTemplateService(template_id)
    service = SendingService.__new__(SendingService)
    service.provider = provider
    service.template_service = template_service
    service.settings = SimpleNamespace(default_from_email='sender@example.com')

    result = service.send_test(
        template_id,
        'recipient@example.com',
        {'first_name': 'Taylor'},
    )

    assert template_service.render_context == {
        'first_name': 'Taylor',
        'order_number': 'SM-1001',
        'order_items': [{'name': 'Starter plan', 'quantity': 1, 'total': '$49.00'}],
    }
    assert provider.message.subject == 'Receipt for SM-1001'
    assert 'Starter plan' in provider.message.html_body
    assert result['provider'] == 'fake'
    assert result['subject'] == 'Receipt for SM-1001'
    assert result['variables']['first_name'] == 'Taylor'
