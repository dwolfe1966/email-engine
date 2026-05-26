from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from email_platform.core.settings import Settings
from email_platform.models.entities import (
    Audience,
    Campaign,
    CampaignSendJob,
    Contact,
    DataSource,
    EmailEvent,
    EmailSendRecord,
    EmailTemplate,
    Journey,
    Suppression,
)

JsonObject = dict[str, object]


def schema_status(db: Session) -> JsonObject:
    expected_revision = _migration_head()
    try:
        current_revision = _current_revision(db)
    except SQLAlchemyError as exc:
        return {
            'ok': False,
            'db_reachable': False,
            'current_revision': None,
            'expected_revision': expected_revision,
            'needs_migration': True,
            'migration_command': 'alembic upgrade head',
            'error': str(exc),
        }
    return {
        'ok': current_revision == expected_revision,
        'db_reachable': True,
        'current_revision': current_revision,
        'expected_revision': expected_revision,
        'needs_migration': current_revision != expected_revision,
        'migration_command': 'alembic upgrade head',
    }


def system_diagnostics(db: Session, settings: Settings) -> JsonObject:
    schema = schema_status(db)
    counts, count_errors = _entity_counts(db) if schema.get('db_reachable') else ({}, [])
    return {
        'ok': bool(schema.get('ok')) and not count_errors,
        'schema': schema,
        'environment': settings.environment,
        'public_base_url': settings.public_base_url,
        'email_provider': {
            'provider': settings.email_provider,
            'default_from_email': str(settings.default_from_email),
            'sendgrid_configured': bool(settings.sendgrid_api_key),
            'smtp_configured': bool(settings.smtp_host),
        },
        'ai': {
            'provider': settings.ai_template_provider,
            'model': settings.openai_model,
            'openai_configured': bool(settings.openai_api_key),
        },
        'entity_counts': counts,
        'errors': count_errors,
    }


def _migration_head() -> str | None:
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    return ScriptDirectory.from_config(config).get_current_head()


def _current_revision(db: Session) -> str | None:
    context = MigrationContext.configure(db.connection())
    return context.get_current_revision()


def _entity_counts(db: Session) -> tuple[JsonObject, list[str]]:
    models = {
        'contacts': Contact,
        'templates': EmailTemplate,
        'audiences': Audience,
        'campaigns': Campaign,
        'send_jobs': CampaignSendJob,
        'send_records': EmailSendRecord,
        'events': EmailEvent,
        'journeys': Journey,
        'data_sources': DataSource,
        'suppressions': Suppression,
    }
    counts: JsonObject = {}
    errors: list[str] = []
    for key, model in models.items():
        try:
            counts[key] = db.scalar(select(func.count()).select_from(model)) or 0
        except SQLAlchemyError as exc:
            errors.append(f'{key}: {exc}')
    return counts, errors
