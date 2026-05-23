import json
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from email_platform.core.settings import get_settings
from email_platform.db.session import get_db
from email_platform.models.entities import (
    Audience,
    Campaign,
    CampaignStatus,
    Contact,
    EmailEvent,
    EmailSendRecord,
    EmailTemplateVersion,
    Journey,
)
from email_platform.schemas.contracts import (
    AudienceCreate,
    AudiencePreviewRequest,
    AudienceUpdate,
    CampaignCreate,
    CampaignLaunchRequest,
    CampaignUpdate,
    ContactUpsert,
    JsonObject,
    TemplateCreate,
    TemplatePreviewRequest,
    TemplateUpdate,
    TemplateValidationRequest,
    TemplateVersionCreate,
)
from email_platform.services.analytics import AnalyticsService
from email_platform.services.audiences import AudienceService
from email_platform.services.campaigns import CampaignService
from email_platform.services.contacts import ContactService
from email_platform.services.delivery import DeliveryService
from email_platform.services.journeys import JourneyService
from email_platform.services.templates import TemplateService

router = APIRouter(prefix='/api', tags=['sentientmail-compat'])
DbSession = Annotated[Session, Depends(get_db)]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]


@router.get('/templates')
def compat_list_templates(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = TemplateService(db)
    templates = service.list(limit=limit, offset=offset)
    return _list_response(
        [_template_summary(template) for template in templates], limit, offset, service.count()
    )


@router.post('/templates')
def compat_create_template(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    template = TemplateService(db).create(_template_create_payload(payload))
    return _template_detail(template)


@router.post('/templates/{template_id}/versions')
def compat_create_template_version(
    template_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    service = TemplateService(db)
    version = service.create_version(template_id, _template_version_create_payload(payload))
    template = service.get(template_id)
    if not version or not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return {
        'version_id': str(version.id),
        'version_number': version.version_number,
        'template': _template_detail(template),
    }


@router.get('/templates/{template_id}')
def compat_get_template(template_id: UUID, db: DbSession) -> dict[str, object]:
    template = TemplateService(db).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return _template_detail(template)


@router.post('/templates/{template_id}/ai-draft')
def compat_template_ai_draft(
    template_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    template = TemplateService(db).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')

    current_html = str(payload.get('current_html', template.html_body))
    current_subject = str(payload.get('current_subject', template.subject))
    brief = str(payload.get('brief', '')).strip()
    new_html = _draft_html(current_html, brief)
    validation = TemplateService(db).validate(
        TemplateValidationRequest(
            subject=current_subject,
            html_body=new_html,
            css_body=template.css_body,
            text_body=template.text_body,
            variables={},
        )
    )
    assistant_message = (
        'I drafted a compatible email-engine revision. Review the generated HTML, '
        'preview it, and apply it if it fits the campaign.'
    )
    return {
        'commentary': (
            f'Applied the brief: {brief}' if brief else 'Generated a conservative draft.'
        ),
        'new_html': new_html,
        'new_subject': current_subject,
        'new_preheader': payload.get('current_preheader'),
        'validation': {
            'passed': validation.ok,
            'blocking_count': len(validation.errors) + len(validation.lint_errors),
            'warning_count': len(validation.lint_warnings),
            'failures': [
                *_validation_failures(validation.errors, 'block'),
                *_validation_failures(validation.lint_errors, 'block'),
                *_validation_failures(validation.lint_warnings, 'warn'),
            ],
        },
        'user_message': brief,
        'assistant_message': assistant_message,
        'provider': 'email-engine',
        'model': 'compat-draft',
    }


@router.patch('/templates/{template_id}')
def compat_update_template(
    template_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    template = TemplateService(db).update(template_id, _template_update_payload(payload))
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return _template_detail(template)


@router.delete('/templates/{template_id}')
def compat_delete_template(template_id: UUID, db: DbSession) -> dict[str, object]:
    if not TemplateService(db).delete(template_id):
        raise HTTPException(status_code=404, detail='Template not found')
    return {'status': 'deleted', 'id': str(template_id)}


@router.post('/render')
def compat_render(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    template_id = payload.get('template_id')
    variables = _object_payload(payload.get('variables', payload.get('slots')))
    if template_id:
        template = TemplateService(db).get(UUID(str(template_id)))
        if not template:
            raise HTTPException(status_code=404, detail='Template not found')
        request = TemplatePreviewRequest(
            subject=template.subject,
            html_body=template.html_body,
            css_body=template.css_body,
            text_body=template.text_body,
            variables=variables,
        )
    else:
        request = TemplatePreviewRequest(
            subject=str(payload.get('subject', '')),
            html_body=str(payload.get('html_body', payload.get('html', ''))),
            css_body=_optional_str(payload.get('css_body', payload.get('css'))),
            text_body=_optional_str(payload.get('text_body', payload.get('text'))),
            variables=variables,
        )
    preview = TemplateService(db).preview(request)
    return _encoded_dict(preview)


@router.post('/render-document')
def compat_render_document(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    document = _object_payload(payload.get('document_json', payload.get('document')))
    html_body = _document_to_html(document)
    request = TemplatePreviewRequest(
        subject=str(payload.get('subject', '')),
        html_body=html_body,
        css_body=_optional_str(payload.get('css_body', payload.get('css'))),
        text_body=_optional_str(payload.get('text_body', payload.get('text'))),
        variables=_object_payload(payload.get('variables')),
    )
    return _encoded_dict(TemplateService(db).preview(request))


@router.get('/contacts')
def compat_list_contacts(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
    email: str | None = None,
    q: str | None = None,
    source: str | None = None,
    state: str | None = None,
    self_search: bool | None = None,
    regulated: bool | None = None,
    intent_criminal: bool | None = None,
    consent_marketing: bool | None = None,
    engagement: str | None = None,
) -> dict[str, object]:
    statement = select(Contact).order_by(Contact.created_at.desc())
    count_statement = select(func.count()).select_from(Contact)
    search = q or email
    if search:
        search_filter = or_(
            Contact.email.ilike(f'%{search}%'),
            Contact.first_name.ilike(f'%{search}%'),
            Contact.last_name.ilike(f'%{search}%'),
        )
        statement = statement.where(search_filter)
        count_statement = count_statement.where(search_filter)
    if source:
        statement = statement.where(Contact.source == source)
        count_statement = count_statement.where(Contact.source == source)
    all_contacts = list(db.scalars(statement).all())
    filtered = [
        contact
        for contact in all_contacts
        if _contact_matches_filters(
            contact,
            state=state,
            self_search=self_search,
            regulated=regulated,
            intent_criminal=intent_criminal,
            consent_marketing=consent_marketing,
            engagement=engagement,
        )
    ]
    page = filtered[offset : offset + limit]
    return _list_response([_contact_row(contact) for contact in page], limit, offset, len(filtered))


@router.get('/contacts/_meta')
def compat_contacts_meta(db: DbSession) -> dict[str, object]:
    sources = db.execute(
        select(Contact.source, func.count())
        .where(Contact.source.is_not(None))
        .group_by(Contact.source)
        .order_by(Contact.source)
    ).all()
    contacts = list(db.scalars(select(Contact)).all())
    return {
        'total': ContactService(db).count(),
        'marketable': sum(1 for contact in contacts if not contact.is_unsubscribed),
        'regulated': sum(1 for contact in contacts if _attribute_bool(contact, 'regulated')),
        'self_search': sum(1 for contact in contacts if _attribute_bool(contact, 'is_self_search')),
        'intent_criminal': sum(
            1 for contact in contacts if _attribute_bool(contact, 'intent_criminal')
        ),
        'sources': [{'source': source, 'count': count} for source, count in sources],
        'fields': ['email', 'first_name', 'last_name', 'source', 'is_unsubscribed', 'attributes'],
    }


@router.post('/contacts')
def compat_upsert_contact(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    contact = ContactService(db).upsert(ContactUpsert.model_validate(payload))
    return _encoded_dict(contact)


@router.get('/segments')
def compat_list_segments(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = AudienceService(db)
    audiences = service.list_items(limit=limit, offset=offset)
    return _list_response(
        [_segment_summary(audience) for audience in audiences], limit, offset, service.count()
    )


@router.get('/segments/_meta/fields')
def compat_segment_fields(db: DbSession) -> dict[str, object]:
    metadata = ContactService(db).metadata(sample_limit=10, scan_limit=500)
    field_names = cast(Iterable[object], metadata.get('fields', []))
    attribute_keys = cast(Iterable[object], metadata.get('attribute_keys', []))
    fields = [
        {'name': str(field), 'type': 'string', 'enum_values': None}
        for field in field_names
    ]
    fields.extend(
        {'name': f'attributes.{field}', 'type': 'string', 'enum_values': None}
        for field in attribute_keys
    )
    return {
        'fields': fields,
        'ops': ['eq', 'ne', 'in', 'not_in', 'is_null', 'is_not_null', 'contains'],
    }


@router.get('/segments/{segment_id}')
def compat_get_segment(segment_id: UUID, db: DbSession) -> dict[str, object]:
    audience = AudienceService(db).get(segment_id)
    if not audience:
        raise HTTPException(status_code=404, detail='Segment not found')
    return _segment_summary(audience)


@router.post('/segments')
def compat_create_segment(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    audience = AudienceService(db).create(
        AudienceCreate(
            name=str(payload.get('name', f'segment-{uuid4()}')),
            description=_optional_str(payload.get('description')),
            rule_tree=_segment_rule_tree(payload),
        )
    )
    return _segment_summary(audience)


@router.patch('/segments/{segment_id}')
def compat_update_segment(
    segment_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    audience = AudienceService(db).update(
        segment_id,
        AudienceUpdate(
            name=_optional_str(payload.get('name')),
            description=_optional_str(payload.get('description')),
            rule_tree=_segment_rule_tree(payload) if _has_segment_rules(payload) else None,
        ),
    )
    if not audience:
        raise HTTPException(status_code=404, detail='Segment not found')
    return _segment_summary(audience)


@router.delete('/segments/{segment_id}')
def compat_delete_segment(segment_id: UUID, db: DbSession) -> dict[str, object]:
    if not AudienceService(db).delete(segment_id):
        raise HTTPException(status_code=404, detail='Segment not found')
    return {'status': 'deleted', 'id': str(segment_id)}


@router.post('/segments/{segment_id}/refresh')
def compat_refresh_segment(segment_id: UUID, db: DbSession) -> dict[str, object]:
    audience = AudienceService(db).get(segment_id)
    if not audience:
        raise HTTPException(status_code=404, detail='Segment not found')
    count, _ = AudienceService(db).preview(audience.rule_tree, limit=1)
    audience.estimated_count = count
    db.commit()
    db.refresh(audience)
    return _segment_summary(audience)


@router.post('/segments/preview')
def compat_preview_segment(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    request = AudiencePreviewRequest(
        rule_tree=_segment_rule_tree(payload),
        limit=_int_payload(payload.get('limit'), 25),
    )
    count, contacts = AudienceService(db).preview(request.rule_tree, request.limit)
    return {
        'estimated_count': count,
        'estimated_size': count,
        'summary': f'{count} matched contacts',
        'items': [_encoded_dict(contact) for contact in contacts],
        'sample': [_contact_row(contact) for contact in contacts],
    }


@router.get('/sends')
def compat_list_sends(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    service = CampaignService(db)
    campaigns = service.list_items(limit=limit, offset=offset)
    return _list_response(
        [_send_detail(db, campaign) for campaign in campaigns], limit, offset, service.count()
    )


@router.get('/sends/{send_id}')
def compat_get_send(send_id: UUID, db: DbSession) -> dict[str, object]:
    campaign = CampaignService(db).get(send_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Send not found')
    return _send_detail(db, campaign)


@router.post('/sends')
def compat_create_send(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    template_id = _template_id_from_payload(payload, db)
    audience_id = payload.get('audience_id', payload.get('segment_id'))
    audience_query: JsonObject = {}
    if audience_id:
        audience = AudienceService(db).get(UUID(str(audience_id)))
        audience_query = cast(JsonObject, audience.rule_tree) if audience else {}
    scheduled_at = _datetime_payload(payload.get('scheduled_for', payload.get('scheduled_at')))
    campaign = CampaignService(db).create(
        CampaignCreate(
            name=str(payload.get('name', payload.get('title', 'Untitled send'))),
            template_id=template_id,
            audience_query=_object_payload(payload.get('audience_query')) or audience_query,
            scheduled_at=scheduled_at,
        )
    )
    return _send_detail(db, campaign)


@router.patch('/sends/{send_id}')
def compat_update_send(
    send_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    updates: dict[str, object] = {}
    if payload.get('name') or payload.get('title'):
        updates['name'] = str(payload.get('name', payload.get('title')))
    if payload.get('template_id') or payload.get('template_version_id'):
        updates['template_id'] = _template_id_from_payload(payload, db)
    if payload.get('audience_query') or payload.get('segment_rules'):
        updates['audience_query'] = _object_payload(
            payload.get('audience_query', payload.get('segment_rules'))
        )
    if 'scheduled_for' in payload or 'scheduled_at' in payload:
        updates['scheduled_at'] = _datetime_payload(
            payload.get('scheduled_for', payload.get('scheduled_at'))
        )
    campaign = CampaignService(db).update(send_id, CampaignUpdate.model_validate(updates))
    if not campaign:
        raise HTTPException(status_code=404, detail='Send not found')
    return _send_detail(db, campaign)


@router.delete('/sends/{send_id}')
def compat_delete_send(send_id: UUID, db: DbSession) -> dict[str, object]:
    if not CampaignService(db).delete(send_id):
        raise HTTPException(status_code=404, detail='Send not found')
    return {'status': 'deleted', 'id': str(send_id)}


@router.post('/sends/{send_id}/recipients/preview')
def compat_preview_send_recipients(send_id: UUID, db: DbSession) -> dict[str, object]:
    campaign = CampaignService(db).get(send_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Send not found')
    matched, contacts = AudienceService(db).preview(campaign.audience_query, limit=500)
    deliverable = [contact for contact in contacts if not contact.is_unsubscribed]
    return {
        'matched': matched,
        'after_consent_filter': len(deliverable),
        'after_suppression_filter': len(deliverable),
        'consent_culled': matched - len(deliverable),
        'suppression_culled': 0,
    }


@router.post('/sends/{send_id}/schedule')
def compat_schedule_send(
    send_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    scheduled_at = _datetime_payload(payload.get('scheduled_for', payload.get('scheduled_at')))
    campaign = CampaignService(db).get(send_id)
    if not campaign:
        raise HTTPException(status_code=404, detail='Send not found')
    campaign.status = CampaignStatus.scheduled
    campaign.scheduled_at = scheduled_at or datetime.utcnow()
    db.commit()
    db.refresh(campaign)
    return _send_detail(db, campaign)


@router.post('/sends/{send_id}/launch')
def compat_launch_send(
    send_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    campaign = CampaignService(db).get(send_id)
    if campaign and campaign.status == CampaignStatus.draft:
        campaign.status = CampaignStatus.scheduled
        campaign.scheduled_at = datetime.utcnow()
        db.flush()
    launch = CampaignService(db).launch(
        send_id,
        CampaignLaunchRequest(
            audience_id=UUID(str(payload['audience_id'])) if payload.get('audience_id') else None,
            rule_tree=_object_payload(payload.get('rule_tree', payload.get('segment_rules')))
            if payload.get('rule_tree') or payload.get('segment_rules')
            else None,
            variables=_object_payload(payload.get('variables')),
            dry_run=bool(payload.get('dry_run', False)),
        ),
    )
    if not launch:
        raise HTTPException(status_code=404, detail='Send not found')
    delivery = None
    if bool(payload.get('process_delivery', payload.get('test_mode', False))):
        delivery = DeliveryService(db, get_settings()).process_queued(
            limit=_int_payload(payload.get('delivery_limit'), 1),
            campaign_id=send_id,
        )
    campaign = CampaignService(db).get(send_id)
    delivered = delivery.sent_count if delivery else 0
    bounced = delivery.failed_count if delivery else 0
    return {
        'send': _send_detail(db, campaign) if campaign else {'id': str(send_id)},
        'summary': {
            'recipient_count': launch.requested_count,
            'delivered': delivered,
            'opened': 0,
            'clicked': 0,
            'converted': 0,
            'bounced': bounced,
            'unsubscribed': 0,
        },
        'delivery': _encoded_dict(delivery) if delivery else None,
        **_encoded_dict(launch),
    }


@router.post('/sends/{send_id}/cancel')
def compat_cancel_send(send_id: UUID, db: DbSession) -> dict[str, object]:
    campaign = CampaignService(db).update(send_id, CampaignUpdate(status=CampaignStatus.paused))
    if not campaign:
        raise HTTPException(status_code=404, detail='Send not found')
    return _send_detail(db, campaign)


@router.post('/sends/{send_id}/request_approval')
def compat_request_send_approval(
    send_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
    if not CampaignService(db).get(send_id):
        raise HTTPException(status_code=404, detail='Send not found')
    return _approval_detail(send_id, note=_optional_str(payload.get('note')))


@router.get('/approvals')
def compat_list_approvals(status: str = 'pending') -> dict[str, object]:
    return _list_response([], 100, 0, 0) if status != 'all' else _list_response([], 100, 0, 0)


@router.post('/approvals/{approval_id}/approve')
def compat_approve_approval(approval_id: UUID) -> dict[str, object]:
    return _approval_detail(approval_id, status='approved')


@router.post('/approvals/{approval_id}/reject')
def compat_reject_approval(approval_id: UUID, payload: dict[str, object]) -> dict[str, object]:
    return _approval_detail(
        approval_id,
        status='rejected',
        rejection_reason=_optional_str(payload.get('reason')),
    )


@router.get('/journeys')
def compat_list_journeys(
    db: DbSession,
    limit: Limit = 100,
    offset: Offset = 0,
) -> dict[str, object]:
    journeys = JourneyService(db).list_items(limit=limit, offset=offset)
    total = db.scalar(select(func.count()).select_from(Journey)) or 0
    return _list_response([_encoded_dict(journey) for journey in journeys], limit, offset, total)


@router.get('/journeys/{journey_id}/performance')
def compat_journey_performance(
    journey_id: UUID, db: DbSession, days: int = 90
) -> dict[str, object]:
    journey = JourneyService(db).get(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail='Journey not found')
    return {
        'journey': _encoded_dict(journey),
        'window_days': days,
        'touches': [],
        'summary': {
            'weakest_touch': None,
            'overall_conversion_rate': 0,
        },
    }


@router.get('/providers')
def compat_providers() -> dict[str, object]:
    return {
        'providers': {
            'email-engine': {
                'configured': True,
                'default_model': 'compat',
                'tasks_owned': ['templates', 'audiences', 'campaigns', 'delivery'],
            }
        }
    }


@router.post('/chat')
def compat_chat(payload: dict[str, object]) -> StreamingResponse:
    message = str(payload.get('message', '')).strip()
    text = (
        'Email Engine compatibility chat is online. '
        'I can help inspect templates, audiences, sends, journeys, and reports exposed by '
        'the email-engine API. Full agent tool execution is not wired yet.'
    )
    if message:
        text = f'{text}\n\nYou asked: {message}'

    def events() -> Iterable[str]:
        yield _sse('text', {'text': text})
        yield _sse('stop', {'reason': 'complete'})

    return StreamingResponse(events(), media_type='text/event-stream')


@router.get('/experiments')
def compat_list_experiments() -> dict[str, object]:
    return _list_response([], 100, 0, 0)


@router.post('/experiments')
def compat_create_experiment(payload: dict[str, object]) -> dict[str, object]:
    now = datetime.utcnow().isoformat()
    return {
        'id': str(uuid4()),
        'name': str(payload.get('name', 'Untitled experiment')),
        'hypothesis': _optional_str(payload.get('hypothesis')),
        'status': 'draft',
        'primary_metric': str(payload.get('primary_metric', 'open_rate')),
        'secondary_metrics': [],
        'allocation_strategy': str(payload.get('allocation_strategy', 'equal')),
        'min_sample_per_arm': _int_payload(payload.get('min_sample_per_arm'), 100),
        'target_lift_pct': payload.get('target_lift_pct'),
        'confidence_target': _float_payload(payload.get('confidence_target'), 0.95),
        'journey_touch_id': None,
        'started_at': None,
        'ended_at': None,
        'winner_variant_id': None,
        'created_at': now,
        'variants': payload.get('variants', []),
    }


@router.get('/experiments/{experiment_id}')
def compat_get_experiment(experiment_id: UUID) -> dict[str, object]:
    raise HTTPException(status_code=404, detail=f'Experiment {experiment_id} not found')


@router.get('/experiments/{experiment_id}/results')
def compat_experiment_results(experiment_id: UUID) -> dict[str, object]:
    return {
        'experiment_id': str(experiment_id),
        'name': 'Experiment',
        'status': 'draft',
        'primary_metric': 'open_rate',
        'variants': [],
        'prob_best': {},
        'winner_name': None,
    }


@router.post('/experiments/{experiment_id}/launch')
@router.post('/experiments/{experiment_id}/conclude')
@router.post('/experiments/{experiment_id}/abort')
def compat_experiment_action(experiment_id: UUID) -> dict[str, object]:
    raise HTTPException(status_code=404, detail=f'Experiment {experiment_id} not found')


@router.get('/reports/overview')
def compat_reports_overview(db: DbSession, days: int = 30) -> dict[str, object]:
    campaign_count = db.scalar(select(func.count()).select_from(Campaign)) or 0
    contact_count = ContactService(db).count()
    audience_count = db.scalar(select(func.count()).select_from(Audience)) or 0
    journey_count = db.scalar(select(func.count()).select_from(Journey)) or 0
    send_record_count = db.scalar(select(func.count()).select_from(EmailSendRecord)) or 0
    event_rows = db.execute(
        select(EmailEvent.event_type, func.count()).group_by(EmailEvent.event_type)
    ).all()
    event_counts = {event_type.value: count for event_type, count in event_rows}
    flat = {
        'campaigns': campaign_count,
        'contacts': contact_count,
        'send_records': send_record_count,
        'event_counts': event_counts,
        'sent': event_counts.get('sent', 0),
        'delivered': event_counts.get('delivered', 0),
        'opened': event_counts.get('opened', 0),
        'clicked': event_counts.get('clicked', 0),
        'bounced': event_counts.get('bounced', 0),
        'complained': event_counts.get('complained', 0),
        'unsubscribed': event_counts.get('unsubscribed', 0),
    }
    return {
        **flat,
        'window_days': days,
        'since': (datetime.utcnow() - timedelta(days=days)).isoformat(),
        'counts': {
            'contacts_total': contact_count,
            'contacts_marketable': contact_count,
            'suppressions_total': 0,
            'templates_total': TemplateService(db).count(),
            'segments_total': audience_count,
            'journeys_total': journey_count,
            'journeys_active': 0,
            'experiments_running': 0,
            'experiments_complete': 0,
            'sends_in_window': campaign_count,
        },
        'send_window': {
            'recipients': send_record_count,
            'delivered': flat['delivered'],
            'opened': flat['opened'],
            'clicked': flat['clicked'],
            'converted': 0,
            'bounced': flat['bounced'],
            'unsubscribed': flat['unsubscribed'],
            'rates': {
                'open_rate': _rate(flat['opened'], flat['sent']),
                'click_rate': _rate(flat['clicked'], flat['sent']),
                'conversion_rate': 0,
                'bounce_rate': _rate(flat['bounced'], flat['sent']),
                'unsubscribe_rate': _rate(flat['unsubscribed'], flat['sent']),
            },
        },
        'daily_series': [],
        'recent_sends': [],
    }


def _list_response(
    items: list[object], limit: int, offset: int, total: int
) -> dict[str, object]:
    return {'items': items, 'limit': limit, 'offset': offset, 'total': total}


def _template_create_payload(payload: dict[str, object]) -> TemplateCreate:
    return TemplateCreate(
        name=str(payload.get('name', payload.get('title', 'Untitled template'))),
        subject=str(payload.get('subject', '')),
        html_body=str(payload.get('html_body', payload.get('html', ''))),
        css_body=_optional_str(payload.get('css_body', payload.get('css'))),
        text_body=_optional_str(payload.get('text_body', payload.get('text'))),
    )


def _template_update_payload(payload: dict[str, object]) -> TemplateUpdate:
    version = _object_payload(payload.get('version', payload))
    values: dict[str, object] = {}
    for source_key, target_key in [
        ('name', 'name'),
        ('title', 'name'),
        ('subject', 'subject'),
        ('html_body', 'html_body'),
        ('html_compiled', 'html_body'),
        ('html', 'html_body'),
        ('css_body', 'css_body'),
        ('css', 'css_body'),
        ('text_body', 'text_body'),
        ('plain_text', 'text_body'),
        ('text', 'text_body'),
    ]:
        if source_key in version:
            values[target_key] = version[source_key]
    return TemplateUpdate.model_validate(values)


def _template_version_create_payload(payload: dict[str, object]) -> TemplateVersionCreate:
    version = _object_payload(payload.get('version', payload))
    return TemplateVersionCreate(
        subject=_optional_str(version.get('subject')),
        html_body=_optional_str(
            version.get('html_body', version.get('html_compiled', version.get('html')))
        ),
        css_body=_optional_str(version.get('css_body', version.get('css'))),
        text_body=_optional_str(
            version.get('text_body', version.get('plain_text', version.get('text')))
        ),
        document_json=_object_payload(version.get('document_json', version.get('document'))),
        set_current=bool(version.get('set_current', payload.get('set_current', True))),
    )


def _template_summary(template: object) -> dict[str, object]:
    data = jsonable_encoder(template)
    versions = _template_versions_for_template(template)
    return {
        **data,
        'title': data.get('name'),
        'current_version': next(
            (version for version in versions if version.get('is_current')), _template_version(data)
        ),
    }


def _template_detail(template: object) -> dict[str, object]:
    data = _template_summary(template)
    data['versions'] = _template_versions_for_template(template)
    return data


def _template_version(template_data: dict[str, object]) -> dict[str, object]:
    return {
        'id': template_data.get('id'),
        'template_id': template_data.get('id'),
        'version': 1,
        'version_number': 1,
        'subject': template_data.get('subject'),
        'preheader': None,
        'from_name': 'Email Engine',
        'from_email': 'no-reply@example.com',
        'html_body': template_data.get('html_body'),
        'html_compiled': template_data.get('html_body'),
        'css_body': template_data.get('css_body'),
        'text_body': template_data.get('text_body'),
        'plain_text': template_data.get('text_body'),
        'document_json': {},
        'personalization_slots': [],
        'is_current': True,
    }


def _template_versions_for_template(template: object) -> list[dict[str, object]]:
    versions = getattr(template, 'versions', None)
    if not versions:
        return [_template_version(jsonable_encoder(template))]
    encoded = [cast(dict[str, object], jsonable_encoder(version)) for version in versions]
    for version in encoded:
        version['version'] = version.get('version_number')
        version['preheader'] = None
        version['from_name'] = 'Email Engine'
        version['from_email'] = 'no-reply@example.com'
        version['html_compiled'] = version.get('html_body')
        version['plain_text'] = version.get('text_body')
        version['personalization_slots'] = []
    return encoded


def _segment_summary(audience: object) -> dict[str, object]:
    data = jsonable_encoder(audience)
    rule_tree = cast(dict[str, object], data.get('rule_tree', {}))
    estimated_count = data.get('estimated_count', 0)
    return {
        **data,
        'rules': rule_tree,
        'definition': _rule_tree_to_segment_definition(rule_tree),
        'summary': f'{estimated_count} estimated contacts',
        'estimated_size': estimated_count,
        'estimated_at': data.get('updated_at', data.get('created_at')),
    }


def _send_detail(db: Session, campaign: Campaign) -> dict[str, object]:
    metrics = AnalyticsService(db).campaign_metrics(campaign.id)
    template = TemplateService(db).get(campaign.template_id)
    versions = _template_versions_for_template(template) if template else []
    current_version = next((version for version in versions if version.get('is_current')), None)
    audience = _audience_for_rule_tree(db, campaign.audience_query)
    metric_data = jsonable_encoder(metrics) if metrics else {}
    return {
        **jsonable_encoder(campaign),
        'send_id': str(campaign.id),
        'id': str(campaign.id),
        'title': campaign.name,
        'template_id': str(campaign.template_id) if campaign.template_id else None,
        'template_name': template.name if template else None,
        'template_version_id': (
            current_version.get('id') if current_version else str(campaign.template_id)
        ),
        'template_version_number': (
            current_version.get('version_number') if current_version else None
        ),
        'subject': template.subject if template else None,
        'segment_id': str(audience.id) if audience else None,
        'segment_name': audience.name if audience else None,
        'segment_summary': f'{audience.estimated_count} estimated contacts' if audience else None,
        'scheduled_for': campaign.scheduled_at.isoformat() if campaign.scheduled_at else None,
        'sent_at': None,
        'recipient_count': metric_data.get('requested_count', 0),
        'delivered_count': metric_data.get('delivered_count', 0),
        'opened_count': metric_data.get('opened_count', 0),
        'clicked_count': metric_data.get('clicked_count', 0),
        'converted_count': 0,
        'bounced_count': metric_data.get('bounced_count', 0),
        'unsubscribed_count': metric_data.get('unsubscribed_count', 0),
        'rates': {
            'open_rate': metric_data.get('open_rate', 0),
            'click_rate': metric_data.get('click_rate', 0),
            'conversion_rate': 0,
            'bounce_rate': metric_data.get('bounce_rate', 0),
            'unsubscribe_rate': 0,
        },
        'metrics': metric_data or None,
    }


def _segment_rule_tree(payload: Mapping[str, object]) -> JsonObject:
    if payload.get('rule_tree') or payload.get('rules'):
        return _object_payload(payload.get('rule_tree', payload.get('rules')))
    definition = _object_payload(payload.get('definition'))
    rules = definition.get('rules')
    if not isinstance(rules, list):
        return {}
    translated: list[object] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        translated.append(
            {
                'field': rule.get('field'),
                'comparator': _segment_op(str(rule.get('op', 'eq'))),
                'value': rule.get('value'),
            }
        )
    return {'operator': 'and', 'rules': translated}


def _has_segment_rules(payload: Mapping[str, object]) -> bool:
    return any(key in payload for key in ('rule_tree', 'rules', 'definition'))


def _segment_op(op: str) -> str:
    return {
        'ne': 'neq',
        'not_in': 'not_in',
        'is_null': 'is_null',
        'is_not_null': 'is_not_null',
    }.get(op, op)


def _rule_tree_to_segment_definition(rule_tree: Mapping[str, object]) -> dict[str, object]:
    rules = rule_tree.get('rules')
    if not isinstance(rules, list):
        return {'rules': []}
    definition_rules: list[dict[str, object]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        definition_rules.append(
            {
                'field': rule.get('field'),
                'op': str(rule.get('comparator', 'eq')),
                'value': rule.get('value'),
            }
        )
    return {'rules': definition_rules}


def _contact_row(contact: Contact) -> dict[str, object]:
    attributes = contact.attributes or {}
    return {
        **_encoded_dict(contact),
        'searched_state': attributes.get('searched_state', attributes.get('state')),
        'is_self_search': attributes.get('is_self_search'),
        'intent_criminal': attributes.get('intent_criminal'),
        'regulated': bool(attributes.get('regulated', False)),
        'consent_marketing': not contact.is_unsubscribed,
        'engagement': attributes.get('engagement'),
        'acquired_at': attributes.get('acquired_at'),
    }


def _contact_matches_filters(
    contact: Contact,
    *,
    state: str | None,
    self_search: bool | None,
    regulated: bool | None,
    intent_criminal: bool | None,
    consent_marketing: bool | None,
    engagement: str | None,
) -> bool:
    attributes = contact.attributes or {}
    contact_state = str(attributes.get('searched_state', attributes.get('state', ''))).upper()
    if state and contact_state != state.upper():
        return False
    if self_search is not None and _attribute_bool(contact, 'is_self_search') != self_search:
        return False
    if regulated is not None and _attribute_bool(contact, 'regulated') != regulated:
        return False
    if (
        intent_criminal is not None
        and _attribute_bool(contact, 'intent_criminal') != intent_criminal
    ):
        return False
    if consent_marketing is not None and (not contact.is_unsubscribed) != consent_marketing:
        return False
    if engagement and str(attributes.get('engagement', '')) != engagement:
        return False
    return True


def _attribute_bool(contact: Contact, key: str) -> bool:
    value = (contact.attributes or {}).get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {'1', 'true', 'yes', 'y'}
    return bool(value)


def _template_id_from_payload(payload: Mapping[str, object], db: Session) -> UUID:
    template_id = payload.get('template_id')
    if template_id:
        return UUID(str(template_id))
    version_id = payload.get('template_version_id')
    if version_id:
        version = db.get(EmailTemplateVersion, UUID(str(version_id)))
        if version:
            return version.template_id
    raise HTTPException(status_code=422, detail='template_id or template_version_id is required')


def _datetime_payload(value: object) -> datetime | None:
    if value is None or value == '':
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')).replace(tzinfo=None)


def _approval_detail(
    resource_id: UUID,
    *,
    status: str = 'pending',
    note: str | None = None,
    rejection_reason: str | None = None,
) -> dict[str, object]:
    now = datetime.utcnow().isoformat()
    return {
        'id': str(uuid4()),
        'resource_type': 'send',
        'resource_id': str(resource_id),
        'resource': {'type': 'send', 'id': str(resource_id)},
        'requested_by': 'email-engine',
        'approved_at': now if status == 'approved' else None,
        'rejected_at': now if status == 'rejected' else None,
        'rejection_reason': rejection_reason,
        'context': {'note': note} if note else {},
        'status': status,
        'created_at': now,
    }


def _audience_for_rule_tree(db: Session, rule_tree: Mapping[str, object]) -> Audience | None:
    return db.scalar(select(Audience).where(Audience.rule_tree == dict(rule_tree)).limit(1))


def _rate(numerator: object, denominator: object) -> float | None:
    try:
        top = float(str(numerator or 0))
        bottom = float(str(denominator or 0))
    except (TypeError, ValueError):
        return None
    if bottom == 0:
        return None
    return top / bottom


def _float_payload(value: object, default: float) -> float:
    if value is None:
        return default
    try:
        return float(str(value))
    except ValueError:
        return default


def _document_to_html(document: Mapping[str, object]) -> str:
    blocks = document.get('blocks')
    if not isinstance(blocks, list):
        return str(document.get('html', ''))
    html_parts: list[str] = []
    for block in blocks:
        if not isinstance(block, dict):
            continue
        block_type = str(block.get('type', 'paragraph'))
        text = str(block.get('text', block.get('content', '')))
        if block_type in {'heading', 'h1'}:
            html_parts.append(f'<h1>{text}</h1>')
        elif block_type in {'html', 'raw'}:
            html_parts.append(text)
        else:
            html_parts.append(f'<p>{text}</p>')
    return '\n'.join(html_parts)


def _draft_html(current_html: str, brief: str) -> str:
    note = brief or 'Review this message for clarity, relevance, and deliverability.'
    return (
        f'{current_html.rstrip()}\n\n'
        '<div class="content-card">\n'
        '  <p class="secondary-text">Draft note</p>\n'
        f'  <p>{_escape_html(note)}</p>\n'
        '</div>'
    )


def _validation_failures(messages: list[str], severity: str) -> list[dict[str, object]]:
    return [
        {
            'code': 'email_engine_validation',
            'severity': severity,
            'location': 'template',
            'message': message,
            'matched_text': None,
            'suggestion': None,
        }
        for message in messages
    ]


def _sse(event: str, data: Mapping[str, object]) -> str:
    return f'event: {event}\ndata: {json.dumps(data)}\n\n'


def _escape_html(value: str) -> str:
    return (
        value.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )


def _encoded_dict(value: object) -> dict[str, object]:
    return cast(dict[str, object], jsonable_encoder(value))


def _object_payload(value: object) -> JsonObject:
    return cast(JsonObject, value) if isinstance(value, dict) else {}


def _int_payload(value: object, default: int) -> int:
    if value is None:
        return default
    try:
        return int(str(value))
    except ValueError:
        return default


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None
