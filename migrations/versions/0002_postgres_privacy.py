"""Block direct anonymous Data API access to application tables on Supabase."""
from alembic import op

revision = '0002_postgres_privacy'
down_revision = '0001_catalogue'
branch_labels = None
depends_on = None

TABLES = ('admins', 'clothing', 'clothing_images', 'site_settings', 'visitors',
          'clothing_activities', 'achievements', 'client_showcase', 'alembic_version')


def upgrade():
    connection = op.get_bind()
    if connection.dialect.name == 'postgresql':
        for name in TABLES:
            op.execute(f'ALTER TABLE "{name}" ENABLE ROW LEVEL SECURITY')


def downgrade():
    raise RuntimeError('Do not disable application table privacy; restore a reviewed backup instead.')
