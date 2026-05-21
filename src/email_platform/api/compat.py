from collections.abc import Mapping
from typing import Annotated, cast
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from email_platform.db.session import get_db
from email_platform.models.entities import Campaign, Contact, EmailEvent, EmailSendRecord
from email_platform.schemas.contracts import (
    AudienceCreate,
    AudiencePreviewRequest,
    CampaignCreate,
    CampaignLaunchRequest,
    ContactUpsert,
    JsonObject,
    TemplateCreate,
    TemplatePreviewRequest,
    TemplateUpdate,
    TemplateVersionCreate,
)
from email_platform.services.analytics import AnalyticsService
from email_platform.services.audiences import AudienceService
from email_platform.services.campaigns import CampaignService
from email_platform.services.contacts import ContactService
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
    return _template_detail(template)


@router.get('/templates/{template_id}')
def compat_get_template(template_id: UUID, db: DbSession) -> dict[str, object]:
    template = TemplateService(db).get(template_id)
    if not template:
        raise HTTPException(status_code=404, detail='Template not found')
    return _template_detail(template)


@router.post('/render')
def compat_render(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    template_id = payload.get('template_id')
    variables = _object_payload(payload.get('variables'))
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
    source: str | None = None,
) -> dict[str, object]:
    statement = select(Contact).order_by(Contact.created_at.desc())
    count_statement = select(func.count()).select_from(Contact)
    if email:
        statement = statement.where(Contact.email.ilike(f'%{email}%'))
        count_statement = count_statement.where(Contact.email.ilike(f'%{email}%'))
    if source:
        statement = statement.where(Contact.source == source)
        count_statement = count_statement.where(Contact.source == source)
    contacts = list(db.scalars(statement.limit(limit).offset(offset)).all())
    total = db.scalar(count_statement) or 0
    return _list_response(
        [_encoded_dict(contact) for contact in contacts], limit, offset, total
    )


@router.get('/contacts/_meta')
def compat_contacts_meta(db: DbSession) -> dict[str, object]:
    sources = db.execute(
        select(Contact.source, func.count())
        .where(Contact.source.is_not(None))
        .group_by(Contact.source)
        .order_by(Contact.source)
    ).all()
    return {
        'total': ContactService(db).count(),
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


@router.post('/segments')
def compat_create_segment(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    audience = AudienceService(db).create(
        AudienceCreate(
            name=str(payload.get('name', f'segment-{uuid4()}')),
            description=_optional_str(payload.get('description')),
            rule_tree=_object_payload(payload.get('rule_tree', payload.get('rules'))),
        )
    )
    return _segment_summary(audience)


@router.post('/segments/preview')
def compat_preview_segment(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    request = AudiencePreviewRequest(
        rule_tree=_object_payload(payload.get('rule_tree', payload.get('rules'))),
        limit=_int_payload(payload.get('limit'), 25),
    )
    count, contacts = AudienceService(db).preview(request.rule_tree, request.limit)
    return {'estimated_count': count, 'items': [_encoded_dict(contact) for contact in contacts]}


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


@router.post('/sends')
def compat_create_send(payload: dict[str, object], db: DbSession) -> dict[str, object]:
    campaign = CampaignService(db).create(
        CampaignCreate(
            name=str(payload.get('name', payload.get('title', 'Untitled send'))),
            template_id=UUID(str(payload.get('template_id'))),
            audience_query=_object_payload(
                payload.get('audience_query', payload.get('segment_rules'))
            ),
        )
    )
    return _send_detail(db, campaign)


@router.post('/sends/{send_id}/launch')
def compat_launch_send(
    send_id: UUID, payload: dict[str, object], db: DbSession
) -> dict[str, object]:
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
    return _encoded_dict(launch)


@router.get('/reports/overview')
def compat_reports_overview(db: DbSession) -> dict[str, object]:
    campaign_count = db.scalar(select(func.count()).select_from(Campaign)) or 0
    contact_count = ContactService(db).count()
    send_record_count = db.scalar(select(func.count()).select_from(EmailSendRecord)) or 0
    event_rows = db.execute(
        select(EmailEvent.event_type, func.count()).group_by(EmailEvent.event_type)
    ).all()
    event_counts = {event_type.value: count for event_type, count in event_rows}
    return {
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
        ('html', 'html_body'),
        ('css_body', 'css_body'),
        ('css', 'css_body'),
        ('text_body', 'text_body'),
        ('text', 'text_body'),
    ]:
        if source_key in version:
            values[target_key] = version[source_key]
    return TemplateUpdate.model_validate(values)


def _template_version_create_payload(payload: dict[str, object]) -> TemplateVersionCreate:
    version = _object_payload(payload.get('version', payload))
    return TemplateVersionCreate(
        subject=_optional_str(version.get('subject')),
        html_body=_optional_str(version.get('html_body', version.get('html'))),
        css_body=_optional_str(version.get('css_body', version.get('css'))),
        text_body=_optional_str(version.get('text_body', version.get('text'))),
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
        'html_body': template_data.get('html_body'),
        'css_body': template_data.get('css_body'),
        'text_body': template_data.get('text_body'),
        'document_json': {},
        'is_current': True,
    }


def _template_versions_for_template(template: object) -> list[dict[str, object]]:
    versions = getattr(template, 'versions', None)
    if not versions:
        return [_template_version(jsonable_encoder(template))]
    encoded = [cast(dict[str, object], jsonable_encoder(version)) for version in versions]
    for version in encoded:
        version['version'] = version.get('version_number')
    return encoded


def _segment_summary(audience: object) -> dict[str, object]:
    data = jsonable_encoder(audience)
    return {
        **data,
        'rules': data.get('rule_tree', {}),
        'estimated_size': data.get('estimated_count', 0),
    }


def _send_detail(db: Session, campaign: Campaign) -> dict[str, object]:
    metrics = AnalyticsService(db).campaign_metrics(campaign.id)
    return {
        **jsonable_encoder(campaign),
        'send_id': str(campaign.id),
        'title': campaign.name,
        'metrics': jsonable_encoder(metrics) if metrics else None,
    }


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
