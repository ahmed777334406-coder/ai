"""Add optional owner-scoped retry keys without changing existing records."""
from alembic import op
import sqlalchemy as sa
revision = '0003_report_idempotency'
down_revision = '0002_revoked_tokens'
branch_labels = None
depends_on = None

def upgrade():
    # The historical initial migration uses current Base.metadata on fresh installs.
    inspector = sa.inspect(op.get_bind())
    if 'client_request_id' not in {column['name'] for column in inspector.get_columns('listings')}:
        op.add_column('listings', sa.Column('client_request_id', sa.String(64), nullable=True))
    if 'uq_listing_owner_request' not in {constraint['name'] for constraint in inspector.get_unique_constraints('listings')}:
        with op.batch_alter_table('listings') as batch:
            batch.create_unique_constraint('uq_listing_owner_request', ['owner_id', 'client_request_id'])

def downgrade():
    with op.batch_alter_table('listings') as batch:
        batch.drop_constraint('uq_listing_owner_request', type_='unique')
        batch.drop_column('client_request_id')
