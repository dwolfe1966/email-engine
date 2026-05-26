from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import func, inspect, select
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
    tables, table_errors = _database_tables(db) if schema.get('db_reachable') else ([], [])
    table_columns, column_errors = (
        _database_table_columns(db, tables) if schema.get('db_reachable') else ({}, [])
    )
    return {
        'ok': bool(schema.get('ok')) and not count_errors and not table_errors and not column_errors,
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
        'database_tables': tables,
        'database_table_columns': table_columns,
        'errors': [*count_errors, *table_errors, *column_errors],
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


def _database_tables(db: Session) -> tuple[list[str], list[str]]:
    try:
        tables = inspect(db.connection()).get_table_names()
    except SQLAlchemyError as exc:
        return [], [f'database_tables: {exc}']
    return sorted(tables), []


def _database_table_columns(db: Session, tables: list[str]) -> tuple[JsonObject, list[str]]:
    inspector = inspect(db.connection())
    schema: JsonObject = {}
    errors: list[str] = []
    for table in tables:
        try:
            schema[table] = [
                {
                    'name': column['name'],
                    'type': str(column['type']),
                    'nullable': bool(column['nullable']),
                    'primary_key': bool(column.get('primary_key')),
                }
                for column in inspector.get_columns(table)
            ]
        except SQLAlchemyError as exc:
            errors.append(f'database_table_columns.{table}: {exc}')
    return schema, errors
