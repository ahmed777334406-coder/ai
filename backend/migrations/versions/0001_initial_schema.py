"""Initial SmartFind schema.

Revision ID: 0001_initial
Revises:
"""
from alembic import op
from app.database import Base
from app import models  # noqa: F401
revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    Base.metadata.create_all(bind=bind)

def downgrade():
    # Initial migration only. Data removal must be an explicit operator decision.
    raise RuntimeError("Initial SmartFind migration is intentionally non-destructive; archive the database instead of downgrading.")
