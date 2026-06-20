from uuid import uuid4

import pytest
from fastapi import HTTPException

from email_platform.api import routes
from email_platform.schemas.contracts import CampaignLaunchRequest


def test_campaign_launch_route_returns_400_for_failed_proof_route(monkeypatch) -> None:
    class FakeCampaignService:
        def __init__(self, db):
            self.db = db

        def launch(self, campaign_id, payload):
            raise ValueError('Resolve proof routing before dry-run launch.')

    monkeypatch.setattr(routes, 'CampaignService', FakeCampaignService)

    with pytest.raises(HTTPException) as exc_info:
        routes.launch_campaign(uuid4(), CampaignLaunchRequest(dry_run=True), db=object())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == 'Resolve proof routing before dry-run launch.'
