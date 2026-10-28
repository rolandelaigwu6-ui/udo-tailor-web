from pathlib import Path
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from app import db


def configuration():
    config = Config()
    config.set_main_option('script_location', str(Path(__file__).resolve().parent.parent / 'migrations'))
    return config


def schema_is_current():
    with db.engine.connect() as connection:
        current = MigrationContext.configure(connection).get_current_revision()
    return current == ScriptDirectory.from_config(configuration()).get_current_head()


def upgrade_database():
    config = configuration()
    with db.engine.begin() as connection:
        config.attributes['connection'] = connection
        command.upgrade(config, 'head')
