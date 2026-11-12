"""Persist logout revocations across restarts."""
from alembic import op
import sqlalchemy as sa
revision = "0002_revoked_tokens"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    from app.models import RevokedToken
    RevokedToken.__table__.create(op.get_bind(), checkfirst=True)

def downgrade():
    op.drop_table("revoked_tokens")
