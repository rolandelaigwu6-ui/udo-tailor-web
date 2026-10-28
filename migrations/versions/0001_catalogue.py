"""Initial schema, including adoption of the original unversioned SQLite schema."""
from alembic import op
import sqlalchemy as sa

revision = '0001_catalogue'
down_revision = None
branch_labels = None
depends_on = None

schema = sa.MetaData()
sa.Table('achievements', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('year', sa.String(length=20), nullable=True),
    sa.Column('image_url', sa.String(length=500), nullable=True),
    sa.Column('display_order', sa.Integer(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
)
sa.Table('admins', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False, unique=True),
    sa.Column('email', sa.String(length=120), nullable=True, unique=True),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
)
sa.Table('client_showcase', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('client_name', sa.String(length=120), nullable=True),
    sa.Column('design_name', sa.String(length=200), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('image_url', sa.String(length=500), nullable=True),
    sa.Column('category', sa.String(length=80), nullable=True),
    sa.Column('testimonial', sa.Text(), nullable=True),
    sa.Column('permission_confirmed', sa.Boolean(), nullable=True),
    sa.Column('featured', sa.Boolean(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
)
sa.Table('clothing', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('slug', sa.String(length=220), nullable=False, unique=True, index=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('category', sa.String(length=80), nullable=True),
    sa.Column('material', sa.String(length=120), nullable=True),
    sa.Column('sizes', sa.String(length=200), nullable=True),
    sa.Column('colors', sa.String(length=200), nullable=True),
    sa.Column('availability', sa.String(length=40), nullable=False),
    sa.Column('featured', sa.Boolean(), nullable=False),
    sa.Column('likes', sa.Integer(), nullable=False),
    sa.Column('interested_count', sa.Integer(), nullable=False),
    sa.Column('not_interested_count', sa.Integer(), nullable=False),
    sa.Column('view_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
)
sa.Table('site_settings', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('brand_name', sa.String(length=120), nullable=True),
    sa.Column('logo', sa.String(length=500), nullable=True),
    sa.Column('hero_heading', sa.String(length=200), nullable=True),
    sa.Column('hero_description', sa.Text(), nullable=True),
    sa.Column('phone', sa.String(length=40), nullable=True),
    sa.Column('whatsapp', sa.String(length=40), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('address', sa.String(length=300), nullable=True),
    sa.Column('opening_hours', sa.String(length=200), nullable=True),
    sa.Column('bank_name', sa.String(length=120), nullable=True),
    sa.Column('account_name', sa.String(length=120), nullable=True),
    sa.Column('account_number', sa.String(length=40), nullable=True),
    sa.Column('about', sa.Text(), nullable=True),
    sa.Column('instagram', sa.String(length=200), nullable=True),
    sa.Column('facebook', sa.String(length=200), nullable=True),
    sa.Column('tiktok', sa.String(length=200), nullable=True),
    sa.Column('social_links', sa.Text(), nullable=True),
    sa.Column('designer_name', sa.String(length=120), nullable=True),
    sa.Column('designer_title', sa.String(length=120), nullable=True),
    sa.Column('designer_bio', sa.Text(), nullable=True),
    sa.Column('designer_image', sa.String(length=500), nullable=True),
    sa.Column('years_experience', sa.String(length=40), nullable=True),
    sa.Column('specialties', sa.Text(), nullable=True),
    sa.Column('signature_style', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
)
sa.Table('visitors', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('public_id', sa.String(length=64), nullable=False, unique=True, index=True),
    sa.Column('name', sa.String(length=120), nullable=True),
    sa.Column('email', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('last_seen_at', sa.DateTime(), nullable=True),
    sa.Column('newsletter_subscribed', sa.Boolean(), nullable=True),
)
sa.Table('clothing_activities', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('clothing_id', sa.Integer(), sa.ForeignKey('clothing.id'), nullable=False),
    sa.Column('visitor_id', sa.Integer(), sa.ForeignKey('visitors.id'), nullable=True),
    sa.Column('activity_type', sa.String(length=40), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
)
sa.Table('clothing_images', schema,
    sa.Column('id', sa.Integer(), primary_key=True, nullable=False),
    sa.Column('clothing_id', sa.Integer(), sa.ForeignKey('clothing.id'), nullable=False),
    sa.Column('image_url', sa.String(length=500), nullable=False),
    sa.Column('is_primary', sa.Boolean(), nullable=True),
    sa.Column('sort_order', sa.Integer(), nullable=True),
)

def upgrade():
    connection = op.get_bind()
    existing = set(sa.inspect(connection).get_table_names())
    for table in schema.sorted_tables:
        if table.name not in existing:
            table.create(connection)
            continue
        # Preserve existing data while adopting the previous unversioned schema.
        columns = {column['name'] for column in sa.inspect(connection).get_columns(table.name)}
        for column in table.columns:
            if column.name in columns:
                continue
            if column.primary_key or (not column.nullable and not isinstance(column.type, sa.Boolean)):
                raise RuntimeError(f'Unsupported legacy schema: missing {table.name}.{column.name}')
            addition = column._copy()
            if isinstance(column.type, sa.Boolean):
                addition.server_default = sa.DefaultClause(sa.false())
            op.add_column(table.name, addition)
        if table.name == 'clothing':
            featured = next(c for c in sa.inspect(connection).get_columns('clothing') if c['name'] == 'featured')
            if featured['nullable']:
                connection.execute(table.update().where(table.c.featured.is_(None)).values(featured=False))
                with op.batch_alter_table('clothing') as batch:
                    batch.alter_column('featured', existing_type=sa.Boolean(), nullable=False)


def downgrade():
    raise RuntimeError('Restore a database backup to undo the initial schema migration.')
