"""Add class-scoped external MCP connection snapshots."""
from alembic import op
import sqlalchemy as sa

revision='0005_mcp_connections'
down_revision='0004_answer_hint'
branch_labels=None
depends_on=None

def upgrade():
    # 0001 imports current Base metadata on a clean install.
    if sa.inspect(op.get_bind()).has_table('mcp_connections'):return
    op.create_table('mcp_connections',
        sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),
        sa.Column('class_id',sa.String(32),nullable=False,index=True),
        sa.Column('name',sa.String(100),nullable=False),
        sa.Column('server_key',sa.String(64),nullable=False),
        sa.Column('credential_ref',sa.String(100),nullable=False),
        sa.Column('state',sa.String(16),nullable=False),
        sa.Column('enabled',sa.Boolean(),nullable=False),
        sa.Column('fingerprint',sa.String(64),nullable=False),
        sa.Column('tools',sa.JSON(),nullable=False))

def downgrade():
    raise RuntimeError('Restore an approved backup instead of dropping MCP connection records')
