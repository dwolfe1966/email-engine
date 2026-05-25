from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

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


def _migration_head() -> str | None:
    root = Path(__file__).resolve().parents[3]
    config = Config(str(root / 'alembic.ini'))
    config.set_main_option('script_location', str(root / 'alembic'))
    return ScriptDirectory.from_config(config).get_current_head()


def _current_revision(db: Session) -> str | None:
    context = MigrationContext.configure(db.connection())
    return context.get_current_revision()
