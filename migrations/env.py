from alembic import context
from app import db

connection = context.config.attributes['connection']
context.configure(connection=connection, target_metadata=db.metadata,
                  render_as_batch=connection.dialect.name == 'sqlite', compare_type=True)
with context.begin_transaction():
    context.run_migrations()
