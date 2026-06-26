from uuid import uuid4

import pytest

from email_platform.models.entities import DeliveryAttempt
from email_platform.services.campaigns import CampaignService


def proof_attempt(
    *,
    status: str = 'submitted',
    smtp_response_code: int | None = 250,
    route_resolved: bool | None = True,
    provider: str = 'managed_smtp',
    route_type: str = 'managed_smtp',
    route_key: str = 'managed-smtp-scaleway-primary',
    metadata: dict[str, object] | None = None,
) -> DeliveryAttempt:
    metadata = dict(metadata or {})
    if route_resolved is not None:
        metadata['mta_route_resolved'] = route_resolved
    return DeliveryAttempt(
        send_record_id=uuid4(),
        send_job_id=uuid4(),
        campaign_id=uuid4(),
        attempt_number=1,
        provider=provider,
        route_type=route_type,
        route_key=route_key,
        status=status,
        smtp_response_code=smtp_response_code,
        metadata_json=metadata,
    )


def service_with_latest_attempt(attempt: DeliveryAttempt | None) -> CampaignService:
    service = CampaignService.__new__(CampaignService)
    service._latest_campaign_test_attempt = lambda _campaign_id: attempt
    return service


def test_campaign_launch_proof_gate_accepts_successful_managed_smtp_attempt() -> None:
    service = service_with_latest_attempt(proof_attempt())

    service._assert_latest_proof_route_ok(uuid4())


def test_campaign_launch_proof_gate_accepts_successful_sendgrid_attempt() -> None:
    service = service_with_latest_attempt(
        proof_attempt(
            provider='sendgrid',
            route_type='sendgrid',
            route_key='sendgrid-primary',
            route_resolved=None,
            smtp_response_code=202,
        )
    )

    service._assert_latest_proof_route_ok(uuid4())


def test_launch_job_metadata_snapshots_managed_smtp_proof_route() -> None:
    service = service_with_latest_attempt(None)
    attempt = proof_attempt(
        metadata={
            'mta_submission_provider': 'managed_smtp',
            'delivery_route_mode': 'managed_smtp_pool',
            'route_mode_provider': 'managed_smtp',
            'route_mode_ip_pool_name': 'scaleway-primary',
            'route_mode_mta_ip_pool_id': 'pool-scaleway-primary',
            'mta_ip_pool_name': 'scaleway-primary',
            'mta_node_name': 'mta-node-1',
            'mta_submission_host': 'mta.scaleway.example',
            'mta_submission_port': 587,
            'mta_public_ipv4': '203.0.113.10',
        },
    )

    metadata = service._launch_job_metadata(True, attempt)

    assert metadata['dry_run'] is True
    proof_route = metadata['latest_proof_route']
    assert proof_route['route_type'] == 'managed_smtp'
    assert proof_route['submission_provider'] == 'managed_smtp'
    assert proof_route['mta_route_status'] == 'resolved'
    assert proof_route['delivery_route_mode'] == 'managed_smtp_pool'
    assert proof_route['route_mode_ip_pool_name'] == 'scaleway-primary'
    assert proof_route['mta_node_name'] == 'mta-node-1'
    assert proof_route['mta_submission_host'] == 'mta.scaleway.example'


def test_launch_job_metadata_snapshots_sendgrid_proof_route() -> None:
    service = service_with_latest_attempt(None)
    attempt = proof_attempt(
        provider='sendgrid',
        route_type='sendgrid',
        route_key='sendgrid-primary',
        route_resolved=None,
        smtp_response_code=202,
        metadata={
            'submission_provider': 'sendgrid',
            'delivery_route_mode': 'third_party_provider',
            'route_mode_provider': 'sendgrid',
        },
    )

    proof_route = service._launch_job_metadata(False, attempt)['latest_proof_route']

    assert proof_route['route_type'] == 'sendgrid'
    assert proof_route['submission_provider'] == 'sendgrid'
    assert proof_route['mta_route_status'] == 'attempted'
    assert proof_route['delivery_route_mode'] == 'third_party_provider'
    assert proof_route['route_mode_provider'] == 'sendgrid'


def test_campaign_launch_proof_gate_requires_a_proof_attempt() -> None:
    service = service_with_latest_attempt(None)

    with pytest.raises(ValueError, match='successful campaign proof send'):
        service._assert_latest_proof_route_ok(uuid4())


def test_campaign_launch_proof_gate_rejects_blocked_managed_smtp_route() -> None:
    service = service_with_latest_attempt(proof_attempt(route_resolved=False))

    with pytest.raises(ValueError, match='Resolve proof routing'):
        service._assert_latest_proof_route_ok(uuid4())


def test_campaign_launch_proof_gate_rejects_unresolved_managed_smtp_route() -> None:
    service = service_with_latest_attempt(proof_attempt(route_resolved=None))

    with pytest.raises(ValueError, match='Resolve proof routing'):
        service._assert_latest_proof_route_ok(uuid4())


def test_campaign_launch_proof_gate_includes_route_block_evidence() -> None:
    service = service_with_latest_attempt(
        proof_attempt(
            route_resolved=False,
            metadata={
                'mta_route_block_code': 'NO_HEALTHY_MTA_NODE',
                'mta_route_block_message': 'No active MTA node is available.',
            },
        )
    )

    with pytest.raises(ValueError) as exc_info:
        service._assert_latest_proof_route_ok(uuid4())

    assert str(exc_info.value) == (
        'Resolve proof routing before dry-run launch. '
        'NO_HEALTHY_MTA_NODE: No active MTA node is available.'
    )


def test_campaign_launch_proof_gate_rejects_failed_smtp_response() -> None:
    service = service_with_latest_attempt(proof_attempt(smtp_response_code=451))

    with pytest.raises(ValueError, match='Resolve proof routing'):
        service._assert_latest_proof_route_ok(uuid4())
