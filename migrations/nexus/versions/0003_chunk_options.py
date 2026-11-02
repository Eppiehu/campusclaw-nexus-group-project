"""Store the slicing choices made in the upload dialog."""
from alembic import op
from sqlalchemy import inspect

revision='0003_chunk_options'
down_revision='0002_search'
branch_labels=None
depends_on=None


def upgrade():
    connection=op.get_bind()
    if 'chunk_options' not in {column['name'] for column in inspect(connection).get_columns('material_versions')}:
        op.execute("ALTER TABLE material_versions ADD COLUMN chunk_options JSON NOT NULL DEFAULT '{}'")


def downgrade():
    raise RuntimeError('Restore an approved database backup instead of destructive downgrade')
